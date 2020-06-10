from flask import Flask
from flask import jsonify, render_template, request

from datetime import datetime
import os
import psutil
import requests
import sqlite3
import time

app = Flask(__name__)

@app.route('/hue/config', methods = ['GET', 'POST'])
def hue_config():
    if request.method == 'POST':
        store.set_config('hue_address', request.form['hue_address'])
        store.set_config('hue_username', request.form['hue_username'])
    hue_address = store.get_config('hue_address')
    hue_username = store.get_config('hue_username')
    return render_template('hue/config.html', hue_address = hue_address, hue_username = hue_username)

@app.route('/metoffice/config', methods = ['GET', 'POST'])
def metoffice_config():
    if request.method == 'POST':
        store.set_config('metoffice_key', request.form['metoffice_key'])
        store.set_config('metoffice_location', request.form['metoffice_location'])
    metoffice_key = store.get_config('metoffice_key')
    metoffice_location = store.get_config('metoffice_location')
    metoffice_locations = metoffice.get_observation_locations()
    return render_template('metoffice/config.html', metoffice_key = metoffice_key, metoffice_location = metoffice_location, metoffice_locations = metoffice_locations)

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
            hue_group_id = request.form['room_{0}'.format(room['id'])]
            store.update_room(room['id'], room['name'], hue_group_id)
    rooms = store.get_rooms()
    hue_groups = hue.get_groups()
    hue_groups[0] = {'name': ''}
    return render_template('rooms/config.html', rooms = rooms, hue_groups = hue_groups)

@app.route('/rooms/<int:room_id>')
def rooms_one(room_id):
    room = store.get_room(room_id)
    hue_group = hue.get_group(room['hue_group_id'])
    lights = {}
    if room['hue_group_id']:
        for hue_light in hue_group['lights']:
            light = hue.get_light(hue_light)
            lights[hue_light] = light
    temperature = store.get_temperature(room_id)
    if temperature:
        temperature['date'] = datetime.fromtimestamp(temperature['timestamp'])
    return render_template('rooms/one.html', room = room, lights = lights, temperature = temperature)

@app.route('/rooms')
def rooms_all():
    rooms = store.get_rooms()
    return render_template('rooms/all.html', rooms = rooms)

@app.route('/api/rooms/<int:room_id>/temperature', methods = [ 'POST' ])
def api_rooms_temperature(room_id):
    # TODO: validate room id
    if request.method == 'POST':
        data = request.get_json()
        store.set_temperature(room_id, data['temperature_c'])
        return jsonify('success')

@app.route('/api/lights/<int:light_id>', methods = [ 'PUT' ])
def api_lights(light_id):
    # TODO: validate light id?
    if request.method == 'PUT':
        data = request.get_json()
        hue.set_light(light_id, data['state'])
        return jsonify('success')

@app.route('/')
def dashboard():
    rooms = store.get_rooms()
    room_temps = {}
    room_lights = {}
    for room in rooms:
        temps = store.get_temperatures(room['id'], time.time() - (60*60*24))
        room_temps[room['id']] = temps
        if room['hue_group_id']:
            hue_group = hue.get_group(room['hue_group_id'])
            room_lights[room['id']] = {}
            for hue_light in hue_group['lights']:
                light = hue.get_light(hue_light)
                room_lights[room['id']][hue_light] = light
    db_file_size = os.stat(DataStore.database).st_size
    root_data = psutil.disk_usage('/')
    weather = metoffice.get_observation(store.get_config('metoffice_location'))
    return render_template('dashboard.html', rooms = rooms, room_temps = room_temps, room_lights = room_lights, db_file_name = DataStore.database, db_file_size = db_file_size, disk_total = root_data.total, disk_used = root_data.used, disk_free = root_data.free, weather = weather)

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

    def __init__(self):
        pass

    def url(self, path):
        return 'http://{0}/api/{1}/{2}'.format(store.get_config('hue_address'), store.get_config('hue_username'), path)

    def request_get(self, path):
        r = requests.get(self.url(path))
        return r.json()

    def request_put(self, path, json):
        r = requests.put(self.url(path), json = json)
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

    def set_light(self, id, state):
        return self.request_put('lights/{0}/state'.format(id), {"on": state})

class MetOffice(object):

    base_url = 'datapoint.metoffice.gov.uk/public/data'
    datatype = 'json'

    def __init__(self):
        pass

    def url(self, path):
        return 'http://{0}/{1}?res=hourly&key={2}'.format(self.base_url, path, store.get_config('metoffice_key'))

    def request_get(self, path):
        r = requests.get(self.url(path))
        return r.json()

    def get_observation_locations(self):
        return self.request_get('/val/wxobs/all/{0}/sitelist'.format(self.datatype))

    def get_observation(self, id):
        return self.request_get('/val/wxobs/all/{0}/{1}'.format(self.datatype, id))

store = DataStore()
hue = Hue()
metoffice = MetOffice()

