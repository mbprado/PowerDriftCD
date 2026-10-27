-- Read-only table-writer and upstream state-word probes for the arcade main CPU.
local mode = assert(os.getenv("PDRIFT_UPSTREAM_MODE"))
assert(mode == "table_boot" or mode == "state_inputs" or
       mode == "state_targets" or mode == "state88_inputs" or
       mode == "state88_targets" or mode == "source_writes")
local cpu = assert(manager.machine.devices[":maincpu"])
local space = assert(cpu.spaces["program"])
local debugger = assert(cpu.debug)
local machine_debugger = assert(manager.machine.debugger)
local output = assert(os.getenv("PDRIFT_UPSTREAM_DIR"))
local state = os.getenv("PDRIFT_STATE_LOAD")
local pulse = tonumber(os.getenv("PDRIFT_STEER_PULSE") or "")
if mode == "table_boot" then
  assert(not state and not pulse)
else
  assert(state and pulse and pulse >= 0 and pulse <= 255)
end
local ports = manager.machine.ioport.ports
local coin = assert(ports[":GENERAL"].fields["Coin 1"])
local start = assert(ports[":GENERAL"].fields["1 Player Start"])
local pedal = assert(ports[":ADC.4"].fields["P1 Pedal 1"])
local steering = assert(ports[":ADC.5"].fields["Paddle"])
local frames = mode == "table_boot" and 0 or 950
local ready = mode == "table_boot"
local breakpoint
local entry_breakpoints = {}
local source_watchpoints = {}
machine_debugger.execution_state = "run"
machine_debugger.visible_cpu = cpu

local function snapshot(frame)
  for _, address in ipairs({ 0x1fa000, 0x1fb000 }) do
    local bytes = {}
    for offset = 0, 0xfff do
      bytes[#bytes + 1] = string.char(space:read_u8(address + offset))
    end
    local path = string.format("%s/table-%04d-%06X.bin", output, frame, address)
    local file = assert(io.open(path, "wb"))
    assert(file:write(table.concat(bytes)))
    assert(file:close())
    print(string.format("UPSTREAM_TABLE,%d,%06X,4096,%s", frame, address, path))
  end
end

if mode == "table_boot" then
  coin:set_value(0)
  start:set_value(0)
  pedal:set_value(0)
  steering:set_value(128)
  breakpoint = debugger:wpset(space, "w", 0x1fa000, 0x2000, "1",
    'printf "TABLE_WRITE pc=%06X addr=%06X data=%08X\\n",pc,wpaddr,wpdata;g')
  if os.getenv("PDRIFT_UPSTREAM_ENTRY_TRACE") == "1" then
    for _, pc in ipairs({ 0x38736, 0x38768 }) do
      entry_breakpoints[#entry_breakpoints + 1] = debugger:bpset(pc, "1",
        'printf "TABLE_ENTRY pc=%06X a6=%06X pointer=%08X\\n",pc,a6,d@ceb00;g')
    end
  end
  print("TABLE_WATCH_ARMED,1FA000,2000")
end

emu.register_frame_done(function()
  if not ready then return end
  frames = frames + 1
  if mode == "table_boot" then
    if frames == 60 then coin:set_value(1) end
    if frames == 65 then coin:set_value(0) end
    if frames == 130 then start:set_value(1) end
    if frames == 135 then start:set_value(0) end
    if frames == 240 then pedal:set_value(255) end
    if frames == 950 then
      debugger:wpclear(breakpoint)
      for _, index in ipairs(entry_breakpoints) do debugger:bpclear(index) end
      snapshot(frames)
      print("TABLE_WATCH_CLEARED,950")
    end
    return
  end
  if frames >= 960 and frames <= 1000 then
    machine_debugger:command(string.format('printf "UPSTREAM_FRAME,%d\\n"', frames))
  end
  if frames == 960 then
    steering:set_value(pulse)
    if mode == "state_inputs" then
      breakpoint = debugger:bpset(0x34dda, "a5==c0840",
        'printf "STATE_INPUT pc=%06X a5=%06X old7a=%04X source7c=%04X sign88=%04X\\n",pc,a5,w@(a5+7a),w@(a5+7c),w@(a5+88);g')
    elseif mode == "state_targets" then
      breakpoint = debugger:bpset(0x34e0a, "a5==c0840",
        'printf "STATE_TARGET pc=%06X a5=%06X new7a=%04X\\n",pc,a5,w@(a5+7a);g')
    elseif mode == "state88_inputs" then
      breakpoint = debugger:bpset(0x34da4, "a5==c0840",
        'printf "STATE88_INPUT pc=%06X a5=%06X source86=%04X old88=%04X\\n",pc,a5,w@(a5+86),w@(a5+88);g')
    elseif mode == "state88_targets" then
      breakpoint = debugger:bpset(0x34dda, "a5==c0840",
        'printf "STATE88_TARGET pc=%06X a5=%06X new88=%04X\\n",pc,a5,w@(a5+88);g')
    else
      for _, address in ipairs({ 0x0c08ba, 0x0c08bc, 0x0c08c8 }) do
        source_watchpoints[#source_watchpoints + 1] =
          debugger:wpset(space, "w", address, 2, "1",
            'printf "STATE_SOURCE_WRITE pc=%06X addr=%06X data=%08X\\n",pc,wpaddr,wpdata;g')
      end
    end
    print(string.format("UPSTREAM_ARMED,%s,960,pulse=%d", mode, pulse))
  end
  if frames == 1000 then
    if breakpoint then debugger:bpclear(breakpoint) end
    for _, index in ipairs(source_watchpoints) do debugger:wpclear(index) end
    print("UPSTREAM_CLEARED,1000")
  end
end, "frame")

if state then
  emu.add_machine_post_load_notifier(function()
    frames = 950
    ready = true
    pedal:set_value(255)
    steering:set_value(128)
    print("UPSTREAM_STATE_LOAD,950," .. state)
  end)
  manager.machine:load(state)
end
