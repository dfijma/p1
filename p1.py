#! /usr/bin/python3 -u

import socket
import sys
import serial
from urllib import request
import time

## parse p1 lines


class Parser:

    def __init__(self):
        self.c = 0
        self.input = []

    def cur(self):
        if self.c < len(self.input):
            return self.input[self.c]
        else:
            return chr(0)

    def skip(self):
        self.c = min(self.c + 1, len(self.input))

    def parse_c(self, unit_allowed):
        start = self.c
        while not self.cur() in ['(', ')', chr(0), '*']:
            self.skip()
        end_val = self.c
        unit = None
        if self.cur() == '*':
            self.skip()
            start_unit = self.c
            while not self.cur() in ['(', ')', chr(0)]:
                self.skip()
            unit = self.input[start_unit:self.c]

        if unit_allowed:
            return self.input[start:end_val], unit
        else:
            if unit:
                raise ValueError("unit not allowed")
            return self.input[start:end_val]

    def parse_bracket_c(self):
        if self.cur() != '(':
            raise ValueError("( expected")
        self.skip()
        val = self.parse_c(True)
        if self.cur() != ')':
            raise ValueError(") expected")
        self.skip()
        return val

    def parse_bracket_list(self):
        f = self.parse_bracket_c()
        if self.cur() == chr(0):
            return [f]
        else:
            rest = self.parse_bracket_list()
            rest.insert(0, f)
            return rest

    def parse(self, s):
        self.input = s
        self.c = 0
        name = self.parse_c(False)
        value_list = self.parse_bracket_list()
        # print(name)
        # print(value_list)
        return name, value_list

    def parse_lines(self, lines_read):
        while True:
            for lines in lines_read:
                for line in lines:
                    try:
                        yield self.parse(line)
                    except ValueError:
                        pass

##### serial p1 communication

class P1Serial:
    def __init__(self):
        self.ser = serial.Serial()
        self.ser.baudrate = 115200
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.xonxoff = 0
        self.ser.rtscts = 0
        self.ser.timeout = 20
        self.ser.port = "/dev/ttyUSB0"
        self.crc = 0
        try:
            self.ser.open()
        except:
            sys.exit(f"error opening serial port {self.ser.name}")


    def calc_crc_telegram(self, telegram):
        for x in telegram:
            self.crc = self.crc ^ x
            for y in range(8):
                if (self.crc & 1) != 0:
                    self.crc = self.crc >> 1
                    self.crc = self.crc ^ (int("0xA001", 16))
                else:
                    self.crc = self.crc >> 1

    def read_p1(self):
        state = 0
        lines = []
        while True:
            try:
                p1_raw = self.ser.readline()
            except:
                sys.exit(f"cannot read serial port {self.ser.name}")
            p1_str = p1_raw.decode('ascii')
            p1_line = p1_str.strip()
            # print(p1_raw)
            if p1_line.startswith("!"):
                self.calc_crc_telegram([ord("!")])
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
                self.calc_crc_telegram(p1_raw)
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
    p1_serial = P1Serial()
    lines_read = p1_serial.read_p1()
    parser = Parser()
    for (name, values) in parser.parse_lines(lines_read):
        if name in names:
            if len(values) == 1:
                value = values[0]
                try:
                    fvalue = float(value[0])
                    vals[name] = fvalue
                except ValueError:
                    pass
        yield vals


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

def run():
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    for t in zip(readouts(), read_omnik()):
        print(t[1])
        ps = t[1][0] # solar power
        yt = t[1][1] # yield today
        ya = t[1][2] # yield all time
        pr = t[0].get('1-0:2.7.0') # power received
        pd = t[0].get('1-0:1.7.0') # power delivered
        if pr is not None and pd is not None:
            pl = pd - pr # power line (negative is received back)
            msg = f"pl={pl} ps={ps} yt={yt} ya={ya}"
            client.sendto(msg.encode('UTF-8'), ('<broadcast>', 37020))
        time.sleep(1)

if __name__ == "__main__":
    run()

