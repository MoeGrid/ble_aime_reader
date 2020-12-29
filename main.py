import sys
import time
import machine
from ble import BleUtil
from machine import UART, Timer, WDT

uart = UART(1, baudrate=38400, rx=0, tx=4)
ble = BleUtil(name='aime-reader')

cards = [{'enable': False, 'uid': None, 'number': None, 'timer': Timer(0)}, {'enable': False, 'uid': None, 'number': None, 'timer': Timer(1)}]


def read(escape=False):
    while uart.any() <= 0:
        time.sleep_ms(10)
    b = uart.read(1)
    b = b[0]
    if b == 0xD0:
        return read(True)
    if escape:
        b += 1
    return b


def reads(count):
    data = []
    for i in range(count):
        data.append(read())
    return data


def sendPkg(addr, comm, data=[]):
    if type(data) is not bytearray:
        data = bytearray(data)

    print('Send data: addr %#x comm %#x' % (addr, comm))
    dataLen = len(data)
    bodyLen = dataLen + 6

    pkg = []
    pkg.append(0xE0)  # 包头
    pkg.append(bodyLen)  #包长
    pkg.append(addr)  # 地址
    pkg.append(0x00)  # 序号
    pkg.append(comm)  # 操作
    pkg.append(0x00)  # 状态
    pkg.append(dataLen)  # 荷载长度
    pkg.extend(data)  # 数据
    pkg.append(checkSum(pkg[1:]))

    uart.write(bytearray(pkg))


def checkSum(data):
    return sum(data) % 256


def handlePkg(addr, comm, data):
    global cards
    print('Recv data: addr %#x comm %#x' % (addr, comm))

    # 只接受地址1和2的封包
    if addr != 0x00 and addr != 0x01:
        return

    # 未知. 重启?
    if comm == 0x62:
        sendPkg(addr, comm)

    # 获取固件版本
    if comm == 0x30:
        sendPkg(addr, comm, 'TN32MSEC003S F/W Ver1.2E')

    # 获取硬件版本
    if comm == 0x32:
        sendPkg(addr, comm, 'TN32MSEC003S H/W Ver3.0J')

    # 设置Mifare KeyA
    # 57 43 43 46 76 32
    # WCCFv2
    if comm == 0x54:
        sendPkg(addr, comm)

    # 设置Mifare KeyB
    # 60 90 D0 06 32 F5
    if comm == 0x50:
        sendPkg(addr, comm)

    # 不明
    # 03
    if comm == 0x40:
        sendPkg(addr, comm)

    # 不明
    if comm == 0x41:
        sendPkg(addr, comm)

    # 检查Mifare卡是否存在?
    if comm == 0x42:
        if cards[addr]['enable']:
            cards[addr]['enable'] = False
            sendPkg(addr, comm, b'\x01\x10\x04' + cards[addr]['uid'])
        else:
            sendPkg(addr, comm, b'\x00')

    # 按UID选择MiFare?
    # xx xx xx xx (四字节Mifare UID)
    if comm == 0x43:
        sendPkg(addr, comm)

    # 不明
    # xx xx xx xx 03 (四字节Mifare UID)
    if comm == 0x55:
        sendPkg(addr, comm)

    # 可能从Mifare扇区0读取块1和2.
    # 块0包含"供应商信息"和UID.
    # 块1的内容未知, 可能是AiMe数据库信息.
    # 块2的最后10个字节(十六进制)印在卡上("本地唯一ID").
    # (第3块包含加密密钥, 因此不允许读取)
    if comm == 0x52:
        number = cards[addr]['number']
        if not number is None:
            if data[4] == 1:
                sendPkg(addr, comm, b'\x53\x42\x53\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x4F\x3D\x46')
                return
            elif data[4] == 2:
                sendPkg(addr, comm, b'\x00\x00\x00\x00\x00\x00' + number)
                return
        sendPkg(addr, comm, b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')


def disableCard(t):
    for i in cards:
        if i['timer'] == t:
            i['enable'] = False


def handleBle():
    data = ble.read()
    if len(data) == 15:
        global cards
        p = data[0]
        if not p in (0, 1):
            return
        cards[p]['uid'] = data[1:5]
        cards[p]['number'] = data[5:15]
        cards[p]['enable'] = True
        cards[p]['timer'].deinit()
        cards[p]['timer'].init(mode=Timer.ONE_SHOT, period=3000, callback=disableCard)
        print('Swipe card.')


def main():
    print('=== Aime Reader ===')

    # 初始化BLE
    ble.irq(handler=handleBle)

    # 主程序
    while True:
        # 读包头
        h = read()
        if h != 0xE0:
            print('Packet header error. %#x' % h)
            continue
        # 读取包长
        l = read()
        if l <= 0:
            print('Packet length error. %#x' % l)
            continue
        # 读取包体
        body = []
        body.append(l)
        body.extend(reads(l - 1))
        # 读取校验
        s = read()
        if s != checkSum(body):
            print('Check sum error. %#x' % s)
            continue
        # 处理封包
        handlePkg(body[1], body[3], body[5:])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('=== Exit ===')
    except Exception as e:
        print('=== Exception ===')
        sys.print_exception(e)
        print('=== Exit ===')
        machine.reset()

# import os; os.remove('main.py')
