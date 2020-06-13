from flask import Flask
from flask import jsonify, render_template, request

from datetime import datetime
import os
import psutil
import requests
import sqlite3
import subprocess
import time

app = Flask(__name__)

@app.route('/hue/config', methods = ['GET', 'POST'])
def hue_config():
    '''Configure the hue address and username'''
    if request.method == 'POST':
        store.set_config('hue_address', request.form['hue_address'])
        store.set_config('hue_username', request.form['hue_username'])
    hue_address = store.get_config('hue_address')
    hue_username = store.get_config('hue_username')
    return render_template('hue/config.html', hue_address = hue_address, hue_username = hue_username)

@app.route('/metoffice/config', methods = ['GET', 'POST'])
def metoffice_config():
    '''Configure the met office key and location'''
    if request.method == 'POST':
        store.set_config('metoffice_key', request.form['metoffice_key'])
        store.set_config('metoffice_location', request.form['metoffice_location'])
    metoffice_key = store.get_config('metoffice_key')
    metoffice_location = store.get_config('metoffice_location')
    metoffice_locations = metoffice.get_observation_locations()
    return render_template('metoffice/config.html', metoffice_key = metoffice_key, metoffice_location = metoffice_location, metoffice_locations = metoffice_locations)

@app.route('/metoffice/test')
def metoffice_test():
    weather_types = MetOffice.weather_types
    weather_icons = ForecastFont.metoffice_icons
    return render_template('metoffice/test.html', weather_types = weather_types, weather_icons = weather_icons)

@app.route('/rooms/config', methods = ['GET', 'POST'])
def rooms_config():
    '''Configure the relationship between the hue groups and rooms'''
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
    '''Show one room'''
    room = store.get_room(room_id)
    hue_group = hue.get_group(room['hue_group_id'])
    lights = hue.get_lights_in_group(room['hue_group_id'])
    temperature = store.get_temperature(room_id)
    if temperature:
        temperature['date'] = datetime.fromtimestamp(temperature['timestamp'])
    return render_template('rooms/one.html', room = room, lights = lights, temperature = temperature)

@app.route('/rooms', methods = ['GET', 'POST'])
def rooms_all():
    '''List all rooms and allow adding a new room'''
    if request.method == 'POST':
        store.add_room(request.form['room_name'])
    rooms = store.get_rooms()
    return render_template('rooms/all.html', rooms = rooms)

@app.route('/api/rooms/<int:room_id>/temperature', methods = [ 'POST' ])
def api_rooms_temperature(room_id):
    '''Append a new temperature reading for the room'''
    # TODO: validate room id
    if request.method == 'POST':
        data = request.get_json()
        store.set_temperature(room_id, data['temperature_c'])
        return jsonify('success')

@app.route('/api/lights/<int:light_id>', methods = [ 'PUT' ])
def api_lights(light_id):
    '''Set the state of the specified hue light'''
    # TODO: validate light id?
    if request.method == 'PUT':
        data = request.get_json()
        hue.set_light(light_id, data['state'])
        return jsonify('success')

@app.route('/')
def dashboard():
    '''A collection of information'''
    rooms = store.get_rooms()
    room_temps = {}
    room_lights = {}
    for room in rooms:
        temps = store.get_temperatures(room['id'], time.time() - (60*60*24))
        room_temps[room['id']] = temps
        room_lights[room['id']] = hue.get_lights_in_group(room['hue_group_id'])
    db_file_size = os.stat(DataStore.database).st_size
    cpu_perc = psutil.cpu_percent()
    cpu_temp = vcgc.measure_temp()
    root_data = psutil.disk_usage('/')
    mem_data = psutil.virtual_memory()
    weather = metoffice.get_observation(store.get_config('metoffice_location'))
    weather_types = MetOffice.weather_types
    weather_location = weather['SiteRep']['DV']['Location']['name']
    weather_keys = weather['SiteRep']['Wx']['Param']
    weather_data = get_latest_weather(weather)
    weather_icons = ForecastFont.metoffice_icons
    return render_template('dashboard.html', rooms = rooms, room_temps = room_temps, room_lights = room_lights, db_file_name = DataStore.database, db_file_size = db_file_size, disk_total = root_data.total, disk_used = root_data.used, disk_free = root_data.free, mem_total = mem_data.total, mem_used = mem_data.used, mem_avail = mem_data.available, cpu_perc = cpu_perc, cpu_temp = cpu_temp, weather_types = weather_types, weather_location = weather_location, weather_keys = weather_keys, weather_data = weather_data, weather_icons = weather_icons)

def get_latest_weather(data):
    now = datetime.now()
    today = now.strftime('%Y-%m-%dZ')
    minutes = now.hour * 60
    for period in data['SiteRep']['DV']['Location']['Period']:
        if period['value'] == datetime.now().strftime('%Y-%m-%dZ'):
            rep = period['Rep'][-1]
            return rep
    return []

def dictionary_factory(cursor, row):
    '''Load the sqlite row into a dictionary'''
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class VCGenCmd(object):

    def __init__(self):
        pass

    def get_raw(self, command):
        return subprocess.check_output(['vcgencmd', command])

    def measure_temp(self):
        '''call the measure_temp command on vcgencmd'''
        return self.get_raw('measure_temp')[5:9]

class ForecastFont(object):

    metoffice_icons = {
        '0': ['icon-moon'],
        '1': ['icon-sun'],
        '2': ['basecloud', 'icon-night'],
        '3': ['basecloud', 'icon-sunny'],

        '5': ['icon-mist'],
        '6': ['icon-mist'],
        '7': ['icon-cloud'],
        '8': ['icon-overcast'],
        '9': ['basecloud', 'icon-showers', 'icon-night'],
        '10': ['basecloud', 'icon-showers', 'icon-sunny'],
        '11': ['basecloud', 'icon-drizzle'],
        '12': ['basecloud', 'icon-showers'],
        '13': ['basecloud', 'icon-rainy', 'icon-night'],
        '14': ['basecloud', 'icon-rainy', 'icon-sunny'],
        '15': ['basecloud', 'icon-rainy'],
        '16': ['basecloud', 'icon-sleet', 'icon-night'],
        '17': ['basecloud', 'icon-sleet', 'icon-sunny'],
        '18': ['basecloud', 'icon-sleet'],
        '19': ['basecloud', 'icon-hail', 'icon-night'],
        '20': ['basecloud', 'icon-hail', 'icon-sunny'],
        '21': ['basecloud', 'icon-hail'],
        '22': ['basecloud', 'icon-snowy', 'icon-night'],
        '23': ['basecloud', 'icon-snowy', 'icon-sunny'],
        '24': ['basecloud', 'icon-snowy'],
        '25': ['basecloud', 'icon-snowy', 'icon-night'],
        '26': ['basecloud', 'icon-snowy', 'icon-sunny'],
        '27': ['basecloud', 'icon-snowy'],
        '28': ['basethundercloud', 'icon-thunder', 'icon-night'],
        '29': ['basethundercloud', 'icon-thunder', 'icon-sunny'],
        '30': ['basethundercloud', 'icon-thunder'],
    }

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

    def set_temperature(self, room_id, temperature):
        '''Append a new temperature reading for the room with the current timestamp'''
        cxn = self.connect(None)
        cur = cxn.cursor()

        cur.execute('''
            INSERT INTO datastore (
                timestamp, room_id, data_key, data_val
            ) VALUES (
                :timestamp, :room_id, :data_key, :temperature
            );
        ''', {"timestamp": time.time(), "room_id": room_id, "data_key": 'temperature_c', "temperature": temperature})

        cxn.commit()
        cxn.close()

    def get_temperature(self, room_id):
        '''Get the last temperature for the room'''
        cxn = self.connect(dictionary_factory)
        cur = cxn.cursor()

        cur.execute('''
            SELECT data_val AS temperature, timestamp FROM datastore WHERE room_id = :room_id AND data_key = :data_key ORDER BY timestamp DESC LIMIT 1;
        ''', {"room_id": room_id, "data_key": 'temperature_c'})

        val = cur.fetchone()

        if val:
            return val
        return None

    def get_temperatures(self, room_id, from_timestamp):
        '''Get the temperatures for the reoom between now and from_timestamp'''
        cxn = self.connect(dictionary_factory)
        cur = cxn.cursor()

        cur.execute('''
            SELECT data_val AS temperature, timestamp FROM datastore WHERE room_id = :room_id AND data_key = :data_key AND timestamp > :timestamp ORDER BY timestamp;
        ''', {"room_id": room_id, "data_key": 'temperature_c', "timestamp": from_timestamp})

        val = cur.fetchmany(1440)

        if val:
            return val
        return None

class Hue(object):

    DEVICE_TYPE = 'home-automation'

    def __init__(self):
        pass

    def url(self, path):
        '''Build the hue api url'''
        return 'http://{0}/api/{1}/{2}'.format(store.get_config('hue_address'), store.get_config('hue_username'), path)

    def request_get(self, path):
        '''Execute a get request and return the json'''
        r = requests.get(self.url(path))
        return r.json()

    def request_put(self, path, json):
        '''Execute a put request and return the json'''
        r = requests.put(self.url(path), json = json)
        return r.json()

    def register(self, device_type):
        '''Register the username with the hue hub'''
        # post
        # /api
        # {"devicetype":device_type}

        # response
        # [{"success":{"username":user_name}}]
        pass

    def get_groups(self):
        '''Get all the groups from the hue hub'''
        return self.request_get('groups')

    def get_group(self, group_id):
        '''Get the specified group from the hue hub'''
        return self.request_get('groups/{0}'.format(group_id))

    def get_lights_in_group(self, group_id):
        '''Get all the lights for the specified group'''
        lights = {}
        if group_id:
            group = self.get_group(group_id)
            for light_id in group['lights']:
                light = self.get_light(light_id)
                lights[light_id] = light
        return lights

    def get_lights(self):
        '''Get all the lights from the hue hub'''
        return self.request_get('lights')

    def get_light(self, light_id):
        '''Get the specified light from the hue hub'''
        return self.request_get('lights/{0}'.format(light_id))

    def set_light(self, light_id, state):
        '''Set the state of the specified light'''
        return self.request_put('lights/{0}/state'.format(light_id), {"on": state})

class MetOffice(object):

    base_url = 'datapoint.metoffice.gov.uk/public/data'
    datatype = 'json'

    weather_types = {
        'NA': 'Not available',
        '0': 'Clear night',
        '1': 'Sunny day',
        '2': 'Partly cloudy (night)',
        '3': 'Partly cloud (day)',
        '4': 'Not used',
        '5': 'Mist',
        '6': 'Fog',
        '7': 'Cloudy',
        '8': 'Overcast',
        '9': 'Light rain shower (night)',
        '10': 'Light rain shower (day)',
        '11': 'Drizzle',
        '12': 'Light rain',
        '13': 'Heavy rain shower (night)',
        '14': 'Heavy rain shower (day)',
        '15': 'Heavy rain',
        '16': 'Sleet shower (night)',
        '17': 'Sleet shower (day)',
        '18': 'Sleet',
        '19': 'Hail shower (night)',
        '20': 'Hail shower (day)',
        '21': 'Hail',
        '22': 'Light snow shower (night)',
        '23': 'Light snow shower (day)',
        '24': 'Light snow',
        '25': 'Heavy snow shower (night)',
        '26': 'Heavy snow shower (day)',
        '27': 'Heavy snow',
        '28': 'Thunder shower (night)',
        '29': 'Thunder shower (day)',
        '30': 'Thunder',
    }

    def __init__(self):
        pass

    def url(self, path):
        '''Build the met office data point url'''
        return 'http://{0}/{1}?res=hourly&key={2}'.format(self.base_url, path, store.get_config('metoffice_key'))

    def request_get(self, path):
        '''Execute a get request and return the json'''
        r = requests.get(self.url(path))
        return r.json()

    def get_observation_locations(self):
        '''Get a list of observation locations'''
        return self.request_get('/val/wxobs/all/{0}/sitelist'.format(self.datatype))

    def get_observation(self, id):
        '''Get the observations for the specified location'''
        return self.request_get('/val/wxobs/all/{0}/{1}'.format(self.datatype, id))

store = DataStore()
hue = Hue()
metoffice = MetOffice()
vcgc = VCGenCmd()

