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
    metoffice_locations = plugin_metoffice.get_observation_locations()
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
    temperature = store.get_one_data(room_id, 'temperature_c')
    if temperature:
        temperature['date'] = datetime.fromtimestamp(temperature['timestamp'])
    return render_template('rooms/one.html', room = room, lights = lights, temperature = temperature)

@app.route('/rooms/<int:room_id>/edit', methods = ['GET', 'POST'])
def rooms_edit(room_id):
    '''Edit one room'''
    if request.method == 'POST':
        store.update_room(room_id, request.form['name'], request.form['hue_group'])
    room = store.get_room(room_id)
    hue_groups = hue.get_groups()
    hue_groups[0] = {'name': ''}
    return render_template('rooms/edit.html', room = room, hue_groups = hue_groups)

@app.route('/rooms', methods = ['GET', 'POST'])
def rooms_all():
    '''List all rooms and allow adding a new room'''
    if request.method == 'POST':
        store.add_room(request.form['room_name'])
    rooms = store.get_rooms()
    return render_template('rooms/all.html', rooms = rooms)

@app.route('/api/rooms/<int:room_id>/data', methods = [ 'POST' ])
def api_rooms_data(room_id):
    '''Append a new data for the room'''
    # TODO: validate room id
    if request.method == 'POST':
        data = request.get_json()
        for k in data.keys():
            store.set_data(room_id, k, data[k])
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
        temps = store.get_many_data(room['id'], 'temperature_c', time.time() - (60*60*24))
        room_temps[room['id']] = temps
        room_lights[room['id']] = hue.get_lights_in_group(room['hue_group_id'])
    database = plugin_datastore.get_data()
    system = plugin_system.get_data()
    weather = plugin_metoffice.get_observation_data(store.get_config('metoffice_location'))
    return render_template('dashboard.html', rooms = rooms, room_temps = room_temps, room_lights = room_lights, database = database, system = system, weather = weather)

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

class DataStoreSqLite(object):

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

class PluginDataStore(object):

    def __init__(self, store):
        self.store = store

    def get_data(self):
        data = {}
        data['file_name'] = self.store.database
        data['file_size'] = os.stat(self.store.database).st_size
        (db_min, db_max) = self.store.get_minmax_dates()
        data['minmax'] = {
            'min': datetime.fromtimestamp(db_min),
            'max': datetime.fromtimestamp(db_max)
        }
        return data

class PluginSystem(object):

    def __init__(self, vcgencmd):
        self.vcgencmd = vcgencmd

    def get_data(self):
        data = {}
        data['cpu_perc'] = psutil.cpu_percent()
        data['cpu_temp'] = self.vcgencmd.measure_temp()
        data['root_data'] = psutil.disk_usage('/')
        data['mem_data'] = psutil.virtual_memory()
        return data

class PluginMetOffice(object):

    def __init__(self, api):
        self.api = api

    def get_latest_weather(self, data):
        now = datetime.now()
        today = now.strftime('%Y-%m-%dZ')
        minutes = now.hour * 60
        for period in data['SiteRep']['DV']['Location']['Period']:
            if period['value'] == datetime.now().strftime('%Y-%m-%dZ'):
                rep = period['Rep'][-1]
                return rep
        return []

    def get_observation_locations(self):
        return self.api.get_observation_locations()

    def get_observation_data(self, location_id):
        data = {}
        weather = self.api.get_observation(store.get_config('metoffice_location'))
        data['types'] = MetOffice.weather_types
        data['location'] = weather['SiteRep']['DV']['Location']['name']
        data['keys'] = weather['SiteRep']['Wx']['Param']
        data['data'] = self.get_latest_weather(weather)
        data['icons'] = ForecastFont.metoffice_icons
        return data

class MetOffice(object):

    base_url = 'datapoint.metoffice.gov.uk/public/data'
    datatype = 'json'

    weather_types = {
        'NA': 'Not available',
        '0': 'Clear night',
        '1': 'Sunny day',
        '2': 'Partly cloudy (night)',
        '3': 'Partly cloudy (day)',
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

store = DataStoreSqLite()
hue = Hue()
plugin_metoffice = PluginMetOffice(MetOffice())
plugin_system = PluginSystem(VCGenCmd())
plugin_datastore = PluginDataStore(store)

