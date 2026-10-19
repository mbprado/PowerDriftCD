#!/bin/sh
set -eu
if [ "$#" -lt 1 ] || [ "$#" -gt 4 ]; then
    echo "usage: sh scripts/build-graphics-vdp.sh LOCAL_US_STARTUP_PREFIX [32|64] [prestage] [dma_only]" >&2
    exit 2
fi
prefix=$1
size=${2:-32}
schedule=${3:-inside_vblank}
transfer=${4:-alternating}
case "$size" in 32|64) ;; *) echo "size must be 32 or 64" >&2; exit 2 ;; esac
case "$schedule" in inside_vblank|prestage) ;; *) echo "invalid schedule" >&2; exit 2 ;; esac
case "$transfer" in alternating|dma_only) ;; *) echo "invalid transfer" >&2; exit 2 ;; esac
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
name=graphics-vdp
as_options=
if [ "$size" = 64 ]; then name=graphics-vdp-64; as_options=--defsym=SIZE_64=1; fi
if [ "$schedule" = prestage ]; then name=$name-prestage; as_options="$as_options --defsym=PRESTAGE_DMA=1"; fi
if [ "$transfer" = dma_only ]; then name=$name-dma-only; as_options="$as_options --defsym=DMA_ONLY=1"; fi
mkdir -p "build/$name" build/graphics-asic build/graphics-asic-bench build/private
python3 tools/make_graphics_asic_fixture.py build/graphics-asic
python3 tools/make_graphics_asic_bench.py build/graphics-asic-bench
m68k-elf-as -m68000 $as_options -o "build/$name/ip.o" src/experiments/graphics_vdp_ip.S
m68k-elf-ld -Ttext=0 -e _start -o "build/$name/ip.elf" "build/$name/ip.o"
m68k-elf-objcopy -O binary "build/$name/ip.elf" "build/$name/ip.img"
m68k-elf-as -m68000 -o "build/$name/sp.o" src/experiments/graphics_asic_bench_sp.S
m68k-elf-ld -Ttext=0 -e _start -o "build/$name/sp.elf" "build/$name/sp.o"
m68k-elf-objcopy -O binary "build/$name/sp.elf" "build/$name/sp.img"
python3 tools/make_smoke_cd.py "build/$name/ip.img" "build/$name/sp.img" \
    "build/private/$name-us.iso" "build/private/$name-us.cue" \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track "build/private/$name-us-silence.bin"
shasum -a 256 "build/$name/ip.img" "build/$name/sp.img" \
    "build/private/$name-us.iso"
