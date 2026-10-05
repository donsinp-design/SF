# Dudley AI (add-on for effie's 3rd_training_lua)

This version of the bot runs on top of [effie's 3rd Strike training mode](https://github.com/effie3rd/3rd_training_lua) and uses its recorded frame data and hitboxes for every character:

- **Defence:** effie's predictive blocking, set to parry. It knows every move's active frames, so it can parry a move the first time it sees it.
- **Punishes:** only when the frame data says the punish will land before the opponent recovers. It picks the biggest one: super, then st.HK, f.MK, MP, then EX or HP Machine Gun Blow from range.
- **Hit-confirms:** it waits to see that st.HK, f.MK, MP or 2LK hit, then cancels into Rocket Upper, Jet Upper or EX MGB during hitstop. Dart shot (f.HK) on a crouching opponent links into super.
- **Anti-air and oki:** Jet Upper on empty jumps (attacking jumps get parried). On wakeup it mixes meaty 2LK, dart shot overhead and throws.
- **Footsies:** it stays just outside the opponent's longest poke and uses st.HK when they walk in. `aggression` controls how much it rushes in.
- **Character select:** it forces P2 to Dudley with Super Art I (Rocket Upper). Change `super_art` in `src/ai/dudley_ai.lua` to use another super.

## Install (Fightcade, offline)
1. Download effie's training mode and paste its files into `Fightcade/emulator/fbneo/fbneo-training-mode/`, as effie's README says.
2. Copy `ai_training.lua` and the `src/ai/` folder from this add-on into the same folder.
3. Open 3rd Strike with **Test Game**, go to **Game → Lua Scripting**, and run **`ai_training.lua`**.
4. Pick your character. The AI picks Dudley for P2.

Offline only. Effie's code is GPL-3.0, so this add-on is distributed under GPL-3.0 too.
