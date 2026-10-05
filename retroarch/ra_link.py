"""Talk to a running RetroArch over UDP (network commands + Network RetroPad)."""
import socket
import struct

CMD_PORT = 55355          # Settings > Network > Network Commands
PAD_PORT_BASE = 55400     # Settings > Network > Network RetroPad (user N listens on 55400 + N - 1)

# libretro joypad ids
JOY = {"B": 0, "Y": 1, "SELECT": 2, "START": 3, "UP": 4, "DOWN": 5, "LEFT": 6, "RIGHT": 7,
       "A": 8, "X": 9, "L": 10, "R": 11}


class RetroArch:
    def __init__(self, host="127.0.0.1", player=2, ram_base=0x02000000, ram_offset=0, swap32=False):
        self.host = host
        self.cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cmd.settimeout(0.05)
        self.pad = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.pad_port = PAD_PORT_BASE + player - 1
        self.ram_base = ram_base      # CPS3 address that maps to RetroArch address `ram_offset`
        self.ram_offset = ram_offset
        self.swap32 = swap32          # some cores store big-endian RAM byte-swapped per 32-bit word
        self.held = {}

    # ---- memory -------------------------------------------------------
    def read_raw(self, addr, length):
        msg = "READ_CORE_MEMORY %x %d\n" % (addr, length)
        self.cmd.sendto(msg.encode(), (self.host, CMD_PORT))
        try:
            data, _ = self.cmd.recvfrom(65536)
        except socket.timeout:
            return None
        parts = data.decode(errors="ignore").split()
        if len(parts) < 3 or parts[2] == "-1":
            return None
        return bytes(int(b, 16) for b in parts[2:])

    def read(self, cps3_addr, length):
        """Read `length` bytes at a CPS3 address, undoing the 32-bit swap if needed."""
        if not self.swap32:
            return self.read_raw(cps3_addr - self.ram_base + self.ram_offset, length)
        start = (cps3_addr & ~3)
        end = (cps3_addr + length + 3) & ~3
        raw = self.read_raw(start - self.ram_base + self.ram_offset, end - start)
        if raw is None:
            return None
        fixed = b"".join(raw[i:i + 4][::-1] for i in range(0, len(raw), 4))
        off = cps3_addr - start
        return fixed[off:off + length]

    # ---- input --------------------------------------------------------
    def set_button(self, name, pressed):
        if self.held.get(name) == pressed:
            return
        self.held[name] = pressed
        # struct remote_message { int port; int device; int index; int id; uint16_t state; }
        msg = struct.pack("<iiiiH2x", 0, 1, 0, JOY[name], 1 if pressed else 0)
        self.pad.sendto(msg, (self.host, self.pad_port))

    def set_buttons(self, pressed_names):
        for name in JOY:
            if name in ("SELECT", "START"):
                continue
            self.set_button(name, name in pressed_names)

    def release_all(self):
        for name in JOY:
            self.set_button(name, False)
