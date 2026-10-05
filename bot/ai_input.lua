-- Frame-exact input queue. Each entry is a set of buttons held for one frame.
local I = { queue = {} }

local NAMES = { LP="Weak Punch", MP="Medium Punch", HP="Strong Punch",
                LK="Weak Kick",  MK="Medium Kick",  HK="Strong Kick" }

-- dir uses numpad notation relative to facing: 6 = toward opponent, 2 = down, etc.
function I.push(frames) for _, f in ipairs(frames) do table.insert(I.queue, f) end end
function I.clear() I.queue = {} end
function I.busy() return #I.queue > 0 end

local function dir_to_keys(dir, facing_right)
  local fwd, back = facing_right and "Right" or "Left", facing_right and "Left" or "Right"
  local map = { [1]={"Down",back},[2]={"Down"},[3]={"Down",fwd},[4]={back},[5]={},
                [6]={fwd},[7]={"Up",back},[8]={"Up"},[9]={"Up",fwd} }
  return map[dir or 5]
end

function I.apply(player, facing_right)
  local f = table.remove(I.queue, 1)
  local pad = {}
  if f then
    for _, k in ipairs(dir_to_keys(f.dir, facing_right)) do pad["P"..player.." "..k] = true end
    for _, b in ipairs(f.btn or {}) do pad["P"..player.." "..NAMES[b]] = true end
  end
  joypad.set(pad)
end

-- helpers
function I.hold(dir, n, btn) local t = {} for i=1,n do t[i]={dir=dir, btn=btn} end return t end
function I.seq(...) local out = {} for _, part in ipairs({...}) do
  for _, f in ipairs(part) do table.insert(out, f) end end return out end

return I
