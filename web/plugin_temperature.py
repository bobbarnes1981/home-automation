import time

class PluginTemperature(object):

    def __init__(self, store):
        self.store = store

    def get_room_data(self, room_id):
        return self.store.get_one_data(room_id, 'temperature_c')

    def get_dashboard_data(self, room):
        return self.store.get_many_data(room['id'], 'temperature_c', time.time() - (60*60*24))

    def config(self, request):
        if request.method == 'POST':
            pass
        tab_data = {}
        return tab_data
