#!/usr/bin/env python3
import json,time
from pathlib import Path
from universal_dudley.visual_backend import VisualMacBackend, choose_window
root=Path(__file__).resolve().parent
cfg=json.loads((root/"config.json").read_text())
import subprocess
emu="openemu"
subprocess.call(["sudo","-v"])
p=int(input("P1 or P2? ").strip())
try:
    b=VisualMacBackend(emu,p,cfg["apps"][emu],cfg["visual"])
except RuntimeError as exc:
    print("\nKEY TEST BLOCKED:",exc)
    raise SystemExit(2)
if b.window is None:
    b.window=choose_window(cfg["apps"][emu]["window_names"])
if b.window is None:
    print("\nKEY TEST BLOCKED: no visible",emu,"window was found. Start the game first.")
    b.close()
    raise SystemExit(2)
print("Game window should be focused. Testing LEFT, RIGHT, LP, HK...")
for keys in [("LEFT",),("RIGHT",),("LP",),("HK",)]:
    print(keys[0])
    b.set_logical(keys,True); time.sleep(.25); b.release_all(); time.sleep(.35)
b.close()
