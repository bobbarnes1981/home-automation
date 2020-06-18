from datetime import datetime
import os
import sqlite3
import time

class PluginDataStore(object):

    def __init__(self, store):
        self.store = store

    def get_dashboard_room_data(self, room):
        return None

    def get_dashboard_data(self):
        data = {}
        data['file_name'] = self.store.database
        data['file_size'] = os.stat(self.store.database).st_size
        (db_min, db_max) = self.store.get_minmax_dates()
        data['minmax'] = {
            'min': datetime.fromtimestamp(db_min),
            'max': datetime.fromtimestamp(db_max)
        }
        data['days'] = (db_max - db_min) / 60 / 60 / 24;
        return data

    def config(self, request):
        if request.method == 'POST':
            pass
        tab_data = {}
        return tab_data

class DataStoreSqLite(object):

    database = 'database.db'

    def __init__(self):
        cxn = self.connect(None)
        cur = cxn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS configurations (
                config_key TEXT PRIMARY KEY UNIQUE,
                config_val TEXT
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                hue_group_id INTEGER
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS datastore (
                timestamp INTEGER NOT NULL,
                room_id INTEGER NOT NULL,
                data_key TEXT NOT NULL,
                data_val REAL NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE
            );
        ''')

        cxn.commit()
        cxn.close()

    def connect(self, row_factory):
        '''Connect and optionally set the row factory'''
        cxn = sqlite3.connect(self.database)
        if row_factory:
            cxn.row_factory = row_factory
        return cxn

    def get_config(self, key):
        '''Get the specified config value'''
        cxn = self.connect(dictionary_factory)
        cur = cxn.cursor()

        cur.execute('''
            SELECT config_val FROM configurations WHERE config_key = :key;
        ''', {'key': key})
        val = cur.fetchone()
        
        cxn.close()
        
        if val:
            return val['config_val']
        return None

    def set_config(self, key, value):
        '''Set the specified config value'''
        if self.get_config(key) == None:
            query = '''
                INSERT INTO configurations (
                    config_key, config_val
                ) VALUES (
                    :key, :val
                );
            '''
        else:
            query = '''
                UPDATE configurations SET config_val = :val WHERE config_key = :key;
            '''

        cxn = self.connect(None)
        cur = cxn.cursor()

        cur.execute(query, {'key':key, 'val':value})

        cxn.commit()
        cxn.close()

    def get_rooms(self):
        '''Get all the rooms'''
        cxn = self.connect(dictionary_factory)
        cur = cxn.cursor()

        cur.execute('''
            SELECT id, name, hue_group_id FROM rooms;
        ''')
        val = cur.fetchmany(999)
        
        cxn.close()
        
        return val

    def get_room(self, room_id):
        '''Get a single room'''
        cxn = self.connect(dictionary_factory)
        cur = cxn.cursor()

        cur.execute('''
            SELECT id, name, hue_group_id FROM rooms WHERE id = :id;
        ''', {"id": room_id})
        val = cur.fetchone()
        
        cxn.close()
        
        return val

    def add_room(self, name):
        '''Add a room with the specified name'''
        cxn = self.connect(None)
        cur = cxn.cursor()

        cur.execute('''
            INSERT INTO rooms (name) VALUES (:name);
        ''', {'name': name})

        cxn.commit()
        cxn.close()

    def update_room(self, room_id, name, hue_group_id):
        '''Update the room with the specified id'''
        cxn = self.connect(None)
        cur = cxn.cursor()

        cur.execute('''
            UPDATE rooms SET name = :name, hue_group_id = :hue_group_id WHERE id = :id;
        ''', {'name': name, 'hue_group_id': hue_group_id, 'id': room_id})

        cxn.commit()
        cxn.close()

    def set_data(self, room_id, data_key, data_val):
        '''Append a new data reading for the room with the current timestamp'''
        cxn = self.connect(None)
        cur = cxn.cursor()

        cur.execute('''
            INSERT INTO datastore (
                timestamp, room_id, data_key, data_val
            ) VALUES (
                :timestamp, :room_id, :data_key, :data_val
            );
        ''', {"timestamp": time.time(), "room_id": room_id, "data_key": data_key, "data_val": data_val})

        cxn.commit()
        cxn.close()

    def get_one_data(self, room_id, data_key):
        '''Get the last data for the room'''
        cxn = self.connect(dictionary_factory)
        cur = cxn.cursor()

        cur.execute('''
            SELECT data_val, timestamp FROM datastore WHERE room_id = :room_id AND data_key = :data_key ORDER BY timestamp DESC LIMIT 1;
        ''', {"room_id": room_id, "data_key": data_key})

        val = cur.fetchone()

        if val:
            return val
        return None

    def get_many_data(self, room_id, data_key, from_timestamp):
        '''Get the data for the reoom between now and from_timestamp'''
        cxn = self.connect(dictionary_factory)
        cur = cxn.cursor()

        cur.execute('''
            SELECT data_val, timestamp FROM datastore WHERE room_id = :room_id AND data_key = :data_key AND timestamp > :timestamp ORDER BY timestamp;
        ''', {"room_id": room_id, "data_key": data_key, "timestamp": from_timestamp})

        val = cur.fetchmany(1440)

        if val:
            return val
        return None

    def get_minmax_dates(self):
        '''Get the minimum and maximum dates in the data store'''
        cxn = self.connect(None)
        cur = cxn.cursor();

        cur.execute('''
            SELECT MIN(timestamp) AS min, MAX(timestamp) AS max FROM datastore;
        ''')

        val = cur.fetchone()

        return val

def dictionary_factory(cursor, row):
    '''Load the sqlite row into a dictionary'''
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

