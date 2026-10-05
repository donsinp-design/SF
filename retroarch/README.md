# RetroArch version (Python bridge)

RetroArch has no Lua, so this is a Python program that reads 3rd Strike's memory from RetroArch and presses P2's buttons over your local network. It uses the same learn-and-parry brain as `bot/`, playing Dudley-style. It's a frame or two behind the Fightcade version, and `--delay` adds more lag on purpose for latency tests.

## Setup
1. In RetroArch, load 3rd Strike (`sfiii3nr1`) with the **FBNeo** core.
2. Go to **Settings → Network** and turn on:
   - **Network Commands** (port 55355)
   - **Network RetroPad** (base port 55400), with **User 2 Remote Enable** on
   Then restart the game.
3. In RetroArch, add a P2 coin and press P2 start. Pick Dudley for P2 yourself.
4. In Terminal, during a round with both players at full health:
   ```
   cd path/to/SF/retroarch && python3 probe.py
   ```
   When it asks, let P1 take one hit, then press Enter. It prints the right setting.
5. Run the bot with that setting, for example:
   ```
   python3 ra_bot.py --swap 4
   ```
   Add `--delay 4` to simulate 4 frames of lag.

If P2's buttons come out wrong (for example kick instead of punch), edit `BUTTONS` at the top of `ra_bot.py` to match **Quick Menu → Controls → Port 2**.

What it learns is saved to `retroarch/threats.json`.
