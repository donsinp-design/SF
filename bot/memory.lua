-- RAM map for sfiii3nr1 (3rd Strike Japan 990512, NO CD), the ROM Fightcade uses.
-- Offsets come from community training-mode research. Verify them with
-- debug overlay (F_DEBUG in main.lua) before trusting the bot; ROM revisions differ.
local M = {}

M.P = {
  [1] = { base = 0x02068C6C, life = 0x02068D0B },
  [2] = { base = 0x02069104, life = 0x020691A3 },
}

M.OFF = {
  flip   = 0x0A,  -- byte: facing
  pos_x  = 0x64,  -- word
  pos_y  = 0x68,  -- word
  posture= 0x20E, -- byte: 0 stand, 0x20 crouch, >=0x0C airborne-ish
  anim   = 0x202, -- word: current animation id
}

local rb, rw = memory.readbyte, memory.readwordsigned

function M.read_player(n)
  local p, o = M.P[n], M.OFF
  return {
    x       = rw(p.base + o.pos_x),
    y       = rw(p.base + o.pos_y),
    flip    = rb(p.base + o.flip),
    posture = rb(p.base + o.posture),
    anim    = memory.readword(p.base + o.anim),
    life    = rb(p.life),
  }
end

return M
