-- Dudley AI for effie's 3rd_training.lua (offline only).
--
-- Defence: effie's predictive parry (real hitboxes from recorded frame data),
-- plus throw teching. Offence: frame-exact punishes, hit-confirms that read
-- the game's own hit flag, a juggle engine, SGGK, parry-buffered pokes,
-- timing-varied oki and a small habit model of the opponent's parries.
local gamestate = require("src.gamestate")
local inputs = require("src.control.inputs")
local framedata = require("src.data.framedata")
local advanced_control = require("src.control.advanced_control")
local settings = require("src.settings")
local modules = require("src.modules")
local character_select = require("src.control.character_select")
local utils = require("src.data.utils")

local AI = {
   enabled = true,    -- false = plain effie training mode
   player_id = 2,     -- side the AI plays
   super_art = 1,     -- 1 Rocket Upper, 2 Rolling Thunder, 3 Corkscrew Blow
   aggression = 0.75, -- 0 = patient footsies, 1 = constant pressure
   hurt_margin = 22,  -- pixels of opponent hurtbox in front of their origin
   show_debug = true,
}

local F, B, D, U = "forward", "back", "down", "up"

local function wait(n) local t = {} for i = 1, n do t[i] = {} end return t end
local function cat(...)
   local out = {}
   for _, part in ipairs({ ... }) do for _, f in ipairs(part) do out[#out + 1] = f end end
   return out
end
local function qcb_f(...) return { { B }, { D, B }, { D }, { D, F }, { F, ... } } end -- 41236
local function dp(...) return { { F }, { D }, { D, F, ... } } end                     -- 623
local function hcb(...) return { { F }, { D, F }, { D }, { D, B }, { B, ... } } end   -- 63214

-- Input sequences, one table per frame, directions relative to facing.
local S = {
   HK = { { "HK" } }, MP = { { "MP" } }, f_MK = { { F, "MK" } }, f_HK = { { F, "HK" } },
   d_LK = { { D, "LK" } }, d_HK = { { D, "HK" } }, MK = { { "MK" } },
   throw = { { F, "LP", "LK" } },
   dp_HP = dp("HP"), dp_MP = dp("MP"), dp_EX = dp("MP", "HP"),
   mgb_EX = qcb_f("MP", "HP"), mgb_HP = qcb_f("HP"), mgb_LP = qcb_f("LP"),
   ducking_upper = cat(qcb_f("MK"), wait(3), { { "LK" } }),  -- 41236MK~K
   ssb_EX = hcb("MK", "HK"),
   -- 236236 + HP then piano MP, LP so the super comes out on the first legal frame
   super = { { D }, { D, F }, { F }, { D }, { D, F }, { F, "HP" }, { "MP" }, { "LP" } },
   -- SGGK: HK~LP+LK. Throw if they stand still, tech if they throw, HK if the
   -- preceding parry tap caught an attack.
   sggk = { { F }, { "HK" }, { "LP", "LK" } },
   parry_poke = { { F }, {}, { "HK" } },     -- parry-buffered st.HK
   dash = { { F }, {}, { F } },
   walk_f = { { F }, { F }, { F }, { F } },
   walk_b = { { B }, { B }, { B }, { B } },
}

-- frames from first input to first active frame
local NEED = { HK = 5, MP = 3, f_MK = 5, f_HK = 12, d_LK = 4, d_HK = 15, dp_HP = 6, mgb_HP = 21, mgb_EX = 20, super = 6 }
-- damage of each super on a standing opponent (wiki), used for kill checks
local SUPER_DAMAGE = { 60, 60, 46 }
-- characters Dudley can loop corner cr.HK on (wiki)
local DHK_LOOP = { chunli = true, makoto = true, dudley = true, oro = true, ibuki = true, elena = true,
   necro = true, alex = true, remy = true, q = true }

local me, opp
local state = { confirm = nil, juggle = nil, last_action = "", oki_at = nil }
local habits = { low = { tries = 1, parried = 0 }, high = { tries = 1, parried = 0 } }
local reach = {}
local selected_this_screen = false

local function has_stock() return me.meter_count >= 1 end
local function has_ex() return me.meter_gauge >= 40 or me.meter_count >= 1 end
local function dist() return math.abs(me.pos_x - opp.pos_x) end
local function opp_near_stun() return opp.stun_bar >= opp.stun_bar_max * 0.6 end
local function super_kills() return has_stock() and opp.life <= SUPER_DAMAGE[AI.super_art] end

local function opp_cornered()
   local left, right = utils.get_stage_limits(gamestate.stage, opp.char_str)
   return opp.pos_x - left < 70 or right - opp.pos_x < 70
end

local function in_reach(name, extra)
   local r = reach[name]
   if not r then
      r = framedata.get_hitbox_max_range_by_name("dudley", name) or 0
      reach[name] = r
   end
   return dist() <= r + AI.hurt_margin + (extra or 0)
end

local function opp_longest_poke()
   local best = 0
   for _, n in ipairs({ "MP", "MK", "HP", "HK", "d_MP", "d_MK", "d_HK" }) do
      local r = framedata.get_hitbox_max_range_by_name(opp.char_str, n) or 0
      if r > best then best = r end
   end
   return best
end

local function act(name, seq, confirm_as, height)
   inputs.queue_input_sequence(me, seq, 0, true)
   state.last_action = name
   if confirm_as then
      state.confirm = { move = confirm_as, until_frame = gamestate.frame_number + #seq + 30, height = height }
   end
   if height then habits[height].tries = habits[height].tries + 1 end
end

local function can_act()
   return me.is_idle and me.remaining_freeze_frames == 0 and not me.is_blocking
      and not inputs.is_playing_input_sequence(me)
end

local function opp_stuck_for(need) return not advanced_control.is_idle_timing(opp, need, true) end

----------------------------------------------------------------------------
-- Combo routing: chooses the ender from kill, stun, meter and position.
----------------------------------------------------------------------------
local function start_juggle(source) state.juggle = { source = source, d_hk = 0, until_frame = gamestate.frame_number + 120 } end

local function cancel_ender(from)
   if super_kills() then return act(from .. " xx super (lethal)", S.super) end
   if opp_near_stun() then return act(from .. " xx HP Jet Upper (stun)", S.dp_HP) end
   if has_stock() then return act(from .. " xx super", S.super) end
   if has_ex() and (from == "HK" or from == "MP") then
      act(from .. " xx EX MGB", S.mgb_EX); start_juggle("ex_mgb"); return
   end
   act(from .. " xx HP Jet Upper", S.dp_HP)
end

local function on_hit(move)
   if move == "HK" or move == "MP" or move == "f_MK" then
      cancel_ender(move)
   elseif move == "d_LK" then
      act("2LK > 2LK", S.d_LK, "d_LK2", "low")
   elseif move == "d_LK2" then
      if has_stock() then act("2LK 2LK xx super", S.super)
      else act("2LK > 2MP > 2HP", cat({ { D, "MP" } }, wait(7), { { D, "HP" } })) end
   elseif move == "f_HK" then
      if has_stock() and AI.super_art ~= 2 and opp.is_crouching then state.link_super = true
      else act("dart shot > MK", cat(wait(6), S.MK)) end
   elseif move == "d_HK" then
      start_juggle("d_hk")
   elseif move == "juggle_fmk" then
      act("juggle: Liver Blow xx HP Jet Upper", S.dp_HP)
   elseif move == "jump_in" then
      state.land_combo = true
   end
end

local function on_block(move)
   if move == "f_MK" or move == "d_LK" or move == "d_LK2" then state.pressure = true end
end

local function update_confirm()
   local c = state.confirm
   if not c then return false end
   if opp.has_just_been_hit then
      state.confirm = nil
      on_hit(c.move)
      return true
   elseif opp.has_just_parried then
      if c.height then habits[c.height].parried = habits[c.height].parried + 1 end
      state.confirm = nil
   elseif opp.has_just_blocked then
      state.confirm = nil
      on_block(c.move)
      return true
   elseif gamestate.frame_number > c.until_frame then
      state.confirm = nil
   end
   return false
end

-- Juggle engine: keeps hitting an airborne opponent until they land.
local function update_juggle()
   local j = state.juggle
   if not j then return false end
   if gamestate.frame_number > j.until_frame or (not opp.is_airborne and not opp.is_in_air_reel and opp.is_idle) then
      state.juggle = nil
      return false
   end
   if not opp.is_airborne then return false end
   if not advanced_control.is_idle_timing(me, 2, true) or inputs.is_playing_input_sequence(me) then return true end
   local d = dist()
   if opp_cornered() and DHK_LOOP[opp.char_str] and j.d_hk < 4 and opp.pos_y < 45 and d < 70 then
      j.d_hk = j.d_hk + 1
      act("juggle: cr.HK #" .. j.d_hk, S.d_HK)
   elseif super_kills() and AI.super_art ~= 2 and d < 90 then
      state.juggle = nil; act("juggle: super (lethal)", S.super)
   elseif opp_near_stun() and d < 70 then
      state.juggle = nil; act("juggle: HP Jet Upper (stun)", S.dp_HP)
   elseif has_stock() and AI.super_art == 3 and d < 90 then
      state.juggle = nil; act("juggle: Corkscrew", S.super)
   elseif d < 60 and opp.pos_y < 60 then
      state.juggle = nil; act("juggle: Liver Blow", S.f_MK, "juggle_fmk")
   elseif d < 120 then
      state.juggle = nil; act("juggle: Ducking Upper", S.ducking_upper)
   end
   return true
end

----------------------------------------------------------------------------
-- Decisions
----------------------------------------------------------------------------
local function opp_projectile_out()
   for _, proj in pairs(gamestate.projectiles) do
      if proj.emitter_id == opp.id then return true end
   end
   return false
end

local function opp_past_active()
   if opp.is_in_recovery then return true end
   if not opp.is_attacking then return false end
   local last = framedata.get_last_hit_frame(opp.char_str, opp.animation)
   return last > 0 and opp.animation_frame > last
end

local function try_punish()
   if opp.is_airborne or opp.has_just_hit or not opp_past_active() or opp_projectile_out() then return false end
   if super_kills() and opp_stuck_for(NEED.super) and in_reach("HK", 10) then act("punish: super (lethal)", S.super); return true end
   if opp_stuck_for(NEED.d_HK) and in_reach("d_HK") and not opp_near_stun() then act("punish: cr.HK launch", S.d_HK, "d_HK"); return true end
   if opp_stuck_for(NEED.HK) and in_reach("HK") then act("punish: HK", S.HK, "HK"); return true end
   if opp_stuck_for(NEED.f_MK) and in_reach("f_MK") then act("punish: f.MK", S.f_MK, "f_MK"); return true end
   if opp_stuck_for(NEED.MP) and in_reach("MP") then act("punish: MP", S.MP, "MP"); return true end
   if has_ex() and opp_stuck_for(NEED.mgb_EX) and in_reach("machinegun_blow_EXP") then
      act("punish: EX MGB", S.mgb_EX); start_juggle("ex_mgb"); return true
   end
   if opp_stuck_for(NEED.mgb_HP) and in_reach("machinegun_blow_HP") then act("punish: HP MGB", S.mgb_HP); return true end
   return false
end

local function try_after_parry()
   if not state.parried then return false end
   state.parried = false
   if in_reach("HK") then act("parry > HK", S.HK, "HK"); return true end
   if in_reach("MP") then act("parry > MP", S.MP, "MP"); return true end
   return false
end

local function try_anti_air()
   if not opp.is_airborne or opp.is_attacking or opp.is_in_air_reel then return false end
   if opp.pos_y > 25 and opp.pos_y < 90 and dist() < 90 then
      if has_ex() and opp.life > 40 then act("anti-air: EX Jet Upper", S.dp_EX)
      else act("anti-air: HP Jet Upper", S.dp_HP) end
      return true
   end
   return false
end

-- pick low or high, favouring whichever the opponent parries less
local function pick_height()
   local low_rate = habits.low.parried / habits.low.tries
   local high_rate = habits.high.parried / habits.high.tries
   local p_low = 0.5 + (high_rate - low_rate) * 0.8
   return math.random() < p_low and "low" or "high"
end

local function try_oki()
   if not opp.is_waking_up then state.oki_at = nil; return false end
   if dist() > 70 then act("oki: dash in", S.dash); return true end
   if not state.oki_at then
      -- vary the contact frame so their parry timing can't be memorised
      state.oki_at = { delay = math.random(0, 6), choice = math.random() }
   end
   local o = state.oki_at
   local function timed(need) return advanced_control.is_wakeup_timing(opp, need + o.delay, true) end
   if o.choice < 0.15 then
      if advanced_control.is_throw_vulnerable_timing(opp, 1 + o.delay, true) then act("oki: throw", S.throw); return true end
   elseif o.choice < 0.3 then
      if timed(2) then act("oki: SGGK", S.sggk, "HK"); return true end
   elseif pick_height() == "low" then
      if timed(NEED.d_LK) then act("oki: meaty 2LK +" .. o.delay, S.d_LK, "d_LK", "low"); return true end
   else
      if timed(NEED.f_HK) then act("oki: dart shot +" .. o.delay, S.f_HK, "f_HK", "high"); return true end
   end
   return true -- wait for the chosen frame
end

local function neutral()
   local d = dist()
   local their_reach = opp_longest_poke() + AI.hurt_margin
   local close = d < framedata.get_contact_distance(me) + 30

   if state.land_combo then state.land_combo = false; act("jump-in > HK", S.HK, "HK"); return end

   if state.pressure or (close and math.random() < AI.aggression * 0.35) then
      state.pressure = false
      local r = math.random()
      if r < 0.25 then act("pressure: f.MK", S.f_MK, "f_MK")
      elseif r < 0.45 then act("pressure: SGGK", S.sggk, "HK")
      elseif r < 0.6 then act("pressure: throw", S.throw)
      elseif pick_height() == "low" then act("pressure: 2LK", S.d_LK, "d_LK", "low")
      else act("pressure: dart shot", S.f_HK, "f_HK", "high") end
      return
   end
   if in_reach("HK") and opp.action == 2 then act("footsie: HK (they walked in)", S.HK, "HK"); return end
   if in_reach("HK", 10) and math.random() < AI.aggression * 0.15 then
      act("footsie: parry-buffered HK", S.parry_poke, "HK"); return
   end
   if d > their_reach + 12 then
      local r = math.random()
      if r < AI.aggression * 0.06 then act("dash in", S.dash)
      elseif r < AI.aggression * 0.08 and d < 220 then
         -- jump-in with varied attack timing (j.HP early, j.HK late) to beat anti-air parry timing
         local late = math.random() < 0.5
         act(late and "jump-in: late j.HK" or "jump-in: early j.HP",
            cat({ { F, U }, { F, U }, { F, U } }, wait(late and math.random(14, 20) or math.random(6, 10)),
               { { late and "HK" or "HP" } }), "jump_in")
      else act("walk in", S.walk_f) end
   elseif d < their_reach - 6 and not close then
      if math.random() < AI.aggression then act("footsie: HK", S.HK, "HK") else act("walk out", S.walk_b) end
   end
end

function AI.update()
   if not gamestate.is_in_match then return end
   me, opp = gamestate.player_objects[AI.player_id], gamestate.player_objects[3 - AI.player_id]
   selected_this_screen = false
   if not framedata.is_loaded or not gamestate.is_in_match_playable or me.char_str ~= "dudley" then return end

   if me.has_just_parried then state.parried = true end
   -- stop walking the moment they attack so the parry logic gets the inputs
   if opp.has_just_attacked and (state.last_action:find("walk") or state.last_action:find("dash")) then
      inputs.clear_input_sequence(me)
   end

   if update_confirm() then return end
   if state.link_super and advanced_control.is_idle_timing(me, NEED.super, true) then
      state.link_super = false; act("dart shot > super (link)", S.super); return
   end
   if update_juggle() then return end
   if can_act() then
      local _ = try_after_parry() or try_punish() or try_anti_air() or try_oki()
         or (not opp.is_attacking and neutral())
   end

   if AI.show_debug then
      gui.text(8, 200, string.format("AI: %s | meter %d/%d | opp stun %d/%d", state.last_action,
         me.meter_count, me.meter_gauge, math.floor(opp.stun_bar), opp.stun_bar_max))
   end
end

local function apply_settings()
   local t = settings.training
   t.blocking_mode = 2     -- always defend
   t.blocking_style = 2    -- by parrying
   t.tech_throws_mode = 2  -- always tech throws
   t.fast_wakeup_mode = 3  -- mix quick rise and normal rise
   t.life_mode, t.meter_mode, t.stun_mode = 1, 1, 1  -- real match: no refills
   t.infinite_time = false
end

function AI.install()
   if not AI.enabled then return end
   local original_update = modules.update
   modules.update = function(...)
      original_update(...)
      AI.update()
   end
   local original_select = character_select.update_character_select
   character_select.update_character_select = function(input)
      if not selected_this_screen then
         selected_this_screen = true
         apply_settings()
         character_select.force_select_character(AI.player_id, "dudley", AI.super_art, "LP")
      end
      return original_select(input)
   end
end

return AI
