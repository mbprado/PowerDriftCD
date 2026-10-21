local ports = manager.machine.ioport.ports
local coin = assert(ports[":GENERAL"].fields["Coin 1"])
local start = assert(ports[":GENERAL"].fields["1 Player Start"])
local pedal = assert(ports[":ADC.4"].fields["P1 Pedal 1"])
local steering = assert(ports[":ADC.5"].fields["Paddle"])
local screen = assert(manager.machine.screens[":screen"])
local output = assert(os.getenv("PDRIFT_SNAPSHOT_DIR"))
local ram_output = os.getenv("PDRIFT_RAM_DIR")
local rotate_output = os.getenv("PDRIFT_ROTATE_DIR")
local swap_output = os.getenv("PDRIFT_SWAP_DIR")
local rotate_override = os.getenv("PDRIFT_ROTATE_OVERRIDE")
assert(not rotate_override or swap_output)
local rotate_override_words
if rotate_override then
  local file = assert(io.open(rotate_override, "rb"))
  local bytes = assert(file:read("*a"))
  assert(file:close())
  assert(#bytes == 32)
  rotate_override_words = {}
  for index = 1, 16 do
    local offset = 2 * index - 1
    rotate_override_words[index] = (bytes:byte(offset) << 8)
      | bytes:byte(offset + 1)
  end
end
local source_output = os.getenv("PDRIFT_SOURCE_DIR")
local source_override = os.getenv("PDRIFT_SOURCE_OVERRIDE")
local source_override_range = os.getenv("PDRIFT_SOURCE_OVERRIDE_RANGE")
local state_save = os.getenv("PDRIFT_STATE_SAVE")
local state_load = os.getenv("PDRIFT_STATE_LOAD")
assert(not state_save or not state_load)
assert(not source_override or source_output)
assert(not source_override_range or source_override)
local override_start, override_size = 0, 0x10000
if source_override_range then
  local start_hex, size_hex = source_override_range:match("^(%x+):(%x+)$")
  assert(start_hex and size_hex,
    "PDRIFT_SOURCE_OVERRIDE_RANGE must be hex start:size")
  override_start = assert(tonumber(start_hex, 16))
  override_size = assert(tonumber(size_hex, 16))
  assert(override_start % 16 == 0 and override_size % 16 == 0
    and override_size > 0 and override_start + override_size <= 0x10000,
    "source override range must be 16-byte aligned and within 64 KiB")
end
local debug_mode = os.getenv("PDRIFT_DEBUG_WATCH")
assert(not debug_mode or debug_mode == "1" or debug_mode == "shared"
  or debug_mode == "reads" or debug_mode == "ysprite")
local ram_space = (ram_output or debug_mode)
  and assert(manager.machine.devices[":maincpu"].spaces["program"])
local steer_pulse = tonumber(os.getenv("PDRIFT_STEER_PULSE") or "")
assert(not steer_pulse or (steer_pulse >= 32 and steer_pulse <= 224))
local steer_return = tonumber(os.getenv("PDRIFT_STEER_RETURN") or "1080")
assert(steer_return and steer_return > 960 and steer_return <= 1080)
local frames = 0
local state_ready = not state_load
local debug_watch = debug_mode == "1" or debug_mode == "shared"
  or debug_mode == "reads" or debug_mode == "ysprite"
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
local rotate_space = (rotate_output or swap_output)
  and assert(manager.machine.devices[":suby"].spaces["program"])
local source_x_space = source_output
  and assert(manager.machine.devices[":subx"].spaces["program"])
local source_y_space = source_output
  and assert(manager.machine.devices[":suby"].spaces["program"])
local swap_read_tap
local swap_write_tap
local swaps = 0
local writes_since_swap = 0
local rotation_overrides = 0
local swap_shadow = {}
local function swap_bytes(words)
  local bytes = {}
  for _, word in ipairs(words) do
    bytes[#bytes + 1] = string.char((word >> 8) & 0xff, word & 0xff)
  end
  return table.concat(bytes)
end
local function save_swap_words(kind, words)
  local path = string.format("%s/swap-%s-%04d-%03d.bin",
    swap_output, kind, frames, swaps)
  local file = assert(io.open(path, "wb"))
  assert(file:write(swap_bytes(words)))
  assert(file:close())
  return path
end
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
local function capture_source(frame, name, space, address, size)
  local bytes = {}
  for offset = 0, size - 1 do
    bytes[#bytes + 1] = string.char(space:read_u8(address + offset))
  end
  local path = string.format("%s/source-%04d-%s.bin", source_output, frame, name)
  local file = assert(io.open(path, "wb"))
  assert(file:write(table.concat(bytes)))
  assert(file:close())
  print(string.format("SOURCE,%d,%s,%06X,%d,%s",
    frame, name, address, size, path))
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
  if not state_ready then return end
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
  if swap_output and frames == 955 then
    for index = 1, 16 do
      swap_shadow[index] = rotate_space:read_u16(0x1807e0 + 2 * (index - 1))
    end
    swap_write_tap = rotate_space:install_write_tap(
      0x1807e0, 0x1807ff, "pdrift-rotation-parameter-writes",
      function(offset, data, mask)
        local index = math.floor((offset - 0x1807e0) / 2) + 1
        assert(index >= 1 and index <= 16)
        if rotate_override_words and frames == 966 then
          data = rotate_override_words[index]
          rotation_overrides = rotation_overrides + 1
        end
        swap_shadow[index] = (swap_shadow[index] & (~mask & 0xffff))
          | (data & mask)
        writes_since_swap = writes_since_swap + 1
        if rotate_override_words and frames == 966 then return data end
      end)
    swap_read_tap = rotate_space:install_read_tap(
      0x198000, 0x198001, "pdrift-rotation-buffer-swap",
      function()
        swaps = swaps + 1
        local pre = save_swap_words("pre", swap_shadow)
        for index = 1, 16 do
          swap_shadow[index] = rotate_space:read_u16(0x1807e0 + 2 * (index - 1))
        end
        local post = save_swap_words("post", swap_shadow)
        print(string.format("SWAP,%d,%d,%d,%s,%s", frames, swaps,
          writes_since_swap, pre, post))
        if rotation_overrides > 0 then
          print(string.format("ROTATE_OVERRIDE,%d,%d,%s", frames,
            rotation_overrides, rotate_override))
          rotation_overrides = 0
        end
        writes_since_swap = 0
      end)
    print("SWAP_TRACE_ARMED,955")
  end
  if swap_output and frames == 1021 then
    swap_read_tap:remove()
    swap_write_tap:remove()
    print(string.format("SWAP_TRACE_CLEARED,1021,%d", swaps))
  end
  if swap_output and frames >= 960 and frames <= 970 then
    local mismatches = 0
    for index = 1, 16 do
      if swap_shadow[index] ~= rotate_space:read_u16(0x1807e0 + 2 * (index - 1)) then
        mismatches = mismatches + 1
      end
    end
    print(string.format("SWAP_SHADOW,%d,%d", frames, mismatches))
    local path = string.format("%s/swap-screen-%04d.png", swap_output, frames)
    print(string.format("SWAP_SCREEN,%d,%s,%s", frames, path,
      tostring(screen:snapshot(path))))
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
  if debug_mode == "ysprite" and frames == 960 then
    local subx = assert(manager.machine.devices[":subx"])
    manager.machine.debugger.visible_cpu = subx
    local disasm_dir = os.getenv("PDRIFT_DISASM_DIR")
    if disasm_dir then
      local path = disasm_dir .. "/subx-ysprite-writer.asm"
      manager.machine.debugger:command(
        string.format("dasm %s,E080,100,0,:subx", path))
      print("DISASM," .. path)
    end
    local debugger = assert(subx.debug)
    local space = assert(subx.spaces["program"])
    local action = 'printf "YSPRITE_WRITE addr=%06X data=%08X pc=%06X\\n",wpaddr,wpdata,pc;g'
    local index = debugger:wpset(space, "w", 0x18e6e0, 16, "1", action)
    watchpoints[#watchpoints + 1] = { debugger, index }
    print("WATCH_ARMED,ysprite,18E6E0,16")
  end
  if debug_mode == "ysprite" and frames == 967 then
    for _, watch in ipairs(watchpoints) do watch[1]:wpclear(watch[2]) end
    print("WATCH_CLEARED,ysprite,967")
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
  if source_output and frames >= 960 and frames <= 970 then
    capture_source(frames, "ysprites", source_x_space, 0x180000, 0x10000)
    capture_source(frames, "bsprites", source_y_space, 0x188000, 0x1000)
    capture_source(frames, "palette", source_y_space, 0x190000, 0x4000)
  end
  if source_override and frames == 966 then
    local file = assert(io.open(source_override, "rb"))
    local bytes = assert(file:read("*a"))
    assert(file:close())
    assert(#bytes == 0x10000)
    for offset = override_start, override_start + override_size - 1 do
      source_x_space:write_u8(0x180000 + offset, bytes:byte(offset + 1))
    end
    print(string.format("SOURCE_OVERRIDE,966,ysprites,%04X,%04X,%s",
      override_start, override_size, source_override))
    capture_source(frames, "ysprites-after", source_x_space, 0x180000, 0x10000)
  end
  if state_save and frames == 950 then
    print("STATE_SAVE,950," .. state_save)
    manager.machine:save(state_save)
  end
end, "frame")
if state_load then
  emu.add_machine_post_load_notifier(function()
    frames = 950
    pedal:set_value(255)
    steering:set_value(128)
    state_ready = true
    print("STATE_LOAD,950," .. state_load)
  end)
  manager.machine:load(state_load)
end
