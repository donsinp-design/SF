-- Dudley game plan. Numpad notation relative to facing (6 = toward opponent).
-- Couldn't reach the supercombo wiki from here: inputs are standard Dudley
-- motions; tune frame counts below if a move doesn't come out.
local I = require("ai_input")
local h, seq = I.hold, I.seq
local D = {}

D.CHAR_ID   = 0x04  -- Dudley's character id on the select screen (verify via debug)
D.SUPER_ART = 2     -- 1 Rocket Upper, 2 Rolling Thunder, 3 Corkscrew Cross

-- Super motion 236236 + P, two frames per direction so it isn't dropped.
local function super(btn)
  return seq(h(2,2), h(3,2), h(6,2), h(2,2), h(3,2), h(6,1,{btn}), h(5,1,{btn}))
end

D.SUPER      = super("HP")
D.JET_UPPER  = seq(h(6,2), h(2,2), h(3,1,{"HP"}))          -- 623P anti-air / reversal
D.CR_MK      = h(2,3,{"MK"})                                -- main footsie poke
D.ST_MK      = h(5,3,{"MK"})                                -- long poke
D.CR_LK      = h(2,2,{"LK"})
D.THROW      = h(6,2,{"LP","LK"})
D.WALK_IN    = h(6,3)
D.WALK_BACK  = h(4,3)
D.DASH_IN    = seq(h(6,1), h(5,1), h(6,1))

-- Pressure starter: cr.LK, cr.LK. The brain checks if it hit before committing to super.
D.CONFIRM_STARTER = seq(D.CR_LK, h(2,6), D.CR_LK)
-- Whiff/recovery punish: cr.MK cancelled straight into super.
D.PUNISH = seq(h(2,3,{"MK"}), super("HP"))

D.POKE_RANGE  = 115  -- cr.MK tip, in game pixels (measure in training mode)
D.THROW_RANGE = 40

return D
