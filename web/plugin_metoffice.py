import requests
from datetime import datetime

class PluginMetOffice(object):

    def __init__(self, store):
        self.store = store
        self.api = ApiMetOffice(self.store)

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

    def get_dashboard_data(self):
        data = {}
        weather = self.api.get_observation(self.store.get_config('metoffice_location'))
        data['types'] = self.api.weather_types
        data['location'] = weather['SiteRep']['DV']['Location']['name']
        data['keys'] = weather['SiteRep']['Wx']['Param']
        data['data'] = self.get_latest_weather(weather)
        data['icons'] = ForecastFont.metoffice_icons
        return data

    def config(self, request):
        if request.method == 'POST':
            self.store.set_config('metoffice_key', request.form['metoffice_key'])
            self.store.set_config('metoffice_location', request.form['metoffice_location'])
        metoffice_key = self.store.get_config('metoffice_key')
        metoffice_location = self.store.get_config('metoffice_location')
        metoffice_locations = self.get_observation_locations()
        tab_data = {
            'metoffice_key': metoffice_key,
            'metoffice_location': metoffice_location,
            'metoffice_locations': metoffice_locations
        }
        return tab_data

class ApiMetOffice(object):

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

    def __init__(self, store):
        self.store = store

    def url(self, path):
        '''Build the met office data point url'''
        return 'http://{0}/{1}?res=hourly&key={2}'.format(self.base_url, path, self.store.get_config('metoffice_key'))

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

