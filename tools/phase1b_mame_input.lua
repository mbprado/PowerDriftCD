local ports = manager.machine.ioport.ports
local coin = assert(ports[":GENERAL"].fields["Coin 1"])
local start = assert(ports[":GENERAL"].fields["1 Player Start"])
local pedal = assert(ports[":ADC.4"].fields["P1 Pedal 1"])
local steering = assert(ports[":ADC.5"].fields["Paddle"])
local screen = assert(manager.machine.screens[":screen"])
local output = assert(os.getenv("PDRIFT_SNAPSHOT_DIR"))
local ram_output = os.getenv("PDRIFT_RAM_DIR")
local ram_space = ram_output and assert(manager.machine.devices[":maincpu"].spaces["program"])
local steer_pulse = tonumber(os.getenv("PDRIFT_STEER_PULSE") or "")
assert(not steer_pulse or (steer_pulse >= 32 and steer_pulse <= 224))
local frames = 0
local captures = { [300] = true, [600] = true, [900] = true,
                   [1020] = true, [1080] = true, [1140] = true,
                   [1200] = true, [1500] = true, [1800] = true }
local ram_captures = { [900] = true, [960] = true, [1020] = true,
                       [1080] = true, [1140] = true, [1200] = true }
local ram_windows = { main_low = 0x1f0000, main_high = 0x1fc000,
                      shared = 0x0c0000 }
local ram_size = 0x4000
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
coin:set_value(0)
start:set_value(0)
pedal:set_value(0)
steering:set_value(128)
print("INPUT_SCHEDULE=coin60-64,start130-134,pedal240+,steer128")
print("STEER_PULSE=" .. tostring(steer_pulse))
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
  if steer_pulse and frames == 1080 then
    steering:set_value(128)
    print("INPUT,1080,steer-128")
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
end, "frame")
