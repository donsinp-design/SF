if emu.romname() == "sfiii3nr1" then
   require("src.data.game_data").is_fightcade = true
   require("src.ai.dudley_ai").install() -- Dudley AI on P2 (set enabled = false in src/ai/dudley_ai.lua to turn off)
   require("3rd_training")
else
   local chunk = assert(loadfile("fbneo-training-mode-original.lua"))
   setfenv(chunk, getfenv(1)) -- run in current environment
   chunk()
end
