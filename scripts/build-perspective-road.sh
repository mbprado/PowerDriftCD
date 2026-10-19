#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
    echo "usage: sh scripts/build-perspective-road.sh LOCAL_US_STARTUP_PREFIX" >&2
    exit 2
fi
prefix=$1
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p build/perspective-road build/graphics-asic-bench build/private
python3 tools/make_perspective_road.py build/perspective-road
python3 tools/make_graphics_asic_bench.py build/graphics-asic-bench
m68k-elf-as -m68000 --defsym=SIZE_64=1 --defsym=FRAME_DIV_2=1 \
    --defsym=PRESTAGE_DMA=1 --defsym=DMA_ONLY=1 --defsym=ROAD_TRACE=1 \
    -o build/perspective-road/ip.o src/experiments/graphics_vdp_ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/perspective-road/ip.elf build/perspective-road/ip.o
m68k-elf-objcopy -O binary build/perspective-road/ip.elf build/perspective-road/ip.img
m68k-elf-as -m68000 -o build/perspective-road/sp.o src/experiments/perspective_road_sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/perspective-road/sp.elf build/perspective-road/sp.o
m68k-elf-objcopy -O binary build/perspective-road/sp.elf build/perspective-road/sp.img
python3 tools/make_smoke_cd.py build/perspective-road/ip.img build/perspective-road/sp.img \
    build/private/perspective-road-us.iso build/private/perspective-road-us.cue \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track build/private/perspective-road-us-silence.bin
shasum -a 256 build/perspective-road/ip.img build/perspective-road/sp.img \
    build/private/perspective-road-us.iso
