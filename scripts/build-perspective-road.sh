#!/bin/sh
set -eu
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: sh scripts/build-perspective-road.sh LOCAL_US_STARTUP_PREFIX [precomputed|runtime|runtime-combined|compare|runtime-full|runtime-independent]" >&2
    exit 2
fi
prefix=$1
mode=${2:-precomputed}
if [ "$mode" != precomputed ] && [ "$mode" != runtime ] && [ "$mode" != runtime-combined ] && [ "$mode" != compare ] && [ "$mode" != runtime-full ] && [ "$mode" != runtime-independent ]; then
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
sp_source=src/experiments/perspective_road_sp.S
if [ "$mode" = runtime ] || [ "$mode" = runtime-combined ] || [ "$mode" = compare ] || [ "$mode" = runtime-full ] || [ "$mode" = runtime-independent ]; then
    runtime_ip=--defsym=ROAD_RUNTIME=1
    runtime_sp=--defsym=RUNTIME_TRACE=1
    image_name=perspective-road-runtime-us
    if [ "$mode" = runtime-combined ]; then
        runtime_ip='--defsym=ROAD_RUNTIME=1 --defsym=ROAD_RUNTIME_COMBINED=1'
        image_name=perspective-road-runtime-combined-us
    fi
    if [ "$mode" = compare ]; then
        runtime_ip='--defsym=ROAD_RUNTIME=1 --defsym=ROAD_RUNTIME_COMBINED=1 --defsym=ROAD_COMPARE=1'
        runtime_sp='--defsym=RUNTIME_TRACE=1 --defsym=ROAD_COMPARE=1'
        image_name=perspective-road-compare-us
    fi
    if [ "$mode" = runtime-full ]; then
        runtime_ip='--defsym=ROAD_RUNTIME=1 --defsym=ROAD_RUNTIME_COMBINED=1 --defsym=ROAD_FULL_CAMERA=1'
        runtime_sp=
        sp_source=src/experiments/perspective_road_full_camera_sp.S
        image_name=perspective-road-runtime-full-us
    fi
    if [ "$mode" = runtime-independent ]; then
        runtime_ip='--defsym=ROAD_RUNTIME=1 --defsym=ROAD_RUNTIME_COMBINED=1 --defsym=ROAD_INDEPENDENT=1'
        runtime_sp=
        sp_source=src/experiments/perspective_road_independent_sp.S
        image_name=perspective-road-runtime-independent-us
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
m68k-elf-as -m68000 $runtime_sp -o build/perspective-road/sp.o "$sp_source"
m68k-elf-ld -Ttext=0 -e _start -o build/perspective-road/sp.elf build/perspective-road/sp.o
m68k-elf-objcopy -O binary build/perspective-road/sp.elf build/perspective-road/sp.img
python3 tools/make_smoke_cd.py build/perspective-road/ip.img build/perspective-road/sp.img \
    "build/private/$image_name.iso" "build/private/$image_name.cue" \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track "build/private/$image_name-silence.bin"
shasum -a 256 build/perspective-road/ip.img build/perspective-road/sp.img \
    "build/private/$image_name.iso"
