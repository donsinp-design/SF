from __future__ import annotations
import time
from collections import deque
import numpy as np
import mss
import Quartz
from AppKit import NSWorkspace, NSApplicationActivateIgnoringOtherApps

KEYCODES={
"a":0,"s":1,"d":2,"f":3,"h":4,"g":5,"z":6,"x":7,"c":8,"v":9,"b":11,
"q":12,"w":13,"e":14,"r":15,"y":16,"t":17,"1":18,"2":19,"3":20,"4":21,
"6":22,"5":23,"=":24,"9":25,"7":26,"-":27,"8":28,"0":29,"]":30,"o":31,
"u":32,"[":33,"i":34,"p":35,"return":36,"enter":36,"l":37,"j":38,"k":40,
";":41,",":43,"/":44,"n":45,"m":46,".":47,"tab":48,"space":49,"escape":53,
"left":123,"right":124,"down":125,"up":126
}

def list_windows():
    opts=Quartz.kCGWindowListOptionOnScreenOnly|Quartz.kCGWindowListExcludeDesktopElements
    rows=Quartz.CGWindowListCopyWindowInfo(opts,Quartz.kCGNullWindowID) or []
    out=[]
    for r in rows:
        owner=str(r.get(Quartz.kCGWindowOwnerName) or "")
        title=str(r.get(Quartz.kCGWindowName) or "")
        b=r.get(Quartz.kCGWindowBounds) or {}
        w,h=int(b.get("Width",0)),int(b.get("Height",0))
        if owner and w>250 and h>180:
            out.append({"id":int(r.get(Quartz.kCGWindowNumber,0)),"owner":owner,"title":title,
                        "pid":int(r.get(Quartz.kCGWindowOwnerPID,0)),
                        "x":int(b.get("X",0)),"y":int(b.get("Y",0)),"width":w,"height":h})
    return out

def choose_window(names):
    names=[x.lower() for x in names]
    c=[]
    for w in list_windows():
        hay=(w["owner"]+" "+w["title"]).lower()
        if any(n in hay for n in names):
            c.append((w["width"]*w["height"],w))
    if not c:return None
    c.sort(reverse=True,key=lambda x:x[0])
    return c[0][1]

def activate(names):
    names=[x.lower() for x in names]
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        n=(app.localizedName() or "").lower()
        if any(x in n for x in names):
            app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            return True
    return False

class MotionTracker:
    def __init__(self):
        self.prev=None
        self.p1=None
        self.p2=None
        self.strength=0.0

    def update(self, gray):
        # gray expected around 96x72, exclude top HUD.
        arr=gray.copy()
        h,w=arr.shape
        play=arr[int(h*.18):,:]
        if self.prev is None or self.prev.shape != play.shape:
            self.prev=play
            return self.p1,self.p2
        diff=np.abs(play-self.prev)
        self.prev=play
        col=diff.mean(axis=0)
        kernel=np.ones(7,dtype=np.float32)/7
        sm=np.convolve(col,kernel,mode="same")
        self.strength=float(np.max(sm))
        peaks=[]
        work=sm.copy()
        for _ in range(4):
            i=int(np.argmax(work))
            if work[i] < 0.018: break
            peaks.append(i)
            work[max(0,i-9):min(w,i+10)]=0
        if len(peaks)<2:
            return self.p1,self.p2
        # Keep the two strongest and reasonably separated.
        peaks=sorted(peaks[:2])
        a,b=float(peaks[0]),float(peaks[1])
        if self.p1 is None:
            self.p1,self.p2=a,b
        else:
            same=abs(a-self.p1)+abs(b-self.p2)
            swapped=abs(b-self.p1)+abs(a-self.p2)
            if swapped<same:
                self.p1,self.p2=b,a
            else:
                self.p1,self.p2=a,b
        return self.p1,self.p2

class VisualMacBackend:
    exact=False
    def __init__(self, emulator, player, app_cfg, visual_cfg):
        if emulator!="openemu":
            raise RuntimeError("The screen-reading bot only supports OpenEmu (offline).")
        self.name=emulator
        self.player=player
        self.names=app_cfg["window_names"]
        self.keys=app_cfg[f"p{player}"]
        self.vcfg=visual_cfg
        self.grabber=mss.mss()
        self.window=None
        self.frame=0
        self.held=set()
        self.prev_health={1:None,2:None}
        self.health_level={1:160.0,2:160.0}
        self.health_fill={1:None,2:None}
        self.health_samples={1:deque(maxlen=5),2:deque(maxlen=5)}
        self.health_cooldown={1:0,2:0}
        self.tracker=MotionTracker()
        # CGEventPost and window capture can fail silently when macOS privacy
        # permission is missing. Refuse to pretend the bot is running.
        screen_ok=bool(Quartz.CGPreflightScreenCaptureAccess())
        input_ok=True  # keys go through Karabiner's virtual keyboard, not synthetic events
        if not screen_ok and hasattr(Quartz,"CGRequestScreenCaptureAccess"):
            screen_ok=bool(Quartz.CGRequestScreenCaptureAccess())
        if not screen_ok or not input_ok:
            missing=[]
            if not screen_ok: missing.append("Screen Recording")
            if not input_ok: missing.append("Accessibility")
            raise RuntimeError(
                "macOS blocked " + " and ".join(missing) + ". Open System Settings > "
                "Privacy & Security, enable those permissions for Terminal, quit Terminal, "
                "then launch UniversalDudley.command again."
            )
        activate(self.names)
        from .karabiner_keys import KarabinerKeys
        self.kbd=KarabinerKeys()
        activate(self.names)

    def _focus_game(self):
        # the virtual keyboard types into whichever app is in front
        front=NSWorkspace.sharedWorkspace().frontmostApplication()
        name=(front.localizedName() or "") if front is not None else ""
        if not any(n.lower() in name.lower() for n in self.names):
            activate(self.names)

    def _post(self,key,down):
        code=KEYCODES.get(str(key).lower())
        if code is None: raise KeyError(f"Unknown macOS key: {key}")
        e=Quartz.CGEventCreateKeyboardEvent(None,code,bool(down))
        # Legacy synthetic-event path; OpenEmu input goes through self.kbd instead.
        pid=int((self.window or {}).get("pid",0))
        if pid:
            front=NSWorkspace.sharedWorkspace().frontmostApplication()
            if front is None or int(front.processIdentifier())!=pid:
                for app in NSWorkspace.sharedWorkspace().runningApplications():
                    if int(app.processIdentifier())==pid:
                        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
                        break
        Quartz.CGEventPost(Quartz.kCGHIDEventTap,e)

    def _viewport(self, raw):
        h,w=raw.shape[:2]
        # Largest 4:3 region centred in the app window.
        if w/h > 4/3:
            vw=int(h*4/3); x=(w-vw)//2
            return raw[:,x:x+vw]
        vh=int(w*3/4); y=max(0,(h-vh)//2)
        return raw[y:y+vh,:]

    def _roi(self,img,r):
        h,w=img.shape[:2]
        x1,y1,x2,y2=r
        return img[int(y1*h):int(y2*h),int(x1*w):int(x2*w)]

    def _health_event_value(self, img, p):
        r=self.vcfg["health_roi"][f"p{p}"]
        roi=self._roi(img,r)[:,:,:3].astype(np.float32)
        if roi.size==0:return self.health_level[p]
        # Measure the persistent coloured portion of the bar instead of treating
        # every animated HUD pixel as damage. The old frame-difference method
        # generated dozens of false hits during ordinary HUD animation.
        mx=roi.max(axis=2)
        mn=roi.min(axis=2)
        sat=(mx-mn)/np.maximum(mx,1.0)
        coloured=(sat>.28)&(mx>75)
        col_fill=coloured.mean(axis=0)>.18
        fill=float(col_fill.mean())
        self.health_samples[p].append(fill)
        if len(self.health_samples[p])<5:return self.health_level[p]
        stable=float(np.median(np.asarray(self.health_samples[p])))
        old=self.health_fill[p]
        if old is None:
            self.health_fill[p]=max(stable,.05)
            return self.health_level[p]
        self.health_cooldown[p]=max(0,self.health_cooldown[p]-1)
        # Debounce damage, and accept a large increase as the next round reset.
        if stable>old+.18:
            self.health_fill[p]=stable
            self.health_level[p]=160.0
        elif stable<old-.025 and self.health_cooldown[p]==0:
            ratio=max(0.0,min(1.0,stable/max(old,.05)))
            loss=max(1.0,160.0*(1.0-ratio))
            self.health_level[p]=max(0.0,self.health_level[p]-loss)
            self.health_fill[p]=stable
            self.health_cooldown[p]=8
        return self.health_level[p]

    @staticmethod
    def _small_gray(img,width,height):
        # Nearest-neighbour sampling is enough for motion/fingerprints and is
        # much faster than constructing several Pillow images every frame.
        h,w=img.shape[:2]
        ys=np.linspace(0,h-1,height).astype(np.intp)
        xs=np.linspace(0,w-1,width).astype(np.intp)
        bgr=img[ys[:,None],xs[None,:],:3].astype(np.float32)
        return (bgr[:,:,0]*.114+bgr[:,:,1]*.587+bgr[:,:,2]*.299)/255.0

    def _fp(self, vp, opponent_x):
        h,w=vp.shape[:2]
        # Fingerprint the opponent's local body region, not the whole animated
        # stage. Whole-screen fingerprints matched nearly every game state.
        cx=int((float(opponent_x)/96.0)*w)
        half=max(24,int(w*.15))
        x0,x1=max(0,cx-half),min(w,cx+half)
        crop=vp[int(h*.18):int(h*.94),x0:x1,:3]
        arr=self._small_gray(crop,int(self.vcfg["fingerprint_width"]),
                            int(self.vcfg["fingerprint_height"]))
        return arr.ravel()

    def read_state(self):
        self.frame+=1
        # Capture and analyse on every loop/frame. Window discovery is only
        # metadata and is refreshed once per second to follow moves/resizes.
        if self.window is None or self.frame%60==1:
            found=choose_window(self.names)
            if found is not None:
                first=self.window is None
                self.window=found
                if first:
                    print("Connected to window:",found["owner"],repr(found["title"]),
                          f"{found['width']}x{found['height']}")
                    activate(self.names)
        if self.window is None:return None
        mon={"left":self.window["x"],"top":self.window["y"],
             "width":self.window["width"],"height":self.window["height"]}
        try: shot=self.grabber.grab(mon)
        except Exception:
            self.window=None; return None
        raw=np.asarray(shot)  # BGRA
        vp=self._viewport(raw)
        p1life=self._health_event_value(vp,1)
        p2life=self._health_event_value(vp,2)

        small=self._small_gray(vp,96,72)
        p1x,p2x=self.tracker.update(small)
        if p1x is None or p2x is None:
            # Start positions until motion tracker locks on.
            p1x,p2x=32.0,64.0
        me_x,op_x=(p1x,p2x) if self.player==1 else (p2x,p1x)
        me_life,op_life=(p1life,p2life) if self.player==1 else (p2life,p1life)
        return {
            "frame":self.frame,"exact":False,"confidence":"VISUAL_INFERRED",
            "me_life":me_life,"opp_life":op_life,
            "me_x":float(me_x),"opp_x":float(op_x),
            "me_y":None,"opp_y":None,"dist":float(abs(me_x-op_x))*2.0,
            "facing_right":bool(me_x<op_x),
            "opp_anim":None,"opp_posture":None,
            "opp_motion":self.tracker.strength,
            "fp":self._fp(vp,op_x)
        }

    def set_logical(self, keys, facing_right):
        wanted=set()
        for k in keys:
            if k=="FORWARD": logical="RIGHT" if facing_right else "LEFT"
            elif k=="BACK": logical="LEFT" if facing_right else "RIGHT"
            else: logical=k
            physical=self.keys.get(logical)
            if physical: wanted.add(physical.lower())
        if wanted!=self.held:
            if wanted: self._focus_game()
            self.kbd.hold(sorted(wanted))
        self.held=wanted

    def release_all(self):
        if self.held: self.kbd.hold([])
        self.held.clear()

    def close(self):
        self.release_all()
        self.kbd.close()
