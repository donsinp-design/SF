#!/usr/bin/env python3
import subprocess, sys
def ask(prompt, valid):
    while True:
        x=input(prompt).strip().lower()
        if x in valid:return x
print()
print("UNIVERSAL DUDLEY")
print("================")
print("1 = RetroArch")
print("2 = OpenEmu (keys via Karabiner virtual keyboard; run setup_karabiner.command once)")
e=ask("Which emulator? [1/2]: ",{"1","2"})
emu={"1":"retroarch","2":"openemu"}[e]
if emu=="openemu":
    # authorise sudo now so the key bridge doesn't stop mid-match for a password
    subprocess.call(["sudo","-v"])
p=ask("Take over P1 or P2? [1/2]: ",{"1","2"})
cmd=[sys.executable,"-m","universal_dudley.main","--emulator",emu,"--player",p]
if emu=="openemu":
    import json, pathlib
    chars=sorted(json.loads((pathlib.Path(__file__).parent/"universal_dudley"/"char_data.json").read_text()))
    print("Opponent's character:", ", ".join(chars))
    o=input("Which character is your opponent? (Enter to skip): ").strip().lower()
    if o in chars: cmd += ["--opponent",o]
if emu=="retroarch":
    print()
    print("RetroArch memory byte order is usually 4.")
    s=input("Swap value [press Enter for 4, or type 1/2/4]: ").strip()
    if s in {"1","2","4"}: cmd += ["--swap",s]
print()
print("Starting Dudley on",emu.upper(),"P"+p)
print()
raise SystemExit(subprocess.call(cmd))
