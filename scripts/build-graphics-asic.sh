#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
    echo "usage: sh scripts/build-graphics-asic.sh LOCAL_US_STARTUP_PREFIX" >&2
    exit 2
fi
prefix=$1
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p build/graphics-asic build/private
python3 tools/make_graphics_asic_fixture.py build/graphics-asic
m68k-elf-as -m68000 -o build/graphics-asic/ip.o src/experiments/graphics_asic_ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/graphics-asic/ip.elf build/graphics-asic/ip.o
m68k-elf-objcopy -O binary build/graphics-asic/ip.elf build/graphics-asic/ip.img
m68k-elf-as -m68000 -o build/graphics-asic/sp.o src/experiments/graphics_asic_sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/graphics-asic/sp.elf build/graphics-asic/sp.o
m68k-elf-objcopy -O binary build/graphics-asic/sp.elf build/graphics-asic/sp.img
python3 tools/make_smoke_cd.py build/graphics-asic/ip.img build/graphics-asic/sp.img \
    build/private/graphics-asic-us.iso build/private/graphics-asic-us.cue \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track build/private/graphics-asic-us-silence.bin
shasum -a 256 build/graphics-asic/ip.img build/graphics-asic/sp.img \
    build/private/graphics-asic-us.iso
