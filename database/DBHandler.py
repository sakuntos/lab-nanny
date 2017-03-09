import sqlite3

LAB_TABLE_COLNAMES = ['_id','labNAME']
LAB_TABLE_COLTYPES = ['INTEGER PRIMARY KEY AUTOINCREMENT','TEXT']
OBSERVATION_TABLE_COLNAMES = ['_id','labID']
OBSERVATION_TABLE_COLTYPES = ['INTEGER PRIMARY KEY AUTOINCREMENT','INTEGER']

class DBHandler(object):
    def __init__(self, db_name='example.db'):
        self.db = sqlite3.connect(db_name)
        self.cursor = self.db.cursor()

        try:
            self.cursor.execute('''CREATE TABLE data (date text, lab text, json_obj text)''')
        except sqlite3.OperationalError as err:
            if err.args[0] is 'table data already exists':
                pass


    def add_data(self,time,user,dict_JSON_dump):
        self.cursor.execute("insert into data values (?,?,?)", (time,user,dict_JSON_dump))

    def commit(self):
        self.db.commit()

    def close(self):
        self.commit()
        self.cursor.close()
        self.db.close()


class DBHandler_complex(object):
    def __init__(self, db_name='example.db',verbose=False):
        self.db = sqlite3.connect(db_name)
        self.cursor = self.db.cursor()
        self.labs_tablename = 'laboratories'
        self.observations_tablename = 'observation_list'
        self.verbose=verbose

        #If these table names exist, nothing will happen
        self._create_table(self.labs_tablename,
                           column_names=LAB_TABLE_COLNAMES,
                           column_types=LAB_TABLE_COLTYPES)
        self._create_table(self.observations_tablename,
                           column_names=OBSERVATION_TABLE_COLNAMES,
                           column_types=OBSERVATION_TABLE_COLTYPES)

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
        return self.cursor.lastrowid

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

        """
        tablename = dictionary["user"]   #see servers.server_node.convert_data()
        list_of_keys = list(dictionary)
        list_of_types = types_from_keys(list_of_keys)
        list_of_keys.append('ID')
        list_of_types.append('INTEGER')

        self._create_table(tablename, list_of_keys, list_of_types)
        self.commit()

    def add_data_from_dict(self, data_dict,observationID=0):
        """ Adds data from a dictionary to a table.

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
            print(user)

        # 2: Add entry to observation list
        key_list = ','.join(OBSERVATION_TABLE_COLNAMES)
        sql_string = 'insert into {tablename}({key_list}) VALUES(NULL,?)'\
            .format(tablename=self.observations_tablename,key_list=key_list)
        if self.verbose:
            print('sql> '+sql_string)
        print(labID)
        self.cursor.execute(sql_string,(labID,))
        # 3: obtain observation ID
        observationID = self.cursor.lastrowid
        if self.verbose:
            print('observation id {}'.format(observationID))

        # 4: Add entry in table with suitable name
        self.add_data_from_dict(dictionary,observationID)



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
    type_list = len(list_of_keys)*['REAL']
    #Not all of the results are REAL: Replace 'user' and 'error' types
    position_of_user  = list_of_keys.index('user')
    position_of_error =  list_of_keys.index('error')
    type_list[position_of_user] = 'TEXT'
    type_list[position_of_error] = 'INTEGER'

    return type_list
