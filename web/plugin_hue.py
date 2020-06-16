import requests

class PluginHue(object):

    def __init__(self, store):
        self.store = store
        self.api = ApiHue(store)

    def get_dashboard_data(self, room):
        return self.api.get_lights_in_group(room['hue_group_id'])

    def config(self, request):
        if request.method == 'POST':
            self.store.set_config('hue_address', request.form['hue_address'])
            self.store.set_config('hue_username', request.form['hue_username'])
            rooms = self.store.get_rooms()
            for room in rooms:
                hue_group_id = request.form['room_{0}'.format(room['id'])]
                self.store.update_room(room['id'], room['name'], hue_group_id)
        hue_address = self.store.get_config('hue_address')
        hue_username = self.store.get_config('hue_username')
        rooms = self.store.get_rooms()
        hue_groups = self.api.get_groups()
        hue_groups[0] = {'name': ''}
        tab_data = {
            'hue_address': hue_address,
            'hue_username': hue_username,
            'rooms': rooms,
            'hue_groups': hue_groups
        }
        return tab_data

class ApiHue(object):

    DEVICE_TYPE = 'home-automation'

    def __init__(self, store):
        self.store = store

    def url(self, path):
        '''Build the hue api url'''
        return 'http://{0}/api/{1}/{2}'.format(self.store.get_config('hue_address'), self.store.get_config('hue_username'), path)

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

