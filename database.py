#%%
import sqlite3
import numpy as np


def adapt_tuple(tuple_val):
    return str(tuple_val)

def adapt_nparray(array_val):
    return array_val.tobytes()

def convert_tuple(tuple_str):
    tuple_str = tuple_str.replace('(', '').replace(')', '').strip()
    return tuple(map(float, tuple_str.split(', ')))

def convert_nparray(array_blob):
    return np.frombuffer(array_blob, dtype=np.complex128).reshape((2, 2))

sqlite3.register_adapter(tuple, adapt_tuple)
sqlite3.register_converter('TUPLE', convert_tuple)
sqlite3.register_adapter(np.ndarray, adapt_nparray)
sqlite3.register_converter('NPARRAY', convert_nparray)



class Datebase:
    def __init__(self, DB_file) :
        self.connect = sqlite3.connect(DB_file, detect_types=sqlite3.PARSE_DECLTYPES)
        self.connect.execute("PRAGMA foreign_keys = ON;")
        self.cursor = self.connect.cursor()
        self.cursor.execute('PRAGMA foreign_keys = 1')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Info 
                            (ind_file TEXT, 
                            material_1 TEXT, 
                            material_2 TEXT, 
                            period_x REAL, 
                            period_y REAL,
                            harmonics TUPLE)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Launch 
                            (lid INTEGER PRIMARY KEY, 
                            wavelength REAL,
                            direct REAL,
                            theta REAL,
                            phi REAL,
                            UNIQUE(wavelength, direct, theta, phi))''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Variable 
                            (vid INTEGER PRIMARY KEY)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS Jones 
                            (lid INTEGER, 
                            vid INTEGER, 
                            order_dmn TUPLE, 
                            matrix NPARRAY,
                            FOREIGN KEY(lid) REFERENCES Launch(lid) ON DELETE CASCADE ON UPDATE CASCADE,
                            FOREIGN KEY(vid) REFERENCES Variable(vid) ON DELETE CASCADE ON UPDATE CASCADE)''')
        self.connect.commit()

        self.cursor.execute('PRAGMA table_info(Variable)')
        self.variable_items = [info[1] for info in self.cursor.fetchall()][1:]

    def add_variable(self, variables, default=None):
        reunique = False
        #check existing variables
        self.cursor.execute('SELECT COUNT(*) FROM Variable')
        count = self.cursor.fetchone()[0]
        new_variables = set(variables) - set(self.variable_items)
        if len(new_variables) == 0:
            print(f'variable exists {self.variable_items}')
        #if the variable don't exist in the column, it will be added.
        elif not self.variable_items or count == 0:#columns is empty
            for var in new_variables:
                self.cursor.execute(f'ALTER TABLE Variable ADD COLUMN {var} REAL')
            self.connect.commit()
            self.variable_items += new_variables
            reunique = True
        #if the table isn't empty, the added column is filled the default value.
        elif count != 0 and default is not None:    #variable exsits
            if len(new_variables) != len(default):
                common_vars = set(variables) & set(self.variable_items)
                raise ValueError(f'{common_vars} are repeat')
            else:  #add variable and default value
                for var in new_variables:
                    self.cursor.execute(f'ALTER TABLE Variable ADD COLUMN {var} REAL')
                self.connect.commit()

                for var, value in zip(new_variables, default):
                    self.cursor.execute(f'UPDATE Variable SET {var} = ?', (value,))
                self.connect.commit()
                self.variable_items += new_variables
                reunique = True
        else:
            raise ValueError('The table Variable exists. If a new variable needs to be added, a default value must be provided.')
        
        if reunique:
            items = ','.join(self.variable_items)
            items_type = ' REAL,'.join(self.variable_items) + ' REAL'
            self.cursor.execute(f'''CREATE TABLE IF NOT EXISTS NewVariable 
                                (vid INTEGER PRIMARY KEY,
                                {items_type},
                                UNIQUE({items}))''')

            self.cursor.execute(f"INSERT INTO NewVariable ({items}) SELECT {items} FROM Variable")
            self.cursor.execute("DROP TABLE Variable")
            self.cursor.execute("ALTER TABLE NewVariable RENAME TO Variable")
            self.connect.commit()

    def insert(self,table,data):
        if table == 'Info':
            items = 'ind_file,material_1,material_2,period_x,period_y,harmonics'
            placeholder = '?,?,?,?,?,?'
        elif table == 'Launch':
            items = 'wavelength,direct,theta,phi'
            placeholder = '?,?,?,?'
        elif table == 'Variable':
            placeholder = ','.join(['?']*len(self.variable_items))
            items = str(self.variable_items).replace('[', '').replace(']', '').replace('\'', '').strip()
        elif table == 'Jones':
            items = '(lid,vid,order_mn,jones_matrix)'
            placeholder = '?,?,?,?'
        self.cursor.executemany(f'INSERT OR IGNORE INTO {table}({items}) values({placeholder})', data)
        self.connect.commit()

    def insert_jones(self,data):
        launch,variable,jones = data[:,:4],data[:,4:-2],data[:,-2:]
        self.insert('Launch',launch)
        lid_list = [self.select('Launch',items = ['wavelength','direct','theta','phi'], values = launch_i)[0][0] for launch_i in launch]
        self.insert('Variable',variable)
        vid_list = [self.select('Variable',items = self.variable_items, values = variable_i)[0][0] for variable_i in variable]
        #unfinish

        return lid_list,vid_list

    def select(self,table,items = [], values = []):
        conditions = 'WHERE '+' AND '.join([item+ ' = ?' for item in items]) if items else ''
        self.cursor.execute(f'SELECT * FROM {table} {conditions}', values)
        return self.cursor.fetchall()

    def close(self):
        self.connect.close()
# %%
DB = Datebase('test.db')
DB.add_variable(['Height','Duty'])
#%%
DB.add_variable(['RI'],[1.9])

# %%
DB.insert('Info',[['a','b','c',0.300,0.200,(8,0)]])
DB.insert('Launch',[[0.525,1,0,0],[0.525,1,10,10]])
DB.insert('Variable',[[0.06,0.5,1.9],[0.05,0.5,1.9]])
# %%
DB.close()
# %%
DB.insert_jones(np.asarray([[0.525,1,10,10,0.06,0.5,1.9,0,0],[0.525,1,10,10,0.05,0.5,1.9,0,0],
                            [0.525,1,0,0,0.05,0.5,1.9,0,0]]))

# %%
