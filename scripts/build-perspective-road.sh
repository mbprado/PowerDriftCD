#!/bin/sh
set -eu
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: sh scripts/build-perspective-road.sh LOCAL_US_STARTUP_PREFIX [precomputed|runtime|runtime-combined]" >&2
    exit 2
fi
prefix=$1
mode=${2:-precomputed}
if [ "$mode" != precomputed ] && [ "$mode" != runtime ] && [ "$mode" != runtime-combined ]; then
    echo "unknown trace mode: $mode" >&2
    exit 2
fi
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p build/perspective-road build/graphics-asic-bench build/private
python3 tools/make_perspective_road.py build/perspective-road
python3 tools/make_graphics_asic_bench.py build/graphics-asic-bench
if [ "$mode" = runtime ] || [ "$mode" = runtime-combined ]; then
    runtime_ip=--defsym=ROAD_RUNTIME=1
    runtime_sp=--defsym=RUNTIME_TRACE=1
    image_name=perspective-road-runtime-us
    if [ "$mode" = runtime-combined ]; then
        runtime_ip='--defsym=ROAD_RUNTIME=1 --defsym=ROAD_RUNTIME_COMBINED=1'
        image_name=perspective-road-runtime-combined-us
    fi
else
    runtime_ip=
    runtime_sp=
    image_name=perspective-road-us
fi
m68k-elf-as -m68000 --defsym=SIZE_64=1 --defsym=FRAME_DIV_2=1 \
    --defsym=PRESTAGE_DMA=1 --defsym=DMA_ONLY=1 --defsym=ROAD_TRACE=1 \
    $runtime_ip \
    -o build/perspective-road/ip.o src/experiments/graphics_vdp_ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/perspective-road/ip.elf build/perspective-road/ip.o
m68k-elf-objcopy -O binary build/perspective-road/ip.elf build/perspective-road/ip.img
m68k-elf-as -m68000 $runtime_sp -o build/perspective-road/sp.o src/experiments/perspective_road_sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/perspective-road/sp.elf build/perspective-road/sp.o
m68k-elf-objcopy -O binary build/perspective-road/sp.elf build/perspective-road/sp.img
python3 tools/make_smoke_cd.py build/perspective-road/ip.img build/perspective-road/sp.img \
    "build/private/$image_name.iso" "build/private/$image_name.cue" \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track "build/private/$image_name-silence.bin"
shasum -a 256 build/perspective-road/ip.img build/perspective-road/sp.img \
    "build/private/$image_name.iso"
