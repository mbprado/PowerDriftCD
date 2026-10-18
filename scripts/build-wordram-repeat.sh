#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: sh scripts/build-wordram-repeat.sh LOCAL_US_STARTUP_PREFIX" >&2
    exit 2
fi

prefix=$1
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p build/wordram-repeat build/private
python3 tools/make_smoke_font.py
m68k-elf-as -m68000 --defsym WORDRAM_REPEAT_TEST=1 -o build/wordram-repeat/ip.o src/smoke/ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/wordram-repeat/ip.elf build/wordram-repeat/ip.o
m68k-elf-objcopy -O binary build/wordram-repeat/ip.elf build/wordram-repeat/ip.img
m68k-elf-as -m68000 --defsym WORDRAM_REPEAT_TEST=1 -o build/wordram-repeat/sp.o src/smoke/sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/wordram-repeat/sp.elf build/wordram-repeat/sp.o
m68k-elf-objcopy -O binary build/wordram-repeat/sp.elf build/wordram-repeat/sp.img
python3 tools/make_smoke_cd.py build/wordram-repeat/ip.img build/wordram-repeat/sp.img \
    build/private/wordram-repeat-us.iso build/private/wordram-repeat-us.cue \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track build/private/wordram-repeat-us-silence.bin
shasum -a 256 build/wordram-repeat/ip.img build/wordram-repeat/sp.img \
    build/private/wordram-repeat-us.iso build/private/wordram-repeat-us.cue \
    build/private/wordram-repeat-us-silence.bin
