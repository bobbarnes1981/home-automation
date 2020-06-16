from flask import Flask
from flask import jsonify, render_template, request

from datetime import datetime

from plugin_system import PluginSystem
from plugin_temperature import PluginTemperature
from plugin_metoffice import PluginMetOffice, ApiMetOffice, ForecastFont
from plugin_hue import PluginHue, ApiHue
from plugin_datastore import PluginDataStore, DataStoreSqLite

app = Flask(__name__)

@app.route('/config/<string:plugin_name>', methods = ['GET', 'POST'])
def config(plugin_name):
    configs = plugins.keys()
    tab_template = 'blank.html'
    tab_data = {}
    if plugin_name == 'hue':
        tab_template = 'hue/config.html'
        tab_data = plugins['hue'].config(request)
    if plugin_name == 'metoffice':
        tab_template = 'metoffice/config.html'
        tab_data = plugins['metoffice'].config(request)
    if plugin_name == 'temperature':
        tab_template = 'temperature/config.html'
        tab_data = plugins['temperature'].config(request)
    return render_template('config.html', plugin_name = plugin_name, configs = configs, tab_template = tab_template, tab_data = tab_data)

@app.route('/metoffice/test')
def metoffice_test():
    weather_types = ApiMetOffice.weather_types
    weather_icons = ForecastFont.metoffice_icons
    return render_template('metoffice/test.html', weather_types = weather_types, weather_icons = weather_icons)

@app.route('/rooms/<int:room_id>')
def rooms_one(room_id):
    '''Show one room'''
    room = store.get_room(room_id)
    hue_group = hue.get_group(room['hue_group_id'])
    lights = hue.get_lights_in_group(room['hue_group_id'])
    temperature = plugins['temperature'].get_room_data(room['id'])
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
        room_temps[room['id']] = plugins['temperature'].get_dashboard_data(room)
        room_lights[room['id']] = plugins['hue'].get_dashboard_data(room)
    database = plugins['datastore'].get_dashboard_data()
    system = plugins['system'].get_dashboard_data()
    weather = plugins['metoffice'].get_dashboard_data()
    return render_template('dashboard.html', rooms = rooms, room_temps = room_temps, room_lights = room_lights, database = database, system = system, weather = weather)

store = DataStoreSqLite()

hue = ApiHue(store)

plugins = {
    'system': PluginSystem(),
    'datastore': PluginDataStore(store),
    'hue': PluginHue(store),
    'metoffice': PluginMetOffice(store),
    'temperature': PluginTemperature(store)
}

