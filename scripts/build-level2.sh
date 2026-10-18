#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: sh scripts/build-level2.sh LOCAL_US_STARTUP_PREFIX" >&2
    exit 2
fi

prefix=$1
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p build/level2 build/private
python3 tools/make_smoke_font.py
m68k-elf-as -m68000 --defsym LEVEL2_TEST=1 -o build/level2/ip.o src/smoke/ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/level2/ip.elf build/level2/ip.o
m68k-elf-objcopy -O binary build/level2/ip.elf build/level2/ip.img
m68k-elf-as -m68000 --defsym LEVEL2_TEST=1 -o build/level2/sp.o src/smoke/sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/level2/sp.elf build/level2/sp.o
m68k-elf-objcopy -O binary build/level2/sp.elf build/level2/sp.img
python3 tools/make_smoke_cd.py build/level2/ip.img build/level2/sp.img \
    build/private/level2-us.iso build/private/level2-us.cue \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track build/private/level2-us-silence.bin
shasum -a 256 build/level2/ip.img build/level2/sp.img \
    build/private/level2-us.iso build/private/level2-us.cue \
    build/private/level2-us-silence.bin
