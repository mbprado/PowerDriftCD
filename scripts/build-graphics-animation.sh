#!/bin/sh
set -eu
if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
    echo "usage: sh scripts/build-graphics-animation.sh LOCAL_US_STARTUP_PREFIX asic|precomputed 60|30 [reverse]" >&2
    exit 2
fi
prefix=$1
strategy=$2
rate=$3
order=${4:-forward}
case "$strategy" in asic|precomputed) ;; *) echo "invalid strategy" >&2; exit 2 ;; esac
case "$rate" in 60|30) ;; *) echo "invalid rate" >&2; exit 2 ;; esac
case "$order" in forward|reverse) ;; *) echo "invalid order" >&2; exit 2 ;; esac
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
name=graphics-animation-$strategy-$rate
if [ "$order" = reverse ]; then name=$name-reverse; fi
mkdir -p "build/$name" build/graphics-asic build/graphics-asic-bench build/private
python3 tools/make_graphics_asic_fixture.py build/graphics-asic
python3 tools/make_graphics_asic_bench.py build/graphics-asic-bench
ip_options=--defsym=ANIMATE_TRACE=1
if [ "$order" = reverse ]; then ip_options="$ip_options --defsym=REVERSE_TRANSFER=1"; fi
if [ "$rate" = 30 ]; then ip_options="$ip_options --defsym=FRAME_DIV_2=1"; fi
if [ "$strategy" = precomputed ]; then
    ip_options="$ip_options --defsym=PRECOMPUTED=1"
    sp_source=src/experiments/graphics_precomputed_sp.S
    sp_options=
else
    sp_source=src/experiments/graphics_asic_bench_sp.S
    sp_options=--defsym=ANIMATE_TRACE=1
fi
# The option words above are fixed script literals, never user input.
m68k-elf-as -m68000 $ip_options -o "build/$name/ip.o" src/experiments/graphics_vdp_ip.S
m68k-elf-ld -Ttext=0 -e _start -o "build/$name/ip.elf" "build/$name/ip.o"
m68k-elf-objcopy -O binary "build/$name/ip.elf" "build/$name/ip.img"
m68k-elf-as -m68000 $sp_options -o "build/$name/sp.o" "$sp_source"
m68k-elf-ld -Ttext=0 -e _start -o "build/$name/sp.elf" "build/$name/sp.o"
m68k-elf-objcopy -O binary "build/$name/sp.elf" "build/$name/sp.img"
python3 tools/make_smoke_cd.py "build/$name/ip.img" "build/$name/sp.img" \
    "build/private/$name-us.iso" "build/private/$name-us.cue" \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track "build/private/$name-us-silence.bin"
shasum -a 256 "build/$name/ip.img" "build/$name/sp.img" "build/private/$name-us.iso"
