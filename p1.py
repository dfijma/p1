#! /usr/bin/python3 -u

import socket
import sys
import serial
from urllib import request
import time

## parse p1 lines

c = 0
input = []


def cur():
    if c < len(input):
        return input[c]
    else:
        return chr(0)


def skip():
    global c
    c = min(c + 1, len(input))


def parse_c(unit_allowed):
    global c
    start = c
    while not cur() in ['(', ')', chr(0), '*']:
        skip()
    end_val = c
    unit = None
    if cur() == '*':
        skip()
        start_unit = c
        while not cur() in ['(', ')', chr(0)]:
            skip()
        unit = input[start_unit:c]

    if unit_allowed:
        return (input[start:end_val], unit)
    else:
        if unit:
            raise ValueError("unit not allowed")
        return input[start:end_val]


def parse_bracket_c():
    if cur() != '(':
        raise ValueError("( expected")
    skip()
    val = parse_c(True)
    if cur() != ')':
        raise ValueError(") expected")
    skip()
    return val


def parse_bracket_list():
    f = parse_bracket_c()
    if cur() == chr(0):
        return [f]
    else:
        rest = parse_bracket_list()
        rest.insert(0, f)
        return rest


def parse(s):
    global c
    global input
    input = s
    c = 0
    name = parse_c(False)
    list = parse_bracket_list()
    # print(name)
    # print(list)
    return (name, list)


def parse_lines(lines_read):
    while True:
        for lines in lines_read:
            for line in lines:
                try:
                    yield (parse(line))
                except ValueError:
                    pass


##### serial p1 communication

ser = serial.Serial()
ser.baudrate = 115200
ser.bytesize = serial.EIGHTBITS
ser.parity = serial.PARITY_NONE
ser.stopbits = serial.STOPBITS_ONE
ser.xonxoff = 0
ser.rtscts = 0
ser.timeout = 20
ser.port = "/dev/ttyUSB0"

try:
    ser.open()
except:
    sys.exit(f"error opening serial port {ser.name}")

crc = 0


def calc_crc_telegram(telegram):
    global crc
    for x in telegram:
        crc = crc ^ x
        for y in range(8):
            if (crc & 1) != 0:
                crc = crc >> 1
                crc = crc ^ (int("0xA001", 16))
            else:
                crc = crc >> 1


def read_p1():
    state = 0
    lines = []
    while True:
        try:
            p1_raw = ser.readline()
        except:
            sys.exit(f"cannot read serial port {ser.name}")
        p1_str = p1_raw.decode('ascii')
        p1_line = p1_str.strip()
        # print(p1_raw)
        if p1_line.startswith("!"):
            calc_crc_telegram([ord("!")])
            if state == 2:
                # happy: all data ssen
                # print(f"telegram {crc:x} {p1_line[1:].strip()} {p1_line} ")
                state = 0
                crc = 0
                yield lines
            else:
                # unhappy, reset
                # print("reset, unexpected crc line")
                state = 0
                crc = 0
        else:
            calc_crc_telegram(p1_raw)
            if p1_line == "":
                if state == 1:
                    # happy: data starts after this
                    state = 2
                else:
                    # unhappy: reset
                    # print("reset, unexpected empty line")
                    state = 0
                    crc = 0
            elif p1_line.startswith("/"):
                # happy: start of telegram
                state = 1
                lines = []
            else:
                if state == 2:
                    # happy, data line
                    lines.append(p1_line)
                else:
                    # print("reset, unexpected data line")
                    state = 0
                    crc = 0


##### read-out interesting values from parsed p1 lines 

names = ['1-0:1.7.0', '1-0:2.7.0']
vals = {}


def readouts():
    global vals
    for name in names:
        vals[name] = None
    lines_read = read_p1()
    for (name, values) in parse_lines(lines_read):
        if name in names:
            if len(values) == 1:
                value = values[0]
                try:
                    fvalue = float(value[0])
                    vals[name] = fvalue
                except ValueError:
                    pass
        yield (vals)


##### omnik

# yuck, but works: https://github.com/Woutrrr/Omnik-Data-Logger/issues/27
url = "http://10.1.0.104/js/status.js"


def read_omnik():
    while True:
        try:
            for line in request.urlopen(url):
                d = line.decode('ascii', errors="ignore")
                if "myDeviceArray[0]=" in d:
                    ps = d.split(',')
                    [now, today, total] = ps[5:8]
                    now = float(now) / 1000
                    today = float(today) / 100  # 1/100's of kWh
                    total = float(total) / 10  # c1/10's of kWh
                    yield now, today, total
                    break
        except Exception as inst:
            print("error: ", inst)


##### main

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

for t in zip(readouts(), read_omnik()):
    ps = t[1][0]
    pr = t[0].get('1-0:2.7.0')
    pd = t[0].get('1-0:1.7.0')
    print(t)
    if pr is not None and pd is not None:
        pl = pd - pr
        msg = f"pl={pl} ps={ps}"
        client.sendto(msg.encode('UTF-8'), ('<broadcast>', 37020))
    time.sleep(1)
