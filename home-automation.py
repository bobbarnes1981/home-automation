from flask import Flask
from flask import render_template, request

import requests
import sqlite3
import time

app = Flask(__name__)

# TODO: 
#       configure sensors
#       assign sensors to rooms

@app.route('/')
def index():
    rooms = store.get_rooms()
    return render_template('index.html', rooms = rooms)

@app.route('/hue/config', methods = ['GET', 'POST'])
def hue_config():
    if request.method == 'POST':
        store.set_config('hue_username', request.form['hue_username'])
    hue_username = store.get_config('hue_username')
    return render_template('hue/config.html', hue_username = hue_username)

@app.route('/rooms/add', methods = ['GET', 'POST'])
def rooms_add():
    if request.method == 'POST':
        store.add_room(request.form['room_name'])
    rooms = store.get_rooms()
    return render_template('rooms/add.html', rooms = rooms)

@app.route('/rooms/config', methods = ['GET', 'POST'])
def rooms_config():
    if request.method == 'POST':
        rooms = store.get_rooms()
        for room in rooms:
            hue_group_id = request.form['room_{0}'.format(room[0])]
            store.update_room(room[0], room[1], hue_group_id)
    rooms = store.get_rooms()
    hue_groups = hue.get_groups()
    return render_template('rooms/config.html', rooms = rooms, hue_groups = hue_groups)

@app.route('/rooms/<int:room_id>')
def rooms_one(room_id):
    room = store.get_room(room_id)
    hue_group = hue.get_group(room['hue_group_id'])
    lights = []
    for hue_light in hue_group['lights']:
        light = hue.get_light(hue_light)
        lights.append(light)
    temperature = store.get_temperature(room_id)
    return render_template('rooms/one.html', room = room, lights = lights, temperature = temperature)

@app.route('/api/rooms/<int:room_id>/temperature', methods = [ 'POST' ])
def api_rooms_temperature(room_id):
    # TODO: validate room id
    if request.method == 'POST':
        data = request.get_json()
        store.set_temperature(room_id, data['temperature_c'])
        return 'success'

@app.route('/dashboard')
def dashboard():
    rooms = store.get_rooms()
    room_temps = {}
    for room in rooms:
        temps = store.get_temperatures(room['id'], time.time() - (60*60*24))
        room_temps[room['id']] = temps
    return render_template('dashboard.html', rooms = rooms, room_temps = room_temps)

def dictionary_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

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
                name TEXT UNIQUE,
                hue_group_id INTEGER
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS temperatures (
                timestamp INTEGER NOT NULL,
                room_id INTEGER NOT NULL,
                temperature REAL NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE
            );
        ''')

        cxn.commit()
        cxn.close()

    def get_config(self, key):
        cxn = sqlite3.connect(self.database)
        cxn.row_factory = dictionary_factory
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
        cxn.row_factory = dictionary_factory
        cur = cxn.cursor()

        cur.execute('''
            SELECT id, name, hue_group_id FROM rooms;
        ''')
        val = cur.fetchmany(999)
        
        cxn.close()
        
        return val

    def get_room(self, id):
        cxn = sqlite3.connect(self.database)
        cxn.row_factory = dictionary_factory
        cur = cxn.cursor()

        cur.execute('''
            SELECT id, name, hue_group_id FROM rooms WHERE id = :id;
        ''', {"id": id})
        val = cur.fetchone()
        
        cxn.close()
        
        return val

    def add_room(self, name):
        cxn = sqlite3.connect(self.database)
        cur = cxn.cursor()

        cur.execute('''
            INSERT INTO rooms (name) VALUES (:name);
        ''', {'name': name})

        cxn.commit()
        cxn.close()

    def update_room(self, id, name, hue_group_id):
        cxn = sqlite3.connect(self.database)
        cur = cxn.cursor()

        cur.execute('''
            UPDATE rooms SET name = :name, hue_group_id = :hue_group_id WHERE id = :id;
        ''', {'name': name, 'hue_group_id': hue_group_id, 'id': id})

        cxn.commit()
        cxn.close()

    def set_temperature(self, room_id, temperature):
        cxn = sqlite3.connect(self.database)
        cur = cxn.cursor()

        cur.execute('''
            INSERT INTO temperatures (
                timestamp, room_id, temperature
            ) VALUES (
                :timestamp, :room_id, :temperature
            );
        ''', {"timestamp": time.time(), "room_id": room_id, "temperature": temperature})

        cxn.commit()
        cxn.close()

    def get_temperature(self, room_id):
        cxn = sqlite3.connect(self.database)
        cxn.row_factory = dictionary_factory
        cur = cxn.cursor()

        cur.execute('''
            SELECT temperature, timestamp FROM temperatures WHERE room_id = :room_id ORDER BY timestamp DESC LIMIT 1;
        ''', {"room_id": room_id})

        val = cur.fetchone()

        if val:
            return val
        return None

    def get_temperatures(self, room_id, from_timestamp):
        cxn = sqlite3.connect(self.database)
        cxn.row_factory = dictionary_factory
        cur = cxn.cursor()

        cur.execute('''
            SELECT temperature, timestamp FROM temperatures WHERE room_id = :room_id AND timestamp > :timestamp ORDER BY timestamp;
        ''', {"room_id": room_id, "timestamp": from_timestamp})

        val = cur.fetchmany(1440)

        if val:
            return val
        return None

class Hue(object):

    DEVICE_TYPE = 'home-automation'

    def __init__(self, address):
        self.address = address

    def request_get(self, path):
        r = requests.get('http://{0}/api/{1}/{2}'.format(self.address, store.get_config('hue_username'), path))
        return r.json()

    def register(self, device_type):
        # post
        # /api
        # {"devicetype":device_type}

        # response
        # [{"success":{"username":user_name}}]
        pass

    def get_groups(self):
        return self.request_get('groups')

    def get_group(self, id):
        return self.request_get('groups/{0}'.format(id))

    def get_lights(self):
        return self.request_get('lights')

    def get_light(self, id):
        return self.request_get('lights/{0}'.format(id))

store = DataStore()
hue = Hue('192.168.0.175')

