import sys
import time
import machine
from reader import AimeReader
from ble import BleUtil
from machine import UART, Timer, Pin

ble = BleUtil(name='aime-reader')
reader = AimeReader(2, 38400)
p13 = Pin(13, Pin.OUT)

def insert_coins(num):
    print('Insert coins.')
    for i in range(num):
        p13.on()
        time.sleep_ms(150)
        p13.off()
        time.sleep_ms(150)


def handle_ble():
    data = ble.read()
    if not data or data[0] not in (0xA1, 0xA2):
        return
    # swipe
    if data[0] == 0xA1:
        p = data[1]
        card = data[2:12]
        if p not in (0, 1) or len(card) != 10:
            return
        reader.swipe(p, card)
    # coin
    if data[0] == 0xA2:
        num = data[1]
        if num < 1 or num > 20:
            return
        insert_coins(num)


if __name__ == "__main__":
    try:
        print('=== Aime Reader ===')
        # init ble
        ble.irq(handler=handle_ble)
        # wait package
        reader.wait()
    except KeyboardInterrupt:
        print('=== Exit ===')
    except Exception as e:
        print('=== Exception ===')
        sys.print_exception(e)
        print('=== Exit ===')
        machine.reset()

# import os; os.remove('main.py')
