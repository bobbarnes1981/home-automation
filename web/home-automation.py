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
    if plugin_name not in configs:
        plugin_name = configs[0]
    tab_template = '{0}/config.html'.format(plugin_name)
    tab_data = plugins[plugin_name].config(request)
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
    lights = plugins['hue'].get_room_data(room)
    temperature = plugins['temperature'].get_room_data(room)
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
    room_data = {}
    data = {}
    for plugin_name in plugins.keys():
        room_data[plugin_name] = {}
        for room in rooms:
            room_data[plugin_name][room['id']] = plugins[plugin_name].get_dashboard_room_data(room)
        data[plugin_name] = plugins[plugin_name].get_dashboard_data()
    rows = [
        {
            'name': '',
            'cards': [
                {
                    'name': 'Temperature',
                    'width': '8',
                    'template': 'temperature/graph.html'
                },
                {
                    'name': 'Weather {0}:00'.format(int(data['metoffice']['data']['$'])/60),
                    'width': '4',
                    'template': 'metoffice/card.html'
                } 
            ]
        },
        {
            'name': 'Rooms',
            'template': 'rooms/row.html'
        },
        {
            'name': 'System',
            'cards': [
                {
                    'name': 'Database',
                    'width': '6',
                    'template': 'datastore/card.html'
                },
                {
                    'name': 'Disk',
                    'width': '3',
                    'template': 'system/card_disk.html'
                },
                {
                    'name': 'Disk',
                    'width': '3',
                    'template': 'system/card_disk_pie.html'
                },
                {
                    'name': 'Memory',
                    'width': '3',
                    'template': 'system/card_memory.html'
                },
                {
                    'name': 'Memory',
                    'width': '3',
                    'template': 'system/card_memory_pie.html'
                },
                {
                    'name': 'CPU',
                    'width': '3',
                    'template': 'system/card_cpu.html'
                },
            ]
        }
    ]
    return render_template('dashboard.html', rows = rows, rooms = rooms, room_data = room_data, data = data)

store = DataStoreSqLite()

hue = ApiHue(store)

plugins = {
    'system': PluginSystem(),
    'datastore': PluginDataStore(store),
    'hue': PluginHue(store),
    'metoffice': PluginMetOffice(store),
    'temperature': PluginTemperature(store)
}

