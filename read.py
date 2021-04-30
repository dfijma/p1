#!/usr/bin/python3 -u

import urllib.request
from datetime import datetime
import Adafruit_CharLCD as LCD
import Adafruit_GPIO.MCP230xx as MCP
import time
import math
import smbus
import sys
import socket

# get i2c bus
bus = smbus.SMBus(1)

# Define MCP pins connected to the LCD.
lcd_rs = 1
lcd_en = 2
lcd_d4 = 3
lcd_d5 = 4
lcd_d6 = 5
lcd_d7 = 6
lcd_back = 7

# Define LCD column and row size for 16x2 LCD.
lcd_columns = 16
lcd_rows = 2

# get lcd via MCP i2c io extender
gpio = MCP.MCP23008(0x20, busnum=1)
lcd = LCD.Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7,
                           lcd_columns, lcd_rows, lcd_back,
                           gpio=gpio, invert_polarity=False)

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
client.bind(('', 37020))

def read():
    try:
        data, addr = client.recvfrom(37020)
        values = data.decode("utf-8").split()
        vs = {}
        for v in values:
            nv = v.split('=')
            vs[nv[0]] = float(nv[1])
        print(vs)
        line1 = f"ps:{vs['ps']:.2f} yt:{vs['yt']:.2f}"
        line2 = f"pl:{vs['pl']:.2f} ya:{vs['ya']:.2f}"
        print(line1)
        print(line2)
        lcd.set_cursor(0, 0)
        lcd.message(line1)
        lcd.set_cursor(0, 1)
        lcd.message(line2)
    except Exception as inst:
        print("error: ", inst)

while True:
    read()
