import os

def get_path():
    BASE = '/sys/bus/w1/devices/'
    FILE = '/w1_slave'
    directories = os.listdir(BASE)
    for directory in directories:
        if directory.startswith('28'):
            return BASE + directory + FILE
    return None
path = get_path()

# 125c is 0x7D0 (2000)
scale = 0x7D0 / 125.0

sp = [
    'temp_lsb',
    'temp_msb',
    'ub1',
    'ub2',
    'conf',
    'res_FF',
    'res',
    'res_10',
    'crc'
]

res = {
    '00': 9,
    '01': 10,
    '10': 11,
    '11': 12
}

with open(path, 'r') as f:
    data = f.readlines()

data = data[0]

data = data.split(':')[0].strip()

print('scratchpad')
print(data)

data = data.split(' ')

for i in range(0, 9):
    print(i, sp[i], data[i])

print("0x{0}{1}".format(data[1], data[0]))
temp = int(data[1], 16)<<8 | int(data[0], 16)
print(temp/scale)

conf = format(int(data[4], 16), '#010b')

print('0b0rr11111')
print(conf)
print("{0} bits".format(res[conf[3:5]]))

