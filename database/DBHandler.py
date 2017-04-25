import sqlite3
import time
import json
LAB_TABLE_COLNAMES = ['_id','labNAME']
LAB_TABLE_COLTYPES = ['INTEGER PRIMARY KEY AUTOINCREMENT','TEXT']
OBSERVATION_TABLE_COLNAMES = ['_id','labID']
OBSERVATION_TABLE_COLTYPES = ['INTEGER PRIMARY KEY AUTOINCREMENT','INTEGER']
METADATA_TABLE_COLNAMES = ['time','labID','metadata']
METADATA_TABLE_COLTYPES = ['REAL','INTEGER','TEXT']


class DBHandler(object):
    """ Handler of the database operations of lab-nanny.

    This handler is in charge of opening/creating a database,
    registering new nodes and metadata, and adding database entries on
    each db_tick in the servers.server_master.

    This handler will create (if it does not exist) an sqlite database
    with at least 3 tables:
    - Laboratories table ('laboratories')
    - Observations table ('observation_list')
    - Metadata table     ('metadata_list')

    Laboratories table:
    -------------------
    Keeps a record of the connected laboratories's names, and associates
    them with an id

    Observations table:
    -------------------
    Each observation corresponds to the dictionary in one lab at the moment
    of saving the data.
    For example, if two nodes are connected, every time a db_tick is called
    in the master server, two observations will be added to the observations
    table, with incremental _id number, and each of them associated with a
    different laboratory id.

    Metadata table
    --------------
    If the dictionary sent by the node has a 'meta' key, the contents of the
    dictionary will be stored in this table as a string, using the JSON
    format. Each of these metadata entries have associated a laboratory
    id and a timestamp.


    To register a new node, the DBHandler creates a new table with the name
    of the node (e.g. 'lab7'), and an entry in the laboratories table.
    The name of the columns in the table are set to the names of the keys
    in the dictionary sent the first time the laboratory is registered.

    If the node is registered, the DBHandler.add_data_from_dict method will
    add data into the table from the given dictionary.

        NOTE: If the dictionaries used in the creation of the database and the
    addition of new data have a different set of keys, problems might occur!




    """
    def __init__(self, db_name='example.db',verbose=False):
        self.db = sqlite3.connect(db_name)
        self.cursor = self.db.cursor()
        self.labs_tablename = 'laboratories'
        self.observations_tablename = 'observation_list'
        self.metadata_tablename = 'metadata_list'

        self.verbose=verbose

        # Make sure that the three main tables (laboratories,
        # observations and metadata) are in the database.
        # If these table names exist, nothing will happen.
        self._create_table(self.labs_tablename,
                           column_names=LAB_TABLE_COLNAMES,
                           column_types=LAB_TABLE_COLTYPES)
        self._create_table(self.observations_tablename,
                           column_names=OBSERVATION_TABLE_COLNAMES,
                           column_types=OBSERVATION_TABLE_COLTYPES)
        self._create_table(self.metadata_tablename,
                           column_names=METADATA_TABLE_COLNAMES,
                           column_types=METADATA_TABLE_COLTYPES)
        self.commit()


    def _create_table(self,tablename,column_names,column_types):
        ''' Creates a table with a given name, column names and types.

        It does not do anything if the table already exists.

        :param tablename:
        :param column_names:
        :param column_types:
        :return:
        '''
        if not self.check_table_exists(tablename):
            #Construct SQL command
            sql_string = 'CREATE TABLE ' + tablename + ' ('
            for colname,coltype in zip(column_names, column_types):
                sql_string = sql_string + '{colname} {coltype}, '\
                    .format(colname=colname, coltype=coltype)
            #We need to remove the last comma and space before closing the parenthesis
            sql_string = sql_string[:-2]+')'

            if self.verbose:
                print('sql> '+sql_string)
            self.cursor.execute(sql_string)
            self.commit()


    def _register_new_laboratory(self,labname):
        """ Registers a new laboratory in the lab's table and returns its ID.

        NOTE: It does not check whether the lab exists beforehand.
        """
        #NOTE: We could check whether a table with the labname exists...
        lab_table_col_string = ','.join(LAB_TABLE_COLNAMES)
        sql_string = 'INSERT INTO {lab_table}('\
            .format(lab_table = self.labs_tablename)
        sql_string+= lab_table_col_string+') VALUES (NULL,?)'
        if self.verbose:
            print('sql> '+sql_string)
        self.cursor.execute(sql_string,(labname,))
        self.commit()
        return self.cursor.lastrowid

    def _add_column(self,labname,columnname,datatype = 'REAL'):
        # It is possible to add a default value for the newly created column.
        self.cursor.execute("ALTER TABLE {table} ADD COLUMN '{colname}' {coltype}"\
                    .format(table=labname,colname=columnname,
                            coltype=datatype))
        self.commit()

    def get_labID_by_name(self,labname):
        sql_string = "SELECT _id FROM {table} WHERE labNAME=(?)"\
            .format(table=self.labs_tablename)
        if self.verbose:
            print('sql> '+sql_string)
        self.cursor.execute(sql_string,(labname,))
        labID = self.cursor.fetchone()
        return labID[0]

    def check_table_exists(self,tablename):
        """ Check if a table with a given name exists in the current database.

        :param tablename:
        """
        table_names = self.tables_in_db()
        return tablename in table_names

    def tables_in_db(self):
        """ Enumerate the tables in the current db."""
        sql_string = "SELECT name FROM sqlite_master WHERE type='table'"
        if self.verbose:
            print('sql> '+sql_string)
        self.cursor.execute(sql_string)
        table_names = [names[0] for names in self.cursor.fetchall()]
        return table_names

    def columns_in_table(self,tablename):
        """ Enumerate the names of the columns in the given table.

        It throws an error if the table does not exist.

        :param tablename:
        """
        sql_string = 'select * from '+tablename
        if self.verbose:
            print('sql> '+sql_string)
        self.cursor.execute(sql_string)
        colnames = [description[0] for description in self.cursor.description]
        return colnames

    def check_column_exists(self,tablename, column_name):
        """ Check if a column name exists within a table.

        :param tablename:
        :param column_name:
        """
        names = self.columns_in_table(tablename)
        return column_name in names

    def add_column(self,tablename, column_name, column_type):
        """ Adds a column named column_name and a given column_type to a table.
        """
        sql_string = "alter table {table} add column '{colname}' '{coltype}'"\
            .format(table=tablename,colname=column_name,coltype=column_type)
        if self.verbose:
            print('sql> '+sql_string)
        self.cursor.execute(sql_string)

    def create_table_from_dict(self,dictionary):
        """ Creates a table schema from a given dictionary.

        It mainly adds an ID (corresponding to the measurement ID) to the list
        of keys of the dictionary, and sets every key name into a different
        column.

        The dictionary must contain keys named 'user' and 'error'. This requirement
        arises from the use of the function "types_from_keys", which sets the type
        of the different columns in the table.

        The 'user' name should be a valid SQLITE table name. For some reason,
        names starting with a number (e.g. 606laser) might raise an exception.

        Once everything else is taken care of, it calls the DBHandler._create_table
        method to actually create a table.

        """
        tablename = dictionary["user"]   #see servers.server_node.convert_data()
        assert 'user' in dictionary, 'The dictionary should contain a "user" key'
        assert 'error' in dictionary, 'The dictionary should contain a "error" key'
        list_of_keys = list(dictionary)
        list_of_types = types_from_keys(list_of_keys)
        list_of_keys.append('ID')
        list_of_types.append('INTEGER')

        self._create_table(tablename, list_of_keys, list_of_types)
        self.commit()

    def add_data_from_dict(self, data_dict,observationID=0):
        """ Adds data from a dictionary to a table.

        The dictionary should, at least, have the key 'user' in it.

        We assume that the table already has columns named in the same way as
        the keys.

        :param data_dict:
        :return:
        """

        tablename = data_dict["user"]  #see servers.server_node.convert_data()

        list_of_keys = data_dict.keys()
        list_of_values = list(data_dict.values())

        keys_string = ','.join(list_of_keys)
        keys_string = 'ID,'+keys_string
        ### Form SQL string
        sql_string = "insert into {tablename}({key_list}) VALUES (?,"\
            .format(tablename=tablename,key_list=keys_string)
        sql_string += '?,'*len(list_of_keys)
        sql_string = sql_string[:-1]+')'

        if self.verbose:
            print('sql> '+sql_string)
        ### Execute SQL string
        list_of_values = [observationID]+list_of_values  #prepend the list with the observationID
        self.cursor.execute(sql_string,list_of_values)
        self.commit()

    def add_database_entry(self, dictionary):
        """ Method that adds a database entry corresponding to an
        observation.

        The dictionary should at least have a key named 'user'

        :param dictionary:
        :return:
        """

        # 1 - Check if lab has a corresponding table?  pass : add table
        # 2 - Add entry to observation list
        # 3 - Obtain observation_id from entry
        # 4 - Add entry in table with suitable name

        # 1: Check if table exists
        user = dictionary["user"]
        if not self.check_table_exists(user):
            # Creates new table with suitable properties
            # and adds an ID to the laboratories list
            self.create_table_from_dict(dictionary)
            labID = self._register_new_laboratory(user)
        else:
            labID = self.get_labID_by_name(user)

        # 2: Add entry to observation list
        key_list = ','.join(OBSERVATION_TABLE_COLNAMES)
        sql_string = 'insert into {tablename}({key_list}) VALUES(NULL,?)'\
            .format(tablename=self.observations_tablename,key_list=key_list)
        if self.verbose:
            print('sql> '+sql_string)
        self.cursor.execute(sql_string,(labID,))

        # 3: obtain observation ID
        observationID = self.cursor.lastrowid
        if self.verbose:
            print('observation id {}'.format(observationID))

        # 4: Add entry in table with suitable name
        self.add_data_from_dict(dictionary,observationID)

    def register_new_metadata(self, user, dictionary):
        """ Creates a new entry in the metadata table.

        The columns to be filled in are the time, the lab_id and a
        string with the JSON representation of the metadata dictionary.

        :param user: identification of the node
        :param dictionary: dictionary with some metadata. It can specify,
        for example, that the key 'ch1' corresponds to 'power of blue laser'

        :return:
        """
        # 1: Check if table exists
        if not self.check_table_exists(user):
            # Creates new table with suitable properties
            # and adds an ID to the laboratories list
            self.create_table_from_dict(dictionary)
            labID = self._register_new_laboratory(user)
        else:
            labID = self.get_labID_by_name(user)
        # 2: Add entry to metadata list
        key_list = ','.join(METADATA_TABLE_COLNAMES)
        sql_string = 'insert into {tablename}({key_list}) VALUES(?,?,?)'\
            .format(tablename=self.metadata_tablename,key_list=key_list)
        if self.verbose:
            print('sql> '+sql_string)
        self.cursor.execute(sql_string,(time.time(),labID,json.dumps(dictionary),))


    def read_table(self,tablename):
        self.cursor.execute('select * from {tablename}'\
                            .format(tablename=tablename))
        return self.cursor.fetchall()

    def commit(self):
        self.db.commit()

    def close(self):
        self.commit()
        self.cursor.close()
        self.db.close()

def types_from_keys(list_of_keys):
    """ Generates a list of data types from a list of keys from a dictionary.

    When we save the data to the different tables in the database, the values
    of most entries will be of type REAL, except those correponding to the 'user'
    (the name of the node) and 'error' (error status), which have types 'TEXT'
    and 'INTEGER' respectively.

    :param list_of_keys:
    :return:
    """
    type_list = len(list_of_keys)*['REAL']
    #Not all of the results are REAL: Replace 'user' and 'error' types
    position_of_user  = list_of_keys.index('user')
    position_of_error =  list_of_keys.index('error')
    type_list[position_of_user] = 'TEXT'
    type_list[position_of_error] = 'INTEGER'

    return type_list
