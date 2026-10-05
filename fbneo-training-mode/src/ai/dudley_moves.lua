-- Dudley inputs shared by the fighting AI and the combo lab.
-- One table per frame; directions are relative to facing.
local M = {}

local F, B, D, U = "forward", "back", "down", "up"
M.F, M.B, M.D, M.U = F, B, D, U

function M.wait(n) local t = {} for i = 1, n do t[i] = {} end return t end
function M.cat(...)
   local out = {}
   for _, part in ipairs({ ... }) do for _, f in ipairs(part) do out[#out + 1] = f end end
   return out
end
local wait, cat = M.wait, M.cat
local function qcb_f(...) return { { B }, { D, B }, { D }, { D, F }, { F, ... } } end -- 41236
local function dp(...) return { { F }, { D }, { D, F, ... } } end                     -- 623
local function hcb(...) return { { F }, { D, F }, { D }, { D, B }, { B, ... } } end   -- 63214
-- 236236 + HP then piano MP, LP so the super comes out on the first legal frame
local SUPER = { { D }, { D, F }, { F }, { D }, { D, F }, { F, "HP" }, { "MP" }, { "LP" } }

M.S = {
   HK = { { "HK" } }, MP = { { "MP" } }, MK = { { "MK" } }, f_MK = { { F, "MK" } }, f_HK = { { F, "HK" } },
   d_LK = { { D, "LK" } }, d_MP = { { D, "MP" } }, d_HK = { { D, "HK" } },
   throw = { { F, "LP", "LK" } },
   dp_HP = dp("HP"), dp_MP = dp("MP"), dp_EX = dp("MP", "HP"),
   mgb_EX = qcb_f("MP", "HP"), mgb_HP = qcb_f("HP"), mgb_LP = qcb_f("LP"),
   ducking_LK = qcb_f("LK"),
   ducking_upper = cat(qcb_f("MK"), wait(3), { { "LK" } }),    -- 41236MK~K
   ducking_straight = cat(qcb_f("MK"), wait(3), { { "LP" } }), -- 41236MK~P
   ssb_LK = hcb("LK"), ssb_EX = hcb("MK", "HK"),
   super = SUPER,
   -- Ducking as a super buffer: cancel into LK Ducking, then into super from the duck
   ducking_super = cat(qcb_f("LK"), SUPER),
   -- SGGK: HK~LP+LK. Throw if they stand still, tech if they throw, HK if the
   -- parry tap before it caught an attack.
   sggk = { { F }, { "HK" }, { "LP", "LK" } },
   parry_poke = { { F }, {}, { "HK" } },
   dash = { { F }, {}, { F } },
   walk_f = { { F }, { F }, { F }, { F } },
   walk_b = { { B }, { B }, { B }, { B } },
   jump_f = { { F, U }, { F, U }, { F, U } },
}

-- frames from first input to first active frame (wiki startup + motion length - 1)
M.NEED = { HK = 5, MP = 3, f_MK = 5, f_HK = 12, d_LK = 4, d_HK = 15, dp_HP = 6, mgb_HP = 21, mgb_EX = 20, super = 6 }
-- self meter gain on hit / on block (wiki), used for the D.E.D. option select
M.GAIN = { HK = { 19, 10 }, MP = { 11, 6 }, f_MK = { 11, 6 }, f_HK = { 19, 10 } }
-- super damage on a standing opponent (wiki)
M.SUPER_DAMAGE = { 60, 60, 46 }

-- Follow-ups the combo lab tries after every hit. cost = {ex bars, super stocks}
M.LAB_STEPS = {
   { name = "d_HK", seq = M.S.d_HK, cost = { 0, 0 } },
   { name = "f_MK", seq = M.S.f_MK, cost = { 0, 0 } },
   { name = "f_MK xx HP Jet Upper", seq = cat(M.S.f_MK, wait(2), M.S.dp_HP), cost = { 0, 0 } },
   { name = "HK", seq = M.S.HK, cost = { 0, 0 } },
   { name = "HK xx HP Jet Upper", seq = cat(M.S.HK, wait(2), M.S.dp_HP), cost = { 0, 0 } },
   { name = "MP xx HP Jet Upper", seq = cat(M.S.MP, wait(1), M.S.dp_HP), cost = { 0, 0 } },
   { name = "d_MP", seq = M.S.d_MP, cost = { 0, 0 } },
   { name = "HP Jet Upper", seq = M.S.dp_HP, cost = { 0, 0 } },
   { name = "MP Jet Upper", seq = M.S.dp_MP, cost = { 0, 0 } },
   { name = "LP MGB", seq = M.S.mgb_LP, cost = { 0, 0 } },
   { name = "Ducking Upper", seq = M.S.ducking_upper, cost = { 0, 0 } },
   { name = "Ducking Straight", seq = M.S.ducking_straight, cost = { 0, 0 } },
   { name = "LK SSB", seq = M.S.ssb_LK, cost = { 0, 0 } },
   { name = "EX Jet Upper", seq = M.S.dp_EX, cost = { 1, 0 } },
   { name = "EX MGB", seq = M.S.mgb_EX, cost = { 1, 0 } },
   { name = "EX SSB", seq = M.S.ssb_EX, cost = { 1, 0 } },
   { name = "super", seq = M.S.super, cost = { 0, 1 } },
   { name = "LK Ducking xx super", seq = M.S.ducking_super, cost = { 0, 1 } },
}
M.LAB_DELAYS = { "now", 0, 3, 6, 10 }

-- Starters the lab builds combo trees from
M.LAB_STARTERS = { "HK", "d_HK", "f_MK", "MP", "d_LK", "f_HK" }

return M
