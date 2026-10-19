#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: sh scripts/build-wordram-paired.sh LOCAL_US_STARTUP_PREFIX [forward|reverse]" >&2
    exit 2
fi

prefix=$1
order=${2:-forward}
case "$order" in
    forward) name=wordram-paired ;;
    reverse) name=wordram-paired-reverse ;;
    *) echo "order must be forward or reverse" >&2; exit 2 ;;
esac
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p "build/$name" build/private
if [ "$order" = reverse ]; then
    m68k-elf-as -m68000 --defsym REVERSE_PHASES=1 -o "build/$name/ip.o" src/experiments/wordram_paired_ip.S
else
    m68k-elf-as -m68000 -o "build/$name/ip.o" src/experiments/wordram_paired_ip.S
fi
m68k-elf-ld -Ttext=0 -e _start -o "build/$name/ip.elf" "build/$name/ip.o"
m68k-elf-objcopy -O binary "build/$name/ip.elf" "build/$name/ip.img"
m68k-elf-as -m68000 -o "build/$name/sp.o" src/experiments/wordram_paired_sp.S
m68k-elf-ld -Ttext=0 -e _start -o "build/$name/sp.elf" "build/$name/sp.o"
m68k-elf-objcopy -O binary "build/$name/sp.elf" "build/$name/sp.img"
python3 tools/make_smoke_cd.py "build/$name/ip.img" "build/$name/sp.img" \
    "build/private/$name-us.iso" "build/private/$name-us.cue" \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track "build/private/$name-us-silence.bin"
shasum -a 256 "build/$name/ip.img" "build/$name/sp.img" \
    "build/private/$name-us.iso" "build/private/$name-us.cue" \
    "build/private/$name-us-silence.bin"
