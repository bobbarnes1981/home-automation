from flask import Flask
from flask import render_template, request

import requests
import sqlite3

app = Flask(__name__)

# TODO: configure hue
#       assign lights to rooms
#       configure sensors
#       assign sensors to rooms
#       manage rooms

@app.route('/')
def index():
    rooms = store.get_rooms()
    return render_template('index.html', rooms = rooms)

@app.route('/hue')
def hue():
    return 'hue {0}'.format(hue.groups())

@app.route('/room/<int:room_id>')
def rooms(room_id):
    #george_lights = [hue.light(16)]
    return render_template('room.html', lights = lights, temperature = temperature)

@app.route('/api/room/<int:room_id>/temperature', methods = [ 'POST' ])
def api_room_temperature(room_id):
    if request.method == 'POST':
        data = request.get_json()
        return '{0}'.format(data['temperature_c'])

class DataStore(object):

    database = 'database.db'

    def __init__(self):
        cxn = sqlite3.connect(self.database)
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
                name TEXT UNIQUE
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS temperatures (
                timestamp INTEGER NOT NULL,
                room_id INTEGER NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE
            );
        ''')

        cxn.commit()
        cxn.close()

    def get_config(self, key):
        cxn = sqlite3.connect(self.database)
        cur = cxn.cursor()

        cur.execute('''
            SELECT config_val FROM configurations WHERE config_key = :key;
        ''', {'key': key})
        val = cur.fetchone()
        
        cxn.close()
        
        if val:
            return val[0]
        return None

    def set_config(self, key, value):
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

        cxn = sqlite3.connect(self.database)
        cur = cxn.cursor()

        cur.execute(query, {'key':key, 'val':value})

        cxn.commit()
        cxn.close()

    def get_rooms(self):
        cxn = sqlite3.connect(self.database)
        cur = cxn.cursor()

        cur.execute('''
            SELECT id, name FROM rooms;
        ''')
        val = cur.fetchmany()
        
        cxn.close()
        
        return val

    def add_room(self, name):
        cxn = sqlite3.connect(self.database)
        cur = cxn.cursor()

        cur.execute('''
            INSERT INTO rooms (name) VALUES (:name);
        ''', {'name':name})

        cxn.commit()
        cxn.close()

class Hue(object):

    DEVICE_TYPE = 'home-automation'

    def __init__(self, address, username):
        self.address = address
        self.username = username

    def request_get(self, path):
        r = requests.get('http://{0}/api/{1}/{2}'.format(self.address, self.username, path))
        return r.json()

    def register(self, device_type):
        # post
        # /api
        # {"devicetype":device_type}

        # response
        # [{"success":{"username":user_name}}]
        pass

    def groups(self):
        return self.request_get('groups')

    def group(self, id):
        return self.request_get('groups/{0}'.format(id))

    def lights(self):
        return self.request_get('lights')

    def light(self, id):
        return self.request_get('lights/{0}'.format(id))

store = DataStore()
hue = Hue('192.168.0.175', store.get_config('hue_username'))

