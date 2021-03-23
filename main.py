import sys
import machine
from reader import AimeReader
from ble import BleUtil
from machine import UART, Timer

ble = BleUtil(name='aime-reader')
reader = AimeReader(2, 38400)


def handle_ble():
    data = ble.read()
    if len(data) == 15:
        p = data[0]
        if p not in (0, 1):
            return
        reader.swipe(p, data[5:15])


if __name__ == "__main__":
    try:
        print('=== Aime Reader ===')
        # 初始化BLE
        ble.irq(handler=handle_ble)
        # 循环处理封包
        reader.wait()
    except KeyboardInterrupt:
        print('=== Exit ===')
    except Exception as e:
        print('=== Exception ===')
        sys.print_exception(e)
        print('=== Exit ===')
        machine.reset()

# import os; os.remove('main.py')
