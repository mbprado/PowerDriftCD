#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: sh scripts/build-wordram.sh LOCAL_US_STARTUP_PREFIX" >&2
    exit 2
fi

prefix=$1
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p build/wordram build/private
python3 tools/make_smoke_font.py
m68k-elf-as -m68000 --defsym WORDRAM_TEST=1 -o build/wordram/ip.o src/smoke/ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/wordram/ip.elf build/wordram/ip.o
m68k-elf-objcopy -O binary build/wordram/ip.elf build/wordram/ip.img
m68k-elf-as -m68000 --defsym WORDRAM_TEST=1 -o build/wordram/sp.o src/smoke/sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/wordram/sp.elf build/wordram/sp.o
m68k-elf-objcopy -O binary build/wordram/sp.elf build/wordram/sp.img
python3 tools/make_smoke_cd.py build/wordram/ip.img build/wordram/sp.img \
    build/private/wordram-us.iso build/private/wordram-us.cue \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track build/private/wordram-us-silence.bin
shasum -a 256 build/wordram/ip.img build/wordram/sp.img \
    build/private/wordram-us.iso build/private/wordram-us.cue \
    build/private/wordram-us-silence.bin
