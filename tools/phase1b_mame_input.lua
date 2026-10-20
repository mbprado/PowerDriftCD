local ports = manager.machine.ioport.ports
local coin = assert(ports[":GENERAL"].fields["Coin 1"])
local start = assert(ports[":GENERAL"].fields["1 Player Start"])
local pedal = assert(ports[":ADC.4"].fields["P1 Pedal 1"])
local steering = assert(ports[":ADC.5"].fields["Paddle"])
local screen = assert(manager.machine.screens[":screen"])
local output = assert(os.getenv("PDRIFT_SNAPSHOT_DIR"))
local ram_output = os.getenv("PDRIFT_RAM_DIR")
local rotate_output = os.getenv("PDRIFT_ROTATE_DIR")
local debug_mode = os.getenv("PDRIFT_DEBUG_WATCH")
assert(not debug_mode or debug_mode == "1" or debug_mode == "shared"
  or debug_mode == "reads")
local ram_space = (ram_output or debug_mode)
  and assert(manager.machine.devices[":maincpu"].spaces["program"])
local steer_pulse = tonumber(os.getenv("PDRIFT_STEER_PULSE") or "")
assert(not steer_pulse or (steer_pulse >= 32 and steer_pulse <= 224))
local steer_return = tonumber(os.getenv("PDRIFT_STEER_RETURN") or "1080")
assert(steer_return and steer_return > 960 and steer_return <= 1080)
local frames = 0
local debug_watch = debug_mode == "1" or debug_mode == "shared"
  or debug_mode == "reads"
local cpu_debug = debug_watch and assert(manager.machine.devices[":maincpu"].debug)
local watchpoints = {}
if debug_watch then
  assert(manager.machine.debugger)
  manager.machine.debugger.execution_state = "run"
end
local captures = { [300] = true, [600] = true, [900] = true,
                   [1020] = true, [1080] = true, [1140] = true,
                   [1200] = true, [1500] = true, [1800] = true }
local ram_profile = os.getenv("PDRIFT_RAM_PROFILE") or "baseline"
assert(ram_profile == "baseline" or ram_profile == "early")
local ram_captures = { [900] = true, [960] = true, [1020] = true,
                       [1080] = true, [1140] = true, [1200] = true }
local ram_windows = { main_low = 0x1f0000, main_high = 0x1fc000,
                      shared = 0x0c0000 }
if ram_profile == "early" then
  ram_captures = { [960] = true, [961] = true, [962] = true,
                   [965] = true, [970] = true, [980] = true,
                   [1000] = true, [1020] = true }
  ram_windows = { main_mid1 = 0x1f4000, main_mid2 = 0x1f8000,
                  main_high = 0x1fc000, shared_mid1 = 0x0c4000,
                  shared_mid2 = 0x0c8000, shared_high = 0x0cc000 }
end
local ram_size = 0x4000
local rotate_space = rotate_output
  and assert(manager.machine.devices[":suby"].spaces["program"])
local rotate_captures = { [961] = true, [962] = true, [965] = true,
                          [970] = true, [980] = true, [1000] = true,
                          [1020] = true }
local function capture_ram(frame, name, address)
  local bytes = {}
  for offset = 0, ram_size - 1 do
    bytes[#bytes + 1] = string.char(ram_space:read_u8(address + offset))
  end
  local path = string.format("%s/ram-%04d-%s.bin", ram_output, frame, name)
  local file = assert(io.open(path, "wb"))
  assert(file:write(table.concat(bytes)))
  assert(file:close())
  print(string.format("RAM,%d,%s,%06X,%d,%s", frame, name, address, ram_size, path))
end
local function capture_rotate(frame)
  local bytes = {}
  for offset = 0, 31 do
    bytes[#bytes + 1] = string.char(rotate_space:read_u8(0x1807e0 + offset))
  end
  local path = string.format("%s/rotate-%04d.bin", rotate_output, frame)
  local file = assert(io.open(path, "wb"))
  assert(file:write(table.concat(bytes)))
  assert(file:close())
  print(string.format("ROTATE,%d,1807E0,32,%s", frame, path))
end
coin:set_value(0)
start:set_value(0)
pedal:set_value(0)
steering:set_value(128)
print("INPUT_SCHEDULE=coin60-64,start130-134,pedal240+,steer128")
print("STEER_PULSE=" .. tostring(steer_pulse))
print("STEER_RETURN=" .. steer_return)
print("RAM_PROFILE=" .. ram_profile)
emu.register_frame_done(function()
  frames = frames + 1
  if frames == 60 then coin:set_value(1); print("INPUT,60,coin-on") end
  if frames == 65 then coin:set_value(0); print("INPUT,65,coin-off") end
  if frames == 130 then start:set_value(1); print("INPUT,130,start-on") end
  if frames == 135 then start:set_value(0); print("INPUT,135,start-off") end
  if frames == 240 then pedal:set_value(255); print("INPUT,240,pedal1-255") end
  if steer_pulse and frames == 960 then
    steering:set_value(steer_pulse)
    print(string.format("INPUT,960,steer-%d", steer_pulse))
  end
  if debug_mode == "1" and frames == 960 then
    local action = 'printf "WATCH addr=%06X data=%08X pc=%06X sp=%06X\\n",wpaddr,wpdata,pc,a7;g'
    watchpoints[1] = cpu_debug:wpset(ram_space, "w", 0x1fff72, 2, "wpdata!=3d00", action)
    watchpoints[2] = cpu_debug:wpset(ram_space, "w", 0x1fffc4, 2, "1", action)
    print(string.format("WATCH_ARMED,%s,%s", tostring(watchpoints[1]), tostring(watchpoints[2])))
  end
  if debug_mode == "1" and frames == 1020 then
    for _, index in ipairs(watchpoints) do cpu_debug:wpclear(index) end
    print("WATCH_CLEARED,1020")
  end
  if debug_mode == "shared" and frames == 960 then
    local disasm_dir = os.getenv("PDRIFT_DISASM_DIR")
    if disasm_dir then
      manager.machine.debugger.visible_cpu = manager.machine.devices[":maincpu"]
      for _, item in ipairs({ { "input", 0x37480 }, { "offset", 0x37520 },
                             { "accum", 0x34f50 } }) do
        local path = string.format("%s/%s.asm", disasm_dir, item[1])
        manager.machine.debugger:command(
          string.format("dasm %s,%X,80,0,:maincpu", path, item[2]))
        print("DISASM," .. path)
      end
    end
    for _, tag in ipairs({ "maincpu", "subx", "suby" }) do
      local device = assert(manager.machine.devices[":" .. tag])
      local debugger = assert(device.debug)
      local space = assert(device.spaces["program"])
      for _, address in ipairs({ 0x0ce0ce, 0x0cea0e, 0x0cff26 }) do
        local action = string.format(
          'printf "WATCH cpu=%s addr=%%06X data=%%08X pc=%%06X\\n",wpaddr,wpdata,pc;g', tag)
        local index = debugger:wpset(space, "w", address, 2, "1", action)
        watchpoints[#watchpoints + 1] = { debugger, index }
      end
    end
    print("WATCH_ARMED,shared," .. tostring(#watchpoints))
  end
  if debug_mode == "shared" and frames == 965 then
    for _, watch in ipairs(watchpoints) do watch[1]:wpclear(watch[2]) end
    print("WATCH_CLEARED,965")
  end
  if debug_mode == "reads" and frames == 960 then
    local read_cpu = os.getenv("PDRIFT_READ_CPU")
    assert(not read_cpu or read_cpu == "suby")
    if read_cpu then
      manager.machine.debugger.visible_cpu = manager.machine.devices[":" .. read_cpu]
    end
    local disasm_dir = os.getenv("PDRIFT_DISASM_DIR")
    if disasm_dir then
      for _, item in ipairs({ { "suby-13400", 0x133f0, ":suby" },
                             { "suby-13450", 0x13450, ":suby" },
                             { "main-339", 0x338f0, ":maincpu" } }) do
        local path = string.format("%s/%s.asm", disasm_dir, item[1])
        manager.machine.debugger:command(
          string.format("dasm %s,%X,80,0,%s", path, item[2], item[3]))
        print("DISASM," .. path)
      end
    end
    for _, tag in ipairs(read_cpu and { read_cpu } or { "maincpu", "subx", "suby" }) do
      local device = assert(manager.machine.devices[":" .. tag])
      local debugger = assert(device.debug)
      local space = assert(device.spaces["program"])
      for _, address in ipairs({ 0x0ce0ce, 0x0cea0e }) do
        local action = string.format(
          'printf "READ cpu=%s addr=%%06X pc=%%06X\\n",wpaddr,pc;g', tag)
        local index = debugger:wpset(space, "r", address, 2, "1", action)
        watchpoints[#watchpoints + 1] = { debugger, index }
      end
    end
    print("WATCH_ARMED,reads," .. tostring(#watchpoints))
  end
  if debug_mode == "reads" and frames == 965 then
    for _, watch in ipairs(watchpoints) do watch[1]:wpclear(watch[2]) end
    print("WATCH_CLEARED,965")
  end
  if steer_pulse and frames == steer_return then
    steering:set_value(128)
    print(string.format("INPUT,%d,steer-128", steer_return))
  end
  if captures[frames] then
    local path = string.format("%s/phase1b-trial-%04d.png", output, frames)
    print(string.format("SNAPSHOT,%d,%s,%s", frames, path,
      tostring(screen:snapshot(path))))
  end
  if ram_output and ram_captures[frames] then
    for name, address in pairs(ram_windows) do
      capture_ram(frames, name, address)
    end
  end
  if rotate_output and rotate_captures[frames] then
    capture_rotate(frames)
  end
end, "frame")
