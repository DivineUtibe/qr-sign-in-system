import sqlite3

DATABASE = 'database.db'

def init_db():
    connection = sqlite3.connect(DATABASE)
    
    with open('schema.sql') as f:
        connection.executescript(f.read())
    
    connection.close()

if __name__ == '__main__':
    init_db()
