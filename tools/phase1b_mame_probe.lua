local frames = 0
local snapshot_dir = os.getenv("PDRIFT_SNAPSHOT_DIR")
print("PHASE1B_SCRIPT_LOADED")
local screen = manager.machine.screens[":screen"]
if screen then
  print(string.format("PHASE1B_SCREEN=%dx%d", screen.width, screen.height))
else
  print("PHASE1B_SCREEN_MISSING")
end
emu.register_frame_done(function()
  frames = frames + 1
  if frames % 60 == 0 then
    print(string.format("PHASE1B_FRAME=%d", frames))
  end
  if screen and snapshot_dir and (frames == 300 or frames == 600) then
    local path = string.format("%s/phase1b-frame%d.png", snapshot_dir, frames)
    local err = screen:snapshot(path)
    print(string.format("PHASE1B_SNAPSHOT=%s ERROR=%s", path, tostring(err)))
  end
end, "frame")
