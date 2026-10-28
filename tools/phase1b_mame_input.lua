local ports = manager.machine.ioport.ports
local coin = assert(ports[":GENERAL"].fields["Coin 1"])
local start = assert(ports[":GENERAL"].fields["1 Player Start"])
local pedal = assert(ports[":ADC.4"].fields["P1 Pedal 1"])
local steering = assert(ports[":ADC.5"].fields["Paddle"])
local screen = assert(manager.machine.screens[":screen"])
local output = assert(os.getenv("PDRIFT_SNAPSHOT_DIR"))
local ram_output = os.getenv("PDRIFT_RAM_DIR")
local geometry_output = os.getenv("PDRIFT_GEOMETRY_SAMPLE_DIR")
local list_output = os.getenv("PDRIFT_SHARED_LIST_DIR")
local sequence_end = tonumber(os.getenv("PDRIFT_SEQUENCE_END_FRAME") or "970")
assert(sequence_end and sequence_end >= 970 and sequence_end <= 1000)
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
local source_override_frame = tonumber(os.getenv("PDRIFT_SOURCE_OVERRIDE_FRAME") or "966")
local bsprite_override = os.getenv("PDRIFT_BSPRITE_OVERRIDE")
local bsprite_override_frame = tonumber(os.getenv("PDRIFT_BSPRITE_OVERRIDE_FRAME") or "979")
local bsprite_override_slot = tonumber(os.getenv("PDRIFT_BSPRITE_OVERRIDE_SLOT") or "", 16)
local capture_profile = os.getenv("PDRIFT_CAPTURE_PROFILE") or "full"
assert(capture_profile == "full" or capture_profile == "road-edge")
assert(capture_profile ~= "road-edge" or (source_output and (source_override or bsprite_override)))
assert(source_override_frame and source_override_frame >= 960
  and source_override_frame <= sequence_end)
assert(not bsprite_override or (source_output and bsprite_override_frame
  and bsprite_override_frame >= 960 and bsprite_override_frame <= sequence_end
  and bsprite_override_slot and bsprite_override_slot % 16 == 0
  and bsprite_override_slot >= 0 and bsprite_override_slot <= 0xff0))
local source_override_range = os.getenv("PDRIFT_SOURCE_OVERRIDE_RANGE")
local extra_screen_frame = tonumber(os.getenv("PDRIFT_EXTRA_SCREEN_FRAME") or "")
assert(not os.getenv("PDRIFT_EXTRA_SCREEN_FRAME") or extra_screen_frame == 971)
local state_save = os.getenv("PDRIFT_STATE_SAVE")
local state_load = os.getenv("PDRIFT_STATE_LOAD")
assert(not state_save or not state_load)
local state7a_delta_frame = tonumber(os.getenv("PDRIFT_STATE7A_DELTA_FRAME") or "")
local state7a_delta = tonumber(os.getenv("PDRIFT_STATE7A_DELTA") or "")
assert((not state7a_delta_frame and not state7a_delta)
  or (state_load and (state7a_delta_frame == 965 or state7a_delta_frame == 966)
    and state7a_delta
    and state7a_delta >= -16 and state7a_delta <= 16
    and state7a_delta ~= 0))
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
  or debug_mode == "reads" or debug_mode == "ysprite"
  or debug_mode == "projection" or debug_mode == "transform"
  or debug_mode == "bsprite")
local shared_watch_address = os.getenv("PDRIFT_SHARED_WATCH_ADDR")
  and tonumber(os.getenv("PDRIFT_SHARED_WATCH_ADDR"), 16)
local shared_watch_until = tonumber(os.getenv("PDRIFT_SHARED_WATCH_UNTIL") or "")
assert(not os.getenv("PDRIFT_SHARED_WATCH_UNTIL") or
  (debug_mode == "shared" and shared_watch_address and shared_watch_until
    and shared_watch_until >= 967 and shared_watch_until <= 975))
assert(not os.getenv("PDRIFT_SHARED_WATCH_ADDR") or
  (debug_mode == "shared" and shared_watch_address
    and shared_watch_address >= 0x0c0000
    and shared_watch_address <= 0x0cfff0
    and shared_watch_address % 2 == 0))
local ysprite_watch_offset = tonumber(os.getenv("PDRIFT_YSPRITE_WATCH_OFFSET") or "E6E0", 16)
assert(ysprite_watch_offset and ysprite_watch_offset % 16 == 0
  and ysprite_watch_offset >= 0 and ysprite_watch_offset <= 0xfff0)
local ysprite_input_trace = os.getenv("PDRIFT_YSPRITE_INPUT_TRACE") == "1"
assert(not ysprite_input_trace or debug_mode == "ysprite")
local ysprite_sequence_trace = os.getenv("PDRIFT_YSPRITE_SEQUENCE_TRACE") == "1"
assert(not ysprite_sequence_trace or debug_mode == "ysprite")
local ysprite_sequence_last_kind = tonumber(
  os.getenv("PDRIFT_YSPRITE_SEQUENCE_LAST_KIND") or "20", 16)
assert(ysprite_sequence_last_kind and ysprite_sequence_last_kind >= 0x20
  and ysprite_sequence_last_kind <= 0x27)
assert(not os.getenv("PDRIFT_YSPRITE_SEQUENCE_LAST_KIND") or
  ysprite_sequence_trace)
local ysprite_sequence_end = tonumber(
  os.getenv("PDRIFT_YSPRITE_SEQUENCE_END_FRAME") or "971")
assert(not os.getenv("PDRIFT_YSPRITE_SEQUENCE_END_FRAME") or
  (ysprite_sequence_trace and ysprite_sequence_end
    and ysprite_sequence_end >= 971 and ysprite_sequence_end <= 1000))
local ram_space = (ram_output or debug_mode or geometry_output or list_output
  or state7a_delta_frame)
  and assert(manager.machine.devices[":maincpu"].spaces["program"])
local geometry_file
if geometry_output then
  geometry_file = assert(io.open(geometry_output .. "/geometry-samples.csv", "w"))
  assert(geometry_file:write("frame,index,object,depth,table,sample0,sample1,sample2,source16,source18,source1a,projected4,projected6,global16,global18,global1a,global1c,global1e,global20,global24,global26,coef1sin,coef1cos,coef2sin,coef2cos,screen_y_offset\n"))
end
local record_tap_enabled = os.getenv("PDRIFT_RECORD_TAP") == "1"
assert(not record_tap_enabled or ram_space)
local record_override_value = os.getenv("PDRIFT_RECORD_OVERRIDE_VALUE")
  and tonumber(os.getenv("PDRIFT_RECORD_OVERRIDE_VALUE"), 16)
local record_override_frame = tonumber(os.getenv("PDRIFT_RECORD_OVERRIDE_FRAME") or "")
assert((not os.getenv("PDRIFT_RECORD_OVERRIDE_VALUE")
    and not os.getenv("PDRIFT_RECORD_OVERRIDE_FRAME"))
  or (record_tap_enabled and record_override_value
    and record_override_value >= 0 and record_override_value <= 0xffff
    and record_override_frame and record_override_frame >= 955
    and record_override_frame <= 967))
local record_tap
local steer_pulse = tonumber(os.getenv("PDRIFT_STEER_PULSE") or "")
assert(not steer_pulse or (steer_pulse >= 32 and steer_pulse <= 224))
local steer_return = tonumber(os.getenv("PDRIFT_STEER_RETURN") or "1080")
assert(steer_return and steer_return > 960 and steer_return <= 1080)
local frames = 0
local state_ready = not state_load
local debug_watch = debug_mode == "1" or debug_mode == "shared"
  or debug_mode == "reads" or debug_mode == "ysprite"
  or debug_mode == "projection" or debug_mode == "transform"
  or debug_mode == "bsprite"
local cpu_debug = debug_watch and assert(manager.machine.devices[":maincpu"].debug)
local watchpoints = {}
local bsprite_write_tap
local bsprite_stage_tap
local bsprite_write_counts = {}
local input_breakpoints = {}
local main_record_breakpoints = {}
local geometry_override_word = os.getenv("PDRIFT_GEOMETRY_OVERRIDE_WORD")
  and tonumber(os.getenv("PDRIFT_GEOMETRY_OVERRIDE_WORD"), 16)
assert(not os.getenv("PDRIFT_GEOMETRY_OVERRIDE_WORD") or
  (debug_mode == "shared" and geometry_override_word
    and geometry_override_word >= 0 and geometry_override_word <= 0xffff))
local projection_global_x_delta = os.getenv("PDRIFT_PROJECTION_GLOBAL_X_DELTA")
  and tonumber(os.getenv("PDRIFT_PROJECTION_GLOBAL_X_DELTA"), 16)
assert(not os.getenv("PDRIFT_PROJECTION_GLOBAL_X_DELTA") or
  (debug_mode == "shared" and projection_global_x_delta
    and projection_global_x_delta >= 0 and projection_global_x_delta <= 0x100
    and not geometry_override_word))
if debug_watch then
  assert(manager.machine.debugger)
  manager.machine.debugger.execution_state = "run"
end
if debug_mode == "bsprite" then
  local suby = assert(manager.machine.devices[":suby"])
  manager.machine.debugger.visible_cpu = suby
  local space = suby.spaces["program"]
  local initial = {}
  for offset = 0, 14, 2 do
    initial[#initial + 1] = string.format("%04X",
      space:read_u16(0x188040 + offset))
  end
  print("BSPRITE_INITIAL," .. table.concat(initial, ","))
  local action = 'printf "BSPRITE_WRITE pc=%06X addr=%06X data=%08X a0=%06X a1=%06X a2=%06X a3=%06X a4=%06X a5=%06X d0=%08X d1=%08X d2=%08X d3=%08X\\n",pc,wpaddr,wpdata,a0,a1,a2,a3,a4,a5,d0,d1,d2,d3;g'
  local index = suby.debug:wpset(suby.spaces["program"], "w",
    0x188040, 16, "1", action)
  watchpoints[#watchpoints + 1] = { suby.debug, index }
  print("BSPRITE_WATCH_ARMED,000,188040,16")
  local stage_action = 'printf "BSTAGE_WRITE pc=%06X addr=%06X data=%08X a0=%06X a1=%06X a2=%06X a3=%06X a4=%06X a5=%06X d0=%08X d1=%08X d2=%08X d3=%08X\\n",pc,wpaddr,wpdata,a0,a1,a2,a3,a4,a5,d0,d1,d2,d3;g'
  local stage_index = suby.debug:wpset(space, "w", 0x1f8630, 12,
    "1", stage_action)
  watchpoints[#watchpoints + 1] = { suby.debug, stage_index }
  bsprite_stage_tap = space:install_write_tap(
    0x1f8630, 0x1f863b, "pdrift-bsprite-stage-writes",
    function(offset, data, mask)
      print(string.format("BSTAGE_TAP,%d,%06X,%08X,%08X",
        frames, offset, data, mask))
    end)
  print("BSTAGE_WATCH_ARMED,000,1F8630,12")
  bsprite_write_tap = space:install_write_tap(
    0x188000, 0x18ffff, "pdrift-bsprite-mirror-writes",
    function(offset, data, mask)
      local mirror = (offset >> 12) & 7
      bsprite_write_counts[mirror] = (bsprite_write_counts[mirror] or 0) + 1
      if (offset & 0xfff) >= 0x40 and (offset & 0xfff) <= 0x4f then
        print(string.format("BSPRITE_TAP,%d,%06X,%08X,%08X",
          frames, offset, data, mask))
      end
    end)
  print("BSPRITE_TAP_ARMED,000,188000,8000")
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
local function capture_shared_list(frame)
  local bytes = {}
  for offset = 0, 0x1fff do
    bytes[#bytes + 1] = string.char(ram_space:read_u8(0x0c9800 + offset))
  end
  local path = string.format("%s/shared-list-%04d.bin", list_output, frame)
  local file = assert(io.open(path, "wb"))
  assert(file:write(table.concat(bytes)))
  assert(file:close())
  print(string.format("SHARED_LIST,%d,0C9800,8192,%s", frame, path))
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
print("CAPTURE_PROFILE=" .. capture_profile)
emu.register_frame_done(function()
  if not state_ready then return end
  frames = frames + 1
  if debug_mode == "bsprite" and frames <= 982 then
    print(string.format("BSPRITE_FRAME,%d", frames))
  end
  if debug_mode == "bsprite" and frames >= 411 and frames <= 413
      and source_output then
    capture_source(frames, "bsource", source_y_space, 0x1f8600, 0x100)
    capture_source(frames, "bobject", source_y_space, 0x1f8000, 0x100)
    capture_source(frames, "bshared", source_y_space, 0x0c1500, 0x100)
  end
  if debug_mode == "bsprite" and frames == 413 then
    local disasm_dir = os.getenv("PDRIFT_BSPRITE_DISASM_DIR")
    if disasm_dir then
      local path = disasm_dir .. "/suby-bsprite-writer.asm"
      manager.machine.debugger:command(
        string.format("dasm %s,13120,100,0,:suby", path))
      print("BSPRITE_DISASM," .. path)
    end
  end
  if (ysprite_sequence_trace or debug_mode == "projection"
      or debug_mode == "transform") and frames >= 960 and
      frames <= ((debug_mode == "projection" or debug_mode == "transform")
        and sequence_end or ysprite_sequence_end) then
    manager.machine.debugger:command(
      string.format('printf "SEQUENCE_FRAME,%d\\n"', frames))
  end
  if frames == 60 then coin:set_value(1); print("INPUT,60,coin-on") end
  if frames == 65 then coin:set_value(0); print("INPUT,65,coin-off") end
  if frames == 130 then start:set_value(1); print("INPUT,130,start-on") end
  if frames == 135 then start:set_value(0); print("INPUT,135,start-off") end
  if frames == 240 then pedal:set_value(255); print("INPUT,240,pedal1-255") end
  if debug_mode == "bsprite" and frames == 982 then
    for _, watch in ipairs(watchpoints) do watch[1]:wpclear(watch[2]) end
    bsprite_write_tap:remove()
    bsprite_stage_tap:remove()
    for mirror = 0, 7 do
      print(string.format("BSPRITE_MIRROR_COUNT,%d,%d",
        mirror, bsprite_write_counts[mirror] or 0))
    end
    print("BSPRITE_WATCH_CLEARED,982")
  end
  if steer_pulse and frames == 960 then
    steering:set_value(steer_pulse)
    print(string.format("INPUT,960,steer-%d", steer_pulse))
  end
  if state7a_delta_frame and frames == state7a_delta_frame then
    local address = 0x0c08ba
    local before = ram_space:read_u16(address)
    local after = (before + state7a_delta) & 0xffff
    ram_space:write_u16(address, after)
    assert(ram_space:read_u16(address) == after)
    print(string.format("STATE7A_DELTA,%d,%06X,%04X,%04X,%d",
      frames, address, before, after, state7a_delta))
  end
  if record_tap_enabled and frames == 955 then
    record_tap = ram_space:install_write_tap(
      0x0c1c84, 0x0c1c85, "pdrift-main-source-record-x",
      function(offset, data, mask)
        print(string.format("RECORD_TAP,%d,%06X,%04X,%04X",
          frames, offset, data, mask))
        if record_override_frame and frames == record_override_frame then
          assert(mask == 0xffff)
          print(string.format("RECORD_OVERRIDE,%d,%06X,%04X,%04X",
            frames, offset, data, record_override_value))
          return record_override_value
        end
      end)
    print("RECORD_TAP_ARMED,955,0C1C84")
  end
  if record_tap_enabled and frames == 968 then
    record_tap:remove()
    print("RECORD_TAP_CLEARED,968")
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
  if swap_output and frames >= 960 and
      (frames <= sequence_end or frames == extra_screen_frame) then
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
  if geometry_file and frames >= 960 and frames <= sequence_end then
    local table_base = (ram_space:read_u16(0x0ceb00) << 16)
      | ram_space:read_u16(0x0ceb02)
    local globals = {}
    for _, offset in ipairs({ 0x16, 0x18, 0x1a, 0x1c, 0x1e, 0x20 }) do
      globals[#globals + 1] = ram_space:read_u16(0x0c0080 + offset)
    end
    local angle2 = ram_space:read_u16(0x0c0080 + 0x24)
    local angle1 = ram_space:read_u16(0x0c0080 + 0x26)
    local lookup1 = 0x0ef6 + 2 * angle1
    local lookup2 = 0x0ef6 + 2 * angle2
    local coefficients = {
      angle2, angle1,
      ram_space:read_u16(lookup1 - 0x600), ram_space:read_u16(lookup1),
      ram_space:read_u16(lookup2 - 0x600), ram_space:read_u16(lookup2),
      ram_space:read_u16(0x0cea3e),
    }
    for index = 0, 11 do
      local object = 0x0c1c80 + index * 0x40
      local depth = ram_space:read_u16(object + 0x3e)
      local sample = table_base + 6 * ((depth & 0xffe0) >> 5)
      local values = {
        frames, index, object, depth, sample,
        ram_space:read_u16(sample), ram_space:read_u16(sample + 2),
        ram_space:read_u16(sample + 4),
        ram_space:read_u16(object + 0x16),
        ram_space:read_u16(object + 0x18),
        ram_space:read_u16(object + 0x1a),
        ram_space:read_u16(object + 0x04),
        ram_space:read_u16(object + 0x06),
      }
      for _, value in ipairs(globals) do values[#values + 1] = value end
      for _, value in ipairs(coefficients) do values[#values + 1] = value end
      assert(geometry_file:write(string.format(
        "%d,%d,%06X,%04X,%06X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X,%04X\n",
        table.unpack(values))))
    end
    print(string.format("GEOMETRY_SAMPLES,%d,12,%06X", frames, table_base))
    if frames == sequence_end then assert(geometry_file:close()) end
  end
  if list_output and frames >= 960 and frames <= sequence_end then
    capture_shared_list(frames)
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
  if debug_mode == "shared" and frames ==
      (os.getenv("PDRIFT_SHARED_WATCH_FROM_BOOT") == "1" and 1 or 960) then
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
      if shared_watch_address then
        local path = disasm_dir .. "/main-sprite-record-writer.asm"
        manager.machine.debugger:command(
          string.format("dasm %s,33E00,100,0,:maincpu", path))
        print("DISASM," .. path)
        local transform_path = disasm_dir .. "/main-sprite-transform.asm"
        manager.machine.debugger:command(
          string.format("dasm %s,33D00,100,0,:maincpu", transform_path))
        print("DISASM," .. transform_path)
        if os.getenv("PDRIFT_MAIN_RECORD_TRACE") == "1" then
          local caller_path = disasm_dir .. "/main-sprite-caller.asm"
          manager.machine.debugger:command(
            string.format("dasm %s,33A00,400,0,:maincpu", caller_path))
          print("DISASM," .. caller_path)
        end
      end
      if os.getenv("PDRIFT_GLOBAL_DISASM") == "1" then
        for _, item in ipairs({ { "main-global-angle", 0x338f0 },
                                 { "main-global-position", 0x347c0 } }) do
          local path = disasm_dir .. "/" .. item[1] .. ".asm"
          manager.machine.debugger:command(
            string.format("dasm %s,%X,200,0,:maincpu", path, item[2]))
          print("DISASM," .. path)
        end
      end
      if os.getenv("PDRIFT_GEOMETRY_DISASM") == "1" then
        local path = disasm_dir .. "/main-geometry-table-select.asm"
        manager.machine.debugger:command(
          string.format("dasm %s,385E0,200,0,:maincpu", path))
        print("DISASM," .. path)
      end
    end
    for _, tag in ipairs({ "maincpu", "subx", "suby" }) do
      local device = assert(manager.machine.devices[":" .. tag])
      local debugger = assert(device.debug)
      local space = assert(device.spaces["program"])
      for _, address in ipairs(shared_watch_address and { shared_watch_address }
          or { 0x0ce0ce, 0x0cea0e, 0x0cff26 }) do
        local action = string.format(
          'printf "WATCH cpu=%s addr=%%06X data=%%08X pc=%%06X\\n",wpaddr,wpdata,pc;g', tag)
        if shared_watch_address and os.getenv("PDRIFT_SHARED_REGS") == "1" then
          action = string.format(
            'printf "RECORD_WRITE cpu=%s addr=%%06X data=%%08X pc=%%06X a0=%%06X a5=%%06X d0=%%08X\\n",wpaddr,wpdata,pc,a0,a5,d0;g', tag)
        end
        local index = debugger:wpset(space, "w", address,
          shared_watch_address and 16 or 2, "1", action)
        watchpoints[#watchpoints + 1] = { debugger, index }
      end
    end
    print("WATCH_ARMED,shared," .. tostring(#watchpoints))
    if os.getenv("PDRIFT_MAIN_RECORD_TRACE") == "1" then
      local action = 'printf "MAIN_RECORD pc=%06X a0=%06X a1=%06X a2=%06X a3=%06X a4=%06X a5=%06X a6=%06X d0=%08X d1=%08X d2=%08X d6=%08X\\n",pc,a0,a1,a2,a3,a4,a5,a6,d0,d1,d2,d6'
      local fields = 'printf "MAIN_FIELDS pc=%06X first=%08X pos=%08X obj=%08X p16=%04X p18=%04X p1a=%04X p1c=%04X p1e=%04X p20=%04X flag32=%04X flag36=%04X depth=%04X cam16=%04X cam18=%04X cam1a=%04X cam1c=%04X cam1e=%04X cam20=%04X\\n",pc,d@a5,d@(a5+4),d@(a5+8),w@(a5+16),w@(a5+18),w@(a5+1a),w@(a5+1c),w@(a5+1e),w@(a5+20),w@(a5+32),w@(a5+36),w@(a5+3e),w@(a4+16),w@(a4+18),w@(a4+1a),w@(a4+1c),w@(a4+1e),w@(a4+20)'
      for _, pc in ipairs({ 0x33d1e, 0x33d56, 0x33e58, 0x33e84 }) do
        main_record_breakpoints[#main_record_breakpoints + 1] =
          cpu_debug:bpset(pc, "a5==c1c80",
            action .. (pc == 0x33d1e and ";" .. fields or "") .. ";g")
      end
      print("MAIN_RECORD_TRACE_ARMED,33D1E,33D56,33E58,33E84")
    end
    if os.getenv("PDRIFT_MAIN_OBJECT_LIST") == "1" then
      local action = 'printf "OBJECT_ENTRY pc=%06X a0=%06X a5=%06X first=%08X pos=%08X p16=%04X p18=%04X p1a=%04X depth=%04X\\n",pc,a0,a5,d@a5,d@(a5+4),w@(a5+16),w@(a5+18),w@(a5+1a),w@(a5+3e);g'
      main_record_breakpoints[#main_record_breakpoints + 1] =
        cpu_debug:bpset(0x33d1e, "a0==c9800", action)
      print("MAIN_OBJECT_LIST_ARMED,33D1E,0C9800")
    end
    if os.getenv("PDRIFT_MAIN_GEOMETRY_TRACE") == "1" then
      local action = 'printf "GEOMETRY_ENTRY pc=%06X a5=%06X a3=%06X table=%06X depth=%04X d0=%08X d1=%08X sample0=%04X sample1=%04X sample2=%04X\\n",pc,a5,a3,d@ceb00,w@(a5+3e),d0,d1,w@a3,w@(a3+2),w@(a3+4);g'
      main_record_breakpoints[#main_record_breakpoints + 1] =
        cpu_debug:bpset(0x33b22, "a5==c1c80", action)
      print("MAIN_GEOMETRY_TRACE_ARMED,33B22,0C1C80")
    end
    if geometry_override_word then
      local original = ram_space:read_u16(0x0c1c96)
      local condition = "a5==c1c80&&a0==c9800"
      local entry = string.format(
        'printf "GEOMETRY_OVERRIDE pc=%%06X old=%%04X new=%04X\\n",pc,w@(a5+16);w@(a5+16)=%04X;g',
        geometry_override_word, geometry_override_word)
      local exit_action = string.format(
        'printf "GEOMETRY_RESTORE pc=%%06X value=%04X\\n",pc;w@(a5+16)=%04X;g',
        original, original)
      main_record_breakpoints[#main_record_breakpoints + 1] =
        cpu_debug:bpset(0x33d1e, condition, entry)
      main_record_breakpoints[#main_record_breakpoints + 1] =
        cpu_debug:bpset(0x33e84, condition, exit_action)
      print(string.format("GEOMETRY_OVERRIDE_ARMED,%04X,%04X",
        original, geometry_override_word))
    end
    if projection_global_x_delta then
      for _, object in ipairs({ 0x0c1d00, 0x0c1d40, 0x0c1d80 }) do
        local condition = string.format("a5==%x&&a0==c9800", object)
        local entry = string.format(
          'printf "GLOBAL_X_ENTRY pc=%%06X a5=%%06X old=%%04X\\n",pc,a5,w@(a4+1c);w@(a4+1c)=w@(a4+1c)+%x;printf "GLOBAL_X_CHANGED a5=%%06X value=%%04X\\n",a5,w@(a4+1c);g',
          projection_global_x_delta)
        local exit_action = string.format(
          'printf "GLOBAL_X_OUTPUT a5=%%06X x=%%04X y=%%04X changed=%%04X\\n",a5,d0,w@(a5+6),w@(a4+1c);w@(a4+1c)=w@(a4+1c)-%x;printf "GLOBAL_X_RESTORED a5=%%06X value=%%04X\\n",a5,w@(a4+1c);g',
          projection_global_x_delta)
        main_record_breakpoints[#main_record_breakpoints + 1] =
          cpu_debug:bpset(0x33d1e, condition, entry)
        main_record_breakpoints[#main_record_breakpoints + 1] =
          cpu_debug:bpset(0x33e84, condition, exit_action)
      end
      print(string.format("GLOBAL_X_OVERRIDE_ARMED,%X,3", projection_global_x_delta))
    end
  end
  if debug_mode == "shared" and frames ==
      (shared_watch_until or (shared_watch_address and 967 or 965)) then
    for _, watch in ipairs(watchpoints) do watch[1]:wpclear(watch[2]) end
    for _, index in ipairs(main_record_breakpoints) do cpu_debug:bpclear(index) end
    print(string.format("WATCH_CLEARED,%d", frames))
  end
  if debug_mode == "projection" and frames == 960 then
    manager.machine.debugger.visible_cpu = manager.machine.devices[":maincpu"]
    local action = 'printf "PROJECTION_GATE pc=%06X a5=%06X d4=%08X flag=%04X old=%08X\\n",pc,a5,d4,w@cea42,d@(a5+4);g'
    main_record_breakpoints[1] = cpu_debug:bpset(0x33d8e,
      "a5>=c1c80&&a5<=c1f40&&((a5-c1c80)&3f)==0", action)
    main_record_breakpoints[2] = cpu_debug:bpset(0x33e00,
      "a5>=c1c80&&a5<=c1f40&&((a5-c1c80)&3f)==0",
      'printf "PROJECTION_DEPTH pc=%06X a5=%06X d2=%08X old=%08X\\n",pc,a5,d2,d@(a5+4);g')
    main_record_breakpoints[3] = cpu_debug:bpset(0x33e58,
      "a5>=c1c80&&a5<=c1f40&&((a5-c1c80)&3f)==0",
      'printf "PROJECTION_WRITE pc=%06X a5=%06X d0=%08X\\n",pc,a5,d0;g')
    print("PROJECTION_GATE_ARMED,33D8E,33E00,33E58,0C1C80_TO_0C1F40")
  end
  if debug_mode == "projection" and frames == sequence_end then
    for _, index in ipairs(main_record_breakpoints) do cpu_debug:bpclear(index) end
    print(string.format("PROJECTION_GATE_CLEARED,%d", frames))
  end
  if debug_mode == "transform" and frames == 960 then
    local disasm_dir = os.getenv("PDRIFT_DISASM_DIR")
    if disasm_dir then
      for _, item in ipairs({ { "main-transform-angle", 0x34680 },
                             { "main-transform-offset", 0x33940 },
                             { "main-transform-position", 0x34770 } }) do
        local path = string.format("%s/%s.asm", disasm_dir, item[1])
        manager.machine.debugger:command(
          string.format("dasm %s,%X,100,0,:maincpu", path, item[2]))
        print("DISASM," .. path)
      end
      if os.getenv("PDRIFT_TRANSFORM_UPSTREAM_TRACE") == "1" then
        for _, item in ipairs({ { "main-state-position", 0x34a80 },
                               { "main-state-offset", 0x34bd0 },
                               { "main-state-adjustment", 0x34dc0 },
                               { "main-state-lookup", 0x348f0 } }) do
          local path = string.format("%s/%s.asm", disasm_dir, item[1])
          manager.machine.debugger:command(
            string.format("dasm %s,%X,120,0,:maincpu", path, item[2]))
          print("DISASM," .. path)
        end
      end
    end
    for _, tag in ipairs({ "maincpu", "subx", "suby" }) do
      local device = assert(manager.machine.devices[":" .. tag])
      local debugger = assert(device.debug)
      local space = assert(device.spaces["program"])
      local action = string.format(
        'printf "TRANSFORM_WRITE cpu=%s pc=%%06X addr=%%06X data=%%08X a4=%%06X a5=%%06X d0=%%08X d1=%%08X\\n",pc,wpaddr,wpdata,a4,a5,d0,d1;g', tag)
      local index = debugger:wpset(space, "w", 0x0c0096, 0x12, "1", action)
      watchpoints[#watchpoints + 1] = { debugger, index }
      if os.getenv("PDRIFT_TRANSFORM_UPSTREAM_TRACE") == "1" then
        for _, item in ipairs({ { "position", 0x0c0856, 6 },
                               { "lookup", 0x0c087e, 2 },
                               { "angle_adjust", 0x0c08ba, 2 },
                               { "late_adjust", 0x0c08ea, 2 },
                               { "offset_source", 0x0c00ae, 2 } }) do
          local source_action = string.format(
            'printf "UPSTREAM_WRITE cpu=%s field=%s pc=%%06X addr=%%06X data=%%08X a5=%%06X d0=%%08X d1=%%08X\\n",pc,wpaddr,wpdata,a5,d0,d1;g',
            tag, item[1])
          local source_index = debugger:wpset(space, "w", item[2],
            item[3], "1", source_action)
          watchpoints[#watchpoints + 1] = { debugger, source_index }
        end
      end
    end
    if os.getenv("PDRIFT_TRANSFORM_SOURCE_TRACE") == "1" then
      local trace = {
        { 0x3397a, 'printf "TRANSFORM_OFFSET_SOURCE pc=%06X source=%04X\\n",pc,w@(a5+2e);g' },
        { 0x346ec, 'printf "TRANSFORM_ANGLE_SOURCE pc=%06X road_depth=%04X road_angle=%04X smooth=%04X adjustment=%04X tilt=%04X d2=%08X\\n",pc,w@(a5+3e),w@cea18,w@cea1c,w@cea3a,w@(a5+7a),d2;g' },
        { 0x3483c, 'printf "TRANSFORM_POSITION_SOURCE pc=%06X x=%04X y=%04X z=%04X\\n",pc,w@(a5+16),w@(a5+18),w@(a5+1a);g' },
        { 0x33d1e, 'printf "TRANSFORM_PROJECT pc=%06X off=%04X angle1=%04X angle2=%04X x=%04X y=%04X z=%04X\\n",pc,w@c0098,w@c00a6,w@c00a4,w@c009c,w@c009e,w@c00a0;g' },
      }
      if os.getenv("PDRIFT_TRANSFORM_UPSTREAM_TRACE") == "1" then
        trace[#trace + 1] = { 0x3490c,
          'printf "UPSTREAM_SPEED pc=%06X speed=%04X half=%04X old_depth=%04X\\n",pc,w@(a5+24),d0,w@(a5+3e);g' }
      end
      for _, item in ipairs(trace) do
        main_record_breakpoints[#main_record_breakpoints + 1] =
          cpu_debug:bpset(item[1], item[1] == 0x33d1e
            and "a5==c1c80" or "1", item[2])
      end
      print("TRANSFORM_SOURCE_TRACE_ARMED,3397A,346EC,3483C,33D1E")
    end
    print("TRANSFORM_WATCH_ARMED,0C0096,18,3_CPUS")
  end
  if debug_mode == "transform" and frames == sequence_end then
    for _, watch in ipairs(watchpoints) do watch[1]:wpclear(watch[2]) end
    for _, index in ipairs(main_record_breakpoints) do cpu_debug:bpclear(index) end
    print(string.format("TRANSFORM_WATCH_CLEARED,%d", frames))
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
      local caller_path = disasm_dir .. "/subx-ysprite-caller.asm"
      manager.machine.debugger:command(
        string.format("dasm %s,DD40,220,0,:subx", caller_path))
      print("DISASM," .. caller_path)
      local transform_path = disasm_dir .. "/subx-ysprite-transform.asm"
      manager.machine.debugger:command(
        string.format("dasm %s,DF80,100,0,:subx", transform_path))
      print("DISASM," .. transform_path)
    end
    local debugger = assert(subx.debug)
    local space = assert(subx.spaces["program"])
    local action = 'printf "YSPRITE_WRITE addr=%06X data=%08X pc=%06X\\n",wpaddr,wpdata,pc;g'
    if os.getenv("PDRIFT_YSPRITE_REGS") == "1" then
      action = 'printf "YSPRITE_REGS addr=%06X data=%08X pc=%06X d0=%08X d1=%08X d2=%08X a2=%06X a5=%06X\\n",wpaddr,wpdata,pc,d0,d1,d2,a2,a5;g'
    end
    local address = 0x180000 + ysprite_watch_offset
    local index = debugger:wpset(space, "w", address, 16, "1", action)
    watchpoints[#watchpoints + 1] = { debugger, index }
    print(string.format("WATCH_ARMED,ysprite,%06X,16", address))
    if ysprite_input_trace then
      local before = 'printf "YSPRITE_INPUT_BEFORE pc=%06X a0=%06X index=%08X a2=%06X\\n",pc,a0,d0,a2;g'
      local after = 'printf "YSPRITE_INPUT_AFTER pc=%06X a0=%06X d0=%08X d1=%08X d2=%08X d3=%08X a2=%06X\\n",pc,a0,d0,d1,d2,d3,a2;g'
      input_breakpoints[1] = debugger:bpset(0xdd64, "a2==18c630", before)
      input_breakpoints[2] = debugger:bpset(0xdd6a, "a2==18c630", after)
      print("INPUT_TRACE_ARMED,DD64,DD6A,18C630")
    end
    if ysprite_sequence_trace then
      local action = 'printf "SUBX_LIST pc=%06X first=%08X pos=%08X size=%08X source=%08X a0=%06X a2=%06X\\n",pc,d0,d1,d2,d3,a0,a2;g'
      input_breakpoints[#input_breakpoints + 1] =
        debugger:bpset(0xdd6a,
          string.format("(d0&ffff)>=20&&(d0&ffff)<=%X",
            ysprite_sequence_last_kind), action)
      print(string.format("SEQUENCE_TRACE_ARMED,DD6A,LOW_WORD_0020_TO_%04X",
        ysprite_sequence_last_kind))
    end
  end
  if debug_mode == "ysprite" and frames ==
      (ysprite_sequence_trace and ysprite_sequence_end or 967) then
    for _, watch in ipairs(watchpoints) do watch[1]:wpclear(watch[2]) end
    local debugger = manager.machine.devices[":subx"].debug
    for _, index in ipairs(input_breakpoints) do debugger:bpclear(index) end
    print(string.format("WATCH_CLEARED,ysprite,%d", frames))
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
  if source_output and frames >= 960 and frames <= sequence_end then
    if capture_profile == "full" or frames == source_override_frame then
      capture_source(frames, "ysprites", source_x_space, 0x180000, 0x10000)
    end
    if capture_profile == "full" or (bsprite_override and frames == bsprite_override_frame) then
      capture_source(frames, "bsprites", source_y_space, 0x188000, 0x1000)
    end
    if capture_profile == "full" then
      capture_source(frames, "palette", source_y_space, 0x190000, 0x4000)
    end
  end
  if source_override and frames == source_override_frame then
    local file = assert(io.open(source_override, "rb"))
    local bytes = assert(file:read("*a"))
    assert(file:close())
    assert(#bytes == 0x10000)
    for offset = override_start, override_start + override_size - 1 do
      source_x_space:write_u8(0x180000 + offset, bytes:byte(offset + 1))
    end
    print(string.format("SOURCE_OVERRIDE,%d,ysprites,%04X,%04X,%s",
      frames, override_start, override_size, source_override))
    capture_source(frames, "ysprites-after", source_x_space, 0x180000, 0x10000)
  end
  if bsprite_override and frames == bsprite_override_frame then
    local file = assert(io.open(bsprite_override, "rb"))
    local bytes = assert(file:read("*a"))
    assert(file:close())
    assert(#bytes == 16)
    for offset = 0, 15 do
      source_y_space:write_u8(0x188000 + bsprite_override_slot + offset,
        bytes:byte(offset + 1))
    end
    print(string.format("BSPRITE_OVERRIDE,%d,%03X,%s",
      frames, bsprite_override_slot, bsprite_override))
    capture_source(frames, "bsprites-after", source_y_space, 0x188000, 0x1000)
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
