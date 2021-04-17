import crcmod.predefined

def calc_crc_telegram1(telegram):
    x = 0
    crc = 0
    while x < len(telegram):
        crc = crc ^ (127 & telegram[x])
        x = x + 1
        y = 0
        while y < 8:
            if (crc & 1) != 0:
                crc = (crc >> 1) ^ (int("0xA001", 16))
            else:
                crc = crc >> 1
            y = y + 1
    print(f"CRC calculated : {crc:x}")
    return crc


def calc_crc_telegram2(telegram):
    crc = 0
    for x in telegram:
        crc = crc ^ (127 & x)
        for y in range(8):
            if (crc & 1) != 0:
                crc = crc >> 1
                crc = crc ^ (int("0xA001", 16))
            else:
                crc = crc >> 1
    print(f"CRC calculated : {crc:x}")

test3 = b"""/KFM5KAIFA-METER\r
\r
1-3:0.2.8(42)\r
0-0:1.0.0(170124213128W)\r
0-0:96.1.1(4530303236303030303234343934333135)\r
1-0:1.8.1(000306.946*kWh)\r
1-0:1.8.2(000210.088*kWh)\r
1-0:2.8.1(000000.000*kWh)\r
1-0:2.8.2(000000.000*kWh)\r
0-0:96.14.0(0001)\r
1-0:1.7.0(02.793*kW)\r
1-0:2.7.0(00.000*kW)\r
0-0:96.7.21(00001)\r
0-0:96.7.9(00001)\r
1-0:99.97.0(1)(0-0:96.7.19)(000101000006W)(2147483647*s)\r
1-0:32.32.0(00000)\r
1-0:52.32.0(00000)\r
1-0:72.32.0(00000)\r
1-0:32.36.0(00000)\r
1-0:52.36.0(00000)\r
1-0:72.36.0(00000)\r
0-0:96.13.1()\r
0-0:96.13.0()\r
1-0:31.7.0(003*A)\r
1-0:51.7.0(005*A)\r
1-0:71.7.0(005*A)\r
1-0:21.7.0(00.503*kW)\r
1-0:41.7.0(01.100*kW)\r
1-0:61.7.0(01.190*kW)\r
1-0:22.7.0(00.000*kW)\r
1-0:42.7.0(00.000*kW)\r
1-0:62.7.0(00.000*kW)\r
0-1:24.1.0(003)\r
0-1:96.1.0(4730303331303033333738373931363136)\r
0-1:24.2.1(170124210000W)(00671.790*m3)\r
!"""

test4 = """29ED"""

crc=0

def calc_crc_telegram(telegram):
    global crc
    for x in telegram:
        crc = crc ^ x
        for y in range(8):
            if (crc & 1) != 0:
                crc = crc >> 1
                crc = crc ^ (int("0xA001",16))
            else:
                crc = crc >> 1

crc16 = crcmod.predefined.mkPredefinedCrcFun('crc16')

calc_crc_telegram1(test3)
calc_crc_telegram2(test3)
calculated_checksum = crc16(test3)
print(f"{calculated_checksum:x}")
calc_crc_telegram(test3)