-- Read-only table-writer and upstream state-word probes for the arcade main CPU.
local mode = assert(os.getenv("PDRIFT_UPSTREAM_MODE"))
assert(mode == "table_boot" or mode == "state_inputs" or
       mode == "state_targets" or mode == "state88_inputs" or
       mode == "state88_targets" or mode == "source_writes" or
       mode == "state86_inputs" or mode == "state86_targets" or
       mode == "state86_path" or mode == "state8a_writes" or
       mode == "state8a_source" or mode == "state8a_inputs" or
       mode == "state8a_targets" or mode == "state8a_chain_order" or
       mode == "state8a_chain_inputs" or mode == "state8a_chain_targets" or
       mode == "state7c_dev" or mode == "state7c_inputs" or
       mode == "state7c_targets" or mode == "state7c_carry_inputs" or
       mode == "state7c_carry_targets" or mode == "state24_writes" or
       mode == "state24_inputs" or mode == "state24_targets" or
       mode == "state24_order" or mode == "state24_source_dev" or
       mode == "state24_source_inputs" or mode == "state24_source_targets" or
       mode == "state24_fraction_inputs" or
       mode == "state24_forward_inputs" or mode == "state24_forward_targets" or
       mode == "state24_forward_order")
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
    elseif mode == "state86_inputs" then
      breakpoint = debugger:bpset(0x34d44, "a5==c0840",
        'printf "STATE86_INPUT pc=%06X a5=%06X word8a=%04X word24=%04X word80=%04X old86=%04X flag91=%02X\\n",pc,a5,w@(a5+8a),w@(a5+24),w@(a5+80),w@(a5+86),b@(a5+91);g')
    elseif mode == "state86_targets" then
      breakpoint = debugger:bpset(0x34da4, "a5==c0840",
        'printf "STATE86_TARGET pc=%06X a5=%06X new86=%04X\\n",pc,a5,w@(a5+86);g')
    elseif mode == "state86_path" then
      for _, pc in ipairs({ 0x34d00, 0x34d04, 0x34d22, 0x34d44,
                            0x34d56, 0x34da0, 0x34da4 }) do
        source_watchpoints[#source_watchpoints + 1] =
          debugger:bpset(pc, "a5==c0840",
            'printf "STATE86_PATH pc=%06X\\n",pc;g')
      end
    elseif mode == "state8a_inputs" then
      breakpoint = debugger:bpset(0x374d0, "1",
        'printf "STATE8A_INPUT pc=%06X a5=%06X raw=%02X old16=%04X old18=%04X oldglobal=%04X\\n",pc,a5,b@cff27,w@(a5+16),w@(a5+18),w@ce0ce;g')
    elseif mode == "state8a_targets" then
      breakpoint = debugger:bpset(0x33922, "a0==c0840",
        'printf "STATE8A_TARGET pc=%06X a0=%06X new8a=%04X\\n",pc,a0,w@(a0+8a);g')
    elseif mode == "state8a_chain_order" then
      for _, pc in ipairs({ 0x374d0, 0x33922, 0x34d44, 0x34da4,
                            0x34dda, 0x34e0a }) do
        local condition = pc == 0x374d0 and "1" or
                          pc == 0x33922 and "a0==c0840" or "a5==c0840"
        source_watchpoints[#source_watchpoints + 1] =
          debugger:bpset(pc, condition,
            'printf "STATE8A_CHAIN_PC pc=%06X\\n",pc;g')
      end
    elseif mode == "state8a_chain_inputs" then
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x374d0, "1",
        'printf "CHAIN_INIT pc=%06X raw=%02X old86=%04X old88=%04X old7a=%04X\\n",pc,b@cff27,w@c08c6,w@c08c8,w@c08ba;g')
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x34d44, "a5==c0840",
        'printf "CHAIN_BRANCH pc=%06X word24=%04X word80=%04X flag91=%02X\\n",pc,w@(a5+24),w@(a5+80),b@(a5+91);g')
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x34dda, "a5==c0840",
        'printf "CHAIN_EXOGENOUS pc=%06X word7c=%04X\\n",pc,w@(a5+7c);g')
    elseif mode == "state8a_chain_targets" then
      breakpoint = debugger:bpset(0x34e0a, "a5==c0840",
        'printf "CHAIN_TARGET pc=%06X word86=%04X word88=%04X word7a=%04X\\n",pc,w@(a5+86),w@(a5+88),w@(a5+7a);g')
    elseif mode == "state7c_dev" or mode == "state7c_inputs" then
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x34e24, "a5==c0840",
        'printf "STATE7C_INPUT pc=%06X a5=%06X word86=%04X word7a=%04X word24=%04X word8a=%04X old7c=%04X flag69=%02X\\n",pc,a5,w@(a5+86),w@(a5+7a),w@(a5+24),w@(a5+8a),w@(a5+7c),b@(a5+69);g')
      if mode == "state7c_dev" then
        source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x34e5a, "a5==c0840",
          'printf "STATE7C_INTERMEDIATE pc=%06X d0=%08X\\n",pc,d0;g')
        source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x34ef4, "a5==c0840",
          'printf "STATE7C_DEV_TARGET pc=%06X new7c=%04X\\n",pc,w@(a5+7c);g')
      end
    elseif mode == "state7c_targets" then
      breakpoint = debugger:bpset(0x34ef4, "a5==c0840",
        'printf "STATE7C_TARGET pc=%06X new7c=%04X\\n",pc,w@(a5+7c);g')
    elseif mode == "state7c_carry_inputs" then
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x34dda, "a5==c0840",
        'printf "CARRY_A pc=%06X sign88=%04X old7a=%04X old7c=%04X\\n",pc,w@(a5+88),w@(a5+7a),w@(a5+7c);g')
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x34e24, "a5==c0840",
        'printf "CARRY_B pc=%06X word86=%04X word24=%04X word8a=%04X flag69=%02X\\n",pc,w@(a5+86),w@(a5+24),w@(a5+8a),b@(a5+69);g')
    elseif mode == "state7c_carry_targets" then
      breakpoint = debugger:bpset(0x34ef4, "a5==c0840",
        'printf "CARRY_TARGET pc=%06X new7a=%04X new7c=%04X\\n",pc,w@(a5+7a),w@(a5+7c);g')
    elseif mode == "state24_inputs" then
      breakpoint = debugger:bpset(0x34478, "a5==c0840",
        'printf "STATE24_INPUT pc=%06X a5=%06X desired=%04X limit=%04X oldglobal=%04X\\n",pc,a5,d0,d1,w@cea12;g')
    elseif mode == "state24_targets" then
      breakpoint = debugger:bpset(0x344a0, "a5==c0840",
        'printf "STATE24_TARGET pc=%06X a5=%06X new24=%04X\\n",pc,a5,w@(a5+24);g')
    elseif mode == "state24_order" then
      for _, pc in ipairs({ 0x344a0, 0x34d44, 0x34e24 }) do
        source_watchpoints[#source_watchpoints + 1] =
          debugger:bpset(pc, "a5==c0840",
            'printf "STATE24_PC pc=%06X\\n",pc;g')
      end
    elseif mode == "state24_source_dev" then
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x343c4, "a5==c0840",
        'printf "STATE24_SOURCE pc=%06X flag26=%02X flag54=%02X flag55=%02X flag47=%02X word80=%04X word8c=%04X flag69=%02X flag5e=%02X word8e=%04X oldglobal=%04X\\n",pc,b@cea26,b@(a5+54),b@(a5+55),b@(a5+47),w@(a5+80),w@(a5+8c),b@(a5+69),b@(a5+5e),w@(a5+8e),w@cea12;g')
      for _, pc in ipairs({ 0x343f4, 0x34418, 0x34424, 0x3443a,
                            0x34448, 0x34454, 0x34474, 0x34478 }) do
        source_watchpoints[#source_watchpoints + 1] =
          debugger:bpset(pc, "a5==c0840",
            'printf "STATE24_SOURCE_PC pc=%06X\\n",pc;g')
      end
    elseif mode == "state24_source_inputs" then
      breakpoint = debugger:bpset(0x343c4, "a5==c0840",
        'printf "STATE24_SOURCE pc=%06X flag26=%02X flag54=%02X flag55=%02X flag47=%02X word80=%04X word8c=%04X flag69=%02X flag5e=%02X word8e=%04X oldglobal=%04X\\n",pc,b@cea26,b@(a5+54),b@(a5+55),b@(a5+47),w@(a5+80),w@(a5+8c),b@(a5+69),b@(a5+5e),w@(a5+8e),w@cea12;g')
    elseif mode == "state24_fraction_inputs" then
      breakpoint = debugger:bpset(0x343c4, "a5==c0840",
        'printf "STATE24_SOURCE pc=%06X flag26=%02X flag54=%02X flag55=%02X flag47=%02X word80=%04X word8c=%04X flag69=%02X flag5e=%02X word8e=%04X oldglobal=%04X oldfraction=%08X oldphase=%04X\\n",pc,b@cea26,b@(a5+54),b@(a5+55),b@(a5+47),w@(a5+80),w@(a5+8c),b@(a5+69),b@(a5+5e),w@(a5+8e),w@cea12,d@cea14,w@cea00;g')
    elseif mode == "state24_source_targets" then
      breakpoint = debugger:bpset(0x34478, "a5==c0840",
        'printf "STATE24_SOURCE_TARGET pc=%06X desired=%04X limit=%04X\\n",pc,d0,d1;g')
    elseif mode == "state24_forward_inputs" then
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x374d0, "1",
        'printf "FORWARD_INIT pc=%06X old86=%04X old88=%04X old7a=%04X old7c=%04X\\n",pc,w@c08c6,w@c08c8,w@c08ba,w@c08bc;g')
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x34d44, "a5==c0840",
        'printf "FORWARD_BRANCH pc=%06X word80=%04X flag91=%02X\\n",pc,w@(a5+80),b@(a5+91);g')
      source_watchpoints[#source_watchpoints + 1] = debugger:bpset(0x34e24, "a5==c0840",
        'printf "FORWARD_FLAG pc=%06X flag69=%02X\\n",pc,b@(a5+69);g')
    elseif mode == "state24_forward_targets" then
      breakpoint = debugger:bpset(0x34ef4, "a5==c0840",
        'printf "FORWARD_TARGET pc=%06X word86=%04X word88=%04X word7a=%04X word7c=%04X\\n",pc,w@(a5+86),w@(a5+88),w@(a5+7a),w@(a5+7c);g')
    elseif mode == "state24_forward_order" then
      for _, pc in ipairs({ 0x374d0, 0x343c4, 0x344a0, 0x33922,
                            0x34d44, 0x34da4, 0x34dda, 0x34e24, 0x34ef4 }) do
        local condition = pc == 0x374d0 and "1" or
                          pc == 0x33922 and "a0==c0840" or "a5==c0840"
        source_watchpoints[#source_watchpoints + 1] =
          debugger:bpset(pc, condition,
            'printf "FORWARD_PC pc=%06X\\n",pc;g')
      end
    else
      local addresses = mode == "state24_writes" and { 0x0c0864 } or
                        mode == "state8a_writes" and { 0x0c08ca } or
                        mode == "state8a_source" and { 0x0ce0ce } or
                        { 0x0c08ba, 0x0c08bc, 0x0c08c8 }
      for _, address in ipairs(addresses) do
        source_watchpoints[#source_watchpoints + 1] =
          debugger:wpset(space, "w", address, 2, "1",
            mode == "state24_writes" and
              'printf "STATE24_WRITE pc=%06X addr=%06X data=%08X\\n",pc,wpaddr,wpdata;g' or
            (mode == "state8a_writes" or mode == "state8a_source") and
              'printf "STATE8A_WRITE pc=%06X addr=%06X data=%08X\\n",pc,wpaddr,wpdata;g' or
              'printf "STATE_SOURCE_WRITE pc=%06X addr=%06X data=%08X\\n",pc,wpaddr,wpdata;g')
      end
    end
    print(string.format("UPSTREAM_ARMED,%s,960,pulse=%d", mode, pulse))
  end
  if frames == 1000 then
    if breakpoint then debugger:bpclear(breakpoint) end
    for _, index in ipairs(source_watchpoints) do
      if mode == "state86_path" or mode == "state8a_chain_order" or
         mode == "state8a_chain_inputs" or mode == "state7c_inputs" or
         mode == "state7c_dev" or mode == "state7c_carry_inputs" or
         mode == "state24_order" or mode == "state24_source_dev" or
         mode == "state24_forward_inputs" or
         mode == "state24_forward_order" then debugger:bpclear(index)
      else debugger:wpclear(index) end
    end
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
