import sqlite3


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





def initialise_table():
        self.c.execute('''CREATE TABLE data (date text, lab text, json_obj text)''')
