-- Isolated, read-only producer entry or output trace from callback-950 state.
local state = assert(os.getenv("PDRIFT_STATE_LOAD"))
local mode = assert(os.getenv("PDRIFT_CODE_PILOT_MODE"))
assert(mode == "inputs" or mode == "targets")
local pulse = tonumber(os.getenv("PDRIFT_STEER_PULSE") or "")
assert(pulse and pulse >= 0 and pulse <= 255)
local cpu = assert(manager.machine.devices[":maincpu"])
local debugger = assert(cpu.debug)
local space = assert(cpu.spaces["program"])
local table_dir = os.getenv("PDRIFT_CODE_PILOT_TABLE_DIR")
assert(mode ~= "inputs" or table_dir)
local steering = assert(manager.machine.ioport.ports[":ADC.5"].fields["Paddle"])
local pedal = assert(manager.machine.ioport.ports[":ADC.4"].fields["P1 Pedal 1"])
local frames = 950
local ready = false
local breakpoint
local function capture_tables(frame)
  if mode ~= "inputs" then return end
  for _, address in ipairs({ 0x1fa000, 0x1fb000 }) do
    local file = assert(io.open(string.format("%s/table-%04d-%06X.bin",
      table_dir, frame, address), "wb"))
    local bytes = {}
    for offset = 0, 0xfff do
      bytes[#bytes + 1] = string.char(space:read_u8(address + offset))
    end
    assert(file:write(table.concat(bytes)))
    assert(file:close())
    print(string.format("PILOT_TABLE,%d,%06X,4096", frame, address))
  end
end
manager.machine.debugger.execution_state = "run"
manager.machine.debugger.visible_cpu = cpu
emu.register_frame_done(function()
  if not ready then return end
  frames = frames + 1
  if frames >= 960 and frames <= 1000 then
    manager.machine.debugger:command(
      string.format('printf "PILOT_FRAME,%d\\n"', frames))
  end
  if frames == 960 then
    steering:set_value(pulse)
    capture_tables(frames)
    local action
    if mode == "inputs" then
      action = 'printf "PILOT_INPUT pc=%06X a0=%06X a1=%06X a4=%06X a5=%06X depth=%04X smooth=%04X state2a=%04X state7a=%04X flag1=%04X flag2=%04X\\n",pc,a0,a1,a4,a5,w@(a5+3e),w@cea1c,w@(a5+2a),w@(a5+7a),w@ce80e,w@ce076;g'
      breakpoint = debugger:bpset(0x34680, "1", action)
    else
      action = 'printf "PILOT_TARGET pc=%06X a4=%06X a5=%06X index=%04X\\n",pc,a4,a5,w@c00a6;g'
      breakpoint = debugger:bpset(0x346f0, "1", action)
    end
    print(string.format("PILOT_ARMED,%s,960,pulse=%d", mode, pulse))
  end
  if frames == 1000 then
    capture_tables(frames)
    debugger:bpclear(breakpoint)
    print("PILOT_CLEARED,1000")
  end
end, "frame")
emu.add_machine_post_load_notifier(function()
  frames = 950
  pedal:set_value(255)
  steering:set_value(128)
  ready = true
  print("PILOT_STATE_LOAD,950," .. state)
end)
manager.machine:load(state)
