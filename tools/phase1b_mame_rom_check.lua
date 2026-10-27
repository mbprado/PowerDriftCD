-- Read-only live address comparison for the privately assembled main-CPU ROM.
local cpu = assert(manager.machine.devices[":maincpu"])
local space = assert(cpu.spaces["program"])
local addresses = { 0x000000, 0x033B02, 0x033D1E, 0x034680,
                    0x03483C, 0x034AD8, 0x034C30 }
local done = false
emu.register_frame_done(function()
  if done then return end
  done = true
  for _, address in ipairs(addresses) do
    local parts = {}
    for offset = 0, 15 do
      parts[#parts + 1] = string.format("%02x", space:read_u8(address + offset))
    end
    print(string.format("MAIN_ROM_WINDOW,%06X,%s", address,
      table.concat(parts)))
  end
end, "frame")
