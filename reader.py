import time
from machine import UART, Timer


class AimeReader:
    def __init__(self, index: int, baudrate: int = 115200):
        self._uart = UART(index, baudrate=baudrate)
        self._cards = [
            {'enable': False, 'number': None, 'timer': Timer(0)},
            {'enable': False, 'number': None, 'timer': Timer(1)}
        ]

    def swipe(self, p, number):
        self._cards[p]['number'] = number
        self._cards[p]['enable'] = True
        self._cards[p]['timer'].deinit()
        self._cards[p]['timer'].init(mode=Timer.ONE_SHOT, period=3000, callback=self._disable_card)
        print('Swipe card.')

    def wait(self):
        while True:
            h = self._read()
            if h != 0xE0:
                print('Packet header error. %#x' % h)
                continue
            l = self._read()
            if l <= 0:
                print('Packet length error. %#x' % l)
                continue
            body = []
            body.append(l)
            body.extend(self._reads(l - 1))
            s = self._read()
            if s != self._check_sum(body):
                print('Check sum error. %#x' % s)
                continue
            self._pkg_handler(body[1], body[3], body[5:])

    def _disable_card(self, t):
        for i in self._cards:
            if i['timer'] == t:
                i['enable'] = False

    def _send_pkg(self, addr, comm, data=None):
        if data is None:
            data = []
        if type(data) is not bytearray:
            data = bytearray(data)
        print('Send data: addr %#x comm %#x' % (addr, comm))
        data_len = len(data)
        body_len = data_len + 6
        pkg = [
            0xE0,  # head
            body_len,  # len
            addr,  # addr
            0x00,  # num
            comm,  # cmd
            data_len  # data len
        ]
        pkg.extend(data)
        pkg.append(self._check_sum(pkg[1:]))
        self._writes(pkg)

    def _pkg_handler(self, addr, comm, data):
        print('Recv data: addr %#x comm %#x' % (addr, comm))
        # Only 1 and 2
        if addr != 0x00 and addr != 0x01:
            return
        # SG_NFC_CMD_RADIO_ON
        # SG_NFC_CMD_RADIO_OFF
        # SG_NFC_CMD_MIFARE_SELECT_TAG
        # SG_NFC_CMD_MIFARE_SET_KEY_BANA
        # SG_NFC_CMD_MIFARE_SET_KEY_AIME
        # SG_NFC_CMD_MIFARE_AUTHENTICATE
        # SG_NFC_CMD_RESET
        if comm in [0x40, 0x41, 0x43, 0x50, 0x54, 0x55, 0x62]:
            self._send_pkg(addr, comm)
        # SG_NFC_CMD_GET_FW_VERSION
        if comm == 0x30:
            self._send_pkg(addr, comm, 'TN32MSEC003S F/W Ver1.2E')
        # SG_NFC_CMD_GET_HW_VERSION
        if comm == 0x32:
            self._send_pkg(addr, comm, 'TN32MSEC003S H/W Ver3.0J')
        # SG_NFC_CMD_POLL
        if comm == 0x42:
            if self._cards[addr]['enable']:
                self._cards[addr]['enable'] = False
                self._send_pkg(addr, comm, b'\x01\x10\x04\x11\x22\x33\x44')
            else:
                self._send_pkg(addr, comm, b'\x00')
        # SG_NFC_CMD_MIFARE_READ_BLOCK
        if comm == 0x52:
            number = self._cards[addr]['number']
            res = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            if number is not None:
                if data[4] == 1:
                    res = b'\x53\x42\x53\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x4F\x3D\x46'
                elif data[4] == 2:
                    res = b'\x00\x00\x00\x00\x00\x00' + number
            self._send_pkg(addr, comm, res)

    def _read(self, escape=False):
        while self._uart.any() <= 0:
            time.sleep_ms(10)
        b = self._uart.read(1)
        b = b[0]
        if b == 0xD0:
            return self._read(True)
        if escape:
            b += 1
        return b

    def _reads(self, count: int):
        data = []
        for i in range(count):
            data.append(self._read())
        return data

    def _writes(self, data):
        tmp = []
        for b in data:
            if len(tmp) != 0 and (b == 0xE0 or b == 0xD0):
                tmp.append(0xD0)
                b -= 1
            tmp.append(b)
        self._uart.write(bytearray(tmp))

    def _check_sum(self, data):
        return sum(data) % 256
