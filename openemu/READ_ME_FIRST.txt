DUDLEY AI FOR OPENEMU (offline) — ELI5

OpenEmu ignores keys "typed" by programs. It only listens to real keyboards.
Karabiner's free virtual keyboard looks like a real keyboard to your Mac,
so the bot types on that instead.

ONE-TIME SETUP
1. Install Homebrew if you don't have it (brew.sh) and Xcode (you already have it).
2. Double-click setup_karabiner.command. It asks for your Mac password.
3. If macOS says "System Extension Blocked": System Settings > Privacy & Security >
   Allow. Restart if asked, then run setup_karabiner.command again.
4. System Settings > Privacy & Security > Screen & System Audio Recording:
   turn on Terminal. (Accessibility is no longer needed.)

OPENEMU CONTROLS (Arcade > Player 2 > Input: Keyboard) — already matching yours:
  Up I   Down K   Left J   Right L   Start P
  Button 1 B (LP)   Button 2 N (MP)   Button 3 M (HP)
  Button 4 , (LK)   Button 5 . (MK)   Button 6 / (HK)
  Different keys? Edit "openemu" > "p2" in config.json.

EVERY TIME
1. Start 3rd Strike in OpenEmu, pick Dudley for P2 yourself, and wait for the round to start.
   (Start the bot during the round — on the select screen it would press random buttons.)
2. Double-click UniversalDudley.command, choose 2 (OpenEmu), then 2 (P2).
3. Enter your Mac password once when asked.
4. Leave the OpenEmu window in front — the virtual keyboard types into the front app.
5. Ctrl+C in Terminal stops it and releases all keys.

TEST THE KEYS FIRST
Double-click TEST_KEYS.command with the game running. Dudley should walk left,
walk right, jab, then roundhouse.

LIMITS
OpenEmu has no way for the bot to read game memory, so it reads the screen.
It's much less exact than the Fightcade Training version (fbneo-training-mode).

LEARNING LOG
saved/dudley_learning.txt — every hit taken and whiff, with the reason.
