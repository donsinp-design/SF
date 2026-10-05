# Dudley AI

This folder is effie's 3rd Strike training mode (https://github.com/effie3rd/3rd_training_lua, commit d0f8e55, GPL-3.0) with a Dudley AI added in `src/ai/dudley_ai.lua`. The AI loads from `fbneo-training-mode.lua` and `ai_training.lua`.

## Install (Fightcade)
1. Copy everything in this folder into `Fightcade/emulator/fbneo/fbneo-training-mode/` and overwrite the existing files.
2. In Fightcade, open the 3rd Strike lobby and press **Training**.
3. Pick your character. P2 picks Dudley (Super Art I) and plays as the AI.

To turn the AI off, set `enabled = false` at the top of `src/ai/dudley_ai.lua`. Other settings there: `super_art`, `aggression`, `hurt_margin`, `show_debug`.

## Combo lab (discovering combos)
1. Nothing to set: `self_learn = true` is the default in `src/ai/dudley_ai.lua`.
2. Press **Training** and **don't touch the controller**. It picks both characters itself.
3. The game runs in turbo. For each starter (st.HK, cr.HK, f.MK, MP, cr.LK, dart shot), at midscreen and in the corner, it tries every follow-up at every timing from a save state. It keeps the routes that are true combos and extends them up to 4 steps.
4. The best route per meter budget (meterless, EX, super) is saved to `saved/dudley_combos.lua`, per opponent character. The AI then switches back to fighting and uses those routes automatically.

It runs by itself: on start it studies every opponent character it has no combos for yet, choosing P1 automatically. Leave the controller alone until the screen stops showing COMBO LAB. Delete `saved/dudley_combos.lua` to make it study everything again. Routes that fail 3 times in real matches are dropped.

## Other techniques it uses
- **D.E.D.:** when meter is just short of a stock, the super is buffered behind st.HK, MP, f.MK or dart shot. It only comes out if the hit's meter gain completes the stock.
- **Ducking super buffer:** against crouching opponents, it uses st.HK/MP xx LK Ducking xx super.
- **Input buffering:** motions start during recovery so the button lands on the first free frame.
- **Move reading:** every frame it reads which move you're doing and how many frames until it hits. It interrupts slow startups with Rocket Upper (invincible) or st.HK, and parries everything else.
