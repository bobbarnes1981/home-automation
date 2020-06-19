import json
import os
import requests
import sys
from threading import Thread
import time
from datetime import datetime

uri = 'http://home-automation/api/room/<room_id>/temperature'
if len(sys.argv) != 2:
    print('Usage {0} <uri>'.format(sys.argv[0]))
    print('  uri: {0}'.format(uri))
    exit()

rest_uri = sys.argv[1]

class Sensor(object):
    def __init__(self):
        self.path = self.get_path()
    def get_path(self):
        BASE = '/sys/bus/w1/devices/'
        FILE = '/w1_slave'
        directories = os.listdir(BASE)
        for directory in directories:
            if directory.startswith('28'):
                return BASE + directory + FILE
        return None
    def raw(self):
        with open(self.path, 'r') as f:
            return f.readlines()
    def temperature(self):
        raw = self.raw()
        while raw[0].strip()[-3:] != 'YES':
            time.sleep(0.5)
            raw = self.raw()
        temp = float(raw[1].strip()[-5:]) / 1000 # convert to decimal
        return temp

class Service(Thread):
    def __init__(self, sensor):
        Thread.__init__(self)
        self.starttime = time.time()
        self.sensor = sensor
        self.running = True

    def run(self):
        while self.running:
            temp = self.sensor.temperature()
            print(datetime.fromtimestamp(time.time()))
            print(temp)
            try:
                payload = { 'temperature_c' : temp }
                header = { 'content-type': 'application/json' }
                response = requests.post(rest_uri, data=json.dumps(payload), headers=header)
                print(response.text)
            except Exception, e:
                print(e)
            delay = (60.0 - ((time.time() - self.starttime) % 60.0))
            print('sleeping for: {0}'.format(delay))
            time.sleep(delay)

srv = Service(Sensor())
#srv.daemon = True
srv.start()

