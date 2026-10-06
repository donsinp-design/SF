from __future__ import annotations
import socket, struct, time

CMD_PORT = 55355
PAD_PORT_BASE = 55400
JOY = {"B":0,"Y":1,"SELECT":2,"START":3,"UP":4,"DOWN":5,"LEFT":6,"RIGHT":7,"A":8,"X":9,"L":10,"R":11}
BUTTONS = {"LP":"Y","MP":"X","HP":"L","LK":"B","MK":"A","HK":"R"}

P_BASE = {1:0x02068C6C, 2:0x02069104}
OFF_FLIP, OFF_X, OFF_Y, OFF_LIFE, OFF_POSTURE, OFF_ANIM = 0x0A,0x64,0x68,0x9F,0x20E,0x202
READ_LEN=0x210

def s16(b,o):
    v=(b[o]<<8)|b[o+1]
    return v-0x10000 if v&0x8000 else v

class RetroArchBackend:
    name="retroarch"
    exact=True
    def __init__(self, player=2, swap=4, host="127.0.0.1"):
        self.player=player
        self.host=host
        self.swap=swap
        self.cmd=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.cmd.settimeout(0.05)
        self.pad=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.pad_port=PAD_PORT_BASE+player-1
        self.ram_base=0x02000000
        self.held={}
        self.frame=0

    def read_raw(self, addr, length):
        self.cmd.sendto((f"READ_CORE_RAM {addr:x} {length}\n").encode(),(self.host,CMD_PORT))
        try: data,_=self.cmd.recvfrom(65536)
        except socket.timeout: return None
        parts=data.decode(errors="ignore").split()
        if len(parts)<3 or parts[2]=="-1": return None
        try: return bytes(int(x,16) for x in parts[2:])
        except Exception: return None

    def read(self, cps3_addr, length):
        w=self.swap
        start=cps3_addr & ~(w-1)
        end=(cps3_addr+length+w-1)&~(w-1)
        raw=self.read_raw(start-self.ram_base,end-start)
        if raw is None:return None
        fixed=b"".join(raw[i:i+w][::-1] for i in range(0,len(raw),w))
        off=cps3_addr-start
        return fixed[off:off+length]

    def _player(self,n):
        b=self.read(P_BASE[n],READ_LEN)
        if b is None:return None
        return {"x":s16(b,OFF_X),"y":s16(b,OFF_Y),"life":b[OFF_LIFE],
                "posture":b[OFF_POSTURE],"anim":(b[OFF_ANIM]<<8)|b[OFF_ANIM+1]}

    def read_state(self):
        self.frame+=1
        p1,p2=self._player(1),self._player(2)
        if not p1 or not p2:return None
        if not (0 <= p1["life"] <= 160 and 0 <= p2["life"] <= 160): return None
        me,op=(p1,p2) if self.player==1 else (p2,p1)
        return {
            "frame":self.frame,"exact":True,"confidence":"EXACT_RAM",
            "me_life":float(me["life"]),"opp_life":float(op["life"]),
            "me_x":float(me["x"]),"opp_x":float(op["x"]),
            "me_y":float(me["y"]),"opp_y":float(op["y"]),
            "dist":float(abs(me["x"]-op["x"])),
            "facing_right":bool(me["x"]<op["x"]),
            "opp_anim":int(op["anim"]),"opp_posture":int(op["posture"]),
            "fp":None
        }

    def _set_button(self,name,pressed):
        if self.held.get(name)==pressed:return
        self.held[name]=pressed
        msg=struct.pack("<iiiiH2x",0,1,0,JOY[name],1 if pressed else 0)
        self.pad.sendto(msg,(self.host,self.pad_port))

    def set_logical(self, keys, facing_right):
        wanted=set()
        for k in keys:
            if k=="FORWARD": wanted.add("RIGHT" if facing_right else "LEFT")
            elif k=="BACK": wanted.add("LEFT" if facing_right else "RIGHT")
            elif k in BUTTONS: wanted.add(BUTTONS[k])
            else: wanted.add(k)
        for n in JOY:
            if n in ("START","SELECT"): continue
            self._set_button(n,n in wanted)

    def release_all(self):
        for n in JOY:self._set_button(n,False)

    def close(self):
        self.release_all()
