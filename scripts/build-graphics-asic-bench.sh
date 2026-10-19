#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
    echo "usage: sh scripts/build-graphics-asic-bench.sh LOCAL_US_STARTUP_PREFIX" >&2
    exit 2
fi
prefix=$1
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p build/graphics-asic-bench build/private
python3 tools/make_graphics_asic_fixture.py build/graphics-asic
python3 tools/make_graphics_asic_bench.py build/graphics-asic-bench
m68k-elf-as -m68000 -o build/graphics-asic-bench/ip.o src/experiments/graphics_asic_bench_ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/graphics-asic-bench/ip.elf build/graphics-asic-bench/ip.o
m68k-elf-objcopy -O binary build/graphics-asic-bench/ip.elf build/graphics-asic-bench/ip.img
m68k-elf-as -m68000 -o build/graphics-asic-bench/sp.o src/experiments/graphics_asic_bench_sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/graphics-asic-bench/sp.elf build/graphics-asic-bench/sp.o
m68k-elf-objcopy -O binary build/graphics-asic-bench/sp.elf build/graphics-asic-bench/sp.img
python3 tools/make_smoke_cd.py build/graphics-asic-bench/ip.img build/graphics-asic-bench/sp.img \
    build/private/graphics-asic-bench-us.iso build/private/graphics-asic-bench-us.cue \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track build/private/graphics-asic-bench-us-silence.bin
shasum -a 256 build/graphics-asic-bench/ip.img build/graphics-asic-bench/sp.img \
    build/private/graphics-asic-bench-us.iso
