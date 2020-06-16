import psutil
import subprocess

class PluginSystem(object):

    def __init__(self):
        self.vcgencmd = VCGenCmd()

    def get_dashboard_data(self):
        data = {}
        data['cpu_perc'] = psutil.cpu_percent()
        data['cpu_temp'] = self.vcgencmd.measure_temp()
        data['root_data'] = psutil.disk_usage('/')
        data['mem_data'] = psutil.virtual_memory()
        return data

class VCGenCmd(object):

    def __init__(self):
        pass

    def get_raw(self, command):
        return subprocess.check_output(['vcgencmd', command])

    def measure_temp(self):
        '''call the measure_temp command on vcgencmd'''
        return self.get_raw('measure_temp')[5:9]

