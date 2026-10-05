-- Plays a combo route step by step, frame-exact. Shared by the lab (which
-- discovers routes) and the fighting AI (which replays them), so a route
-- behaves the same in a match as it did when it was found.
--
-- A route is a list of { step = <name in moves.LAB_STEPS>, delay = "now" | n }.
--   "now": queue immediately (a cancel during hitstop)
--   n:    queue so the button lands n frames after Dudley's first free frame
local gamestate = require("src.gamestate")
local inputs = require("src.control.inputs")
local advanced_control = require("src.control.advanced_control")
local moves = require("src.ai.dudley_moves")

local steps = {}
for _, s in ipairs(moves.LAB_STEPS) do steps[s.name] = s end

local E = { steps = steps }

function E.new(chain) return { chain = chain, i = 1, phase = "schedule" } end

-- returns "running", "done" or "failed"
function E.update(ex, me, opp)
   local el = ex.chain[ex.i]
   if not el then return "done" end
   local step = steps[el.step]
   if not step then return "failed" end
   local frame = gamestate.frame_number
   if ex.phase == "schedule" then
      local go = false
      if el.delay == "now" then
         go = true
      else
         if not ex.ready_since and advanced_control.is_idle_timing(me, #step.seq - 1, true) then ex.ready_since = frame end
         go = ex.ready_since and frame - ex.ready_since >= el.delay
      end
      if go then
         local seq = moves.lagged(step.seq)
         inputs.queue_input_sequence(me, seq, 0, true)
         ex.press_frame = frame + #seq - 1
         ex.phase = "await_hit"
      elseif opp.is_idle and not opp.is_airborne then
         return "failed"
      end
   elseif ex.phase == "await_hit" then
      if opp.has_just_been_hit and frame >= ex.press_frame then
         ex.i, ex.phase, ex.ready_since = ex.i + 1, "schedule", nil
         if not ex.chain[ex.i] then return "done" end
      elseif frame > ex.press_frame + 45 or (opp.is_idle and frame > ex.press_frame) or opp.is_blocking then
         return "failed"
      end
   end
   return "running"
end

function E.cost(chain)
   local ex, sup = 0, 0
   for _, el in ipairs(chain) do
      local s = steps[el.step]
      if s then ex, sup = ex + s.cost[1], sup + s.cost[2] end
   end
   return ex, sup
end

function E.describe(chain)
   local parts = {}
   for _, el in ipairs(chain) do
      parts[#parts + 1] = el.step .. (el.delay == "now" and "" or ("(+" .. el.delay .. ")"))
   end
   return table.concat(parts, " > ")
end

return E
