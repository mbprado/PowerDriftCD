#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: sh scripts/build-wordram-timer.sh LOCAL_US_STARTUP_PREFIX" >&2
    exit 2
fi

prefix=$1
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p build/wordram-timer build/private
python3 tools/make_smoke_font.py
m68k-elf-as -m68000 --defsym WORDRAM_REPEAT_TEST=1 --defsym WORDRAM_TIMER_TEST=1 \
    -o build/wordram-timer/ip.o src/smoke/ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/wordram-timer/ip.elf build/wordram-timer/ip.o
m68k-elf-objcopy -O binary build/wordram-timer/ip.elf build/wordram-timer/ip.img
m68k-elf-as -m68000 --defsym WORDRAM_REPEAT_TEST=1 --defsym WORDRAM_TIMER_TEST=1 \
    -o build/wordram-timer/sp.o src/smoke/sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/wordram-timer/sp.elf build/wordram-timer/sp.o
m68k-elf-objcopy -O binary build/wordram-timer/sp.elf build/wordram-timer/sp.img
python3 tools/make_smoke_cd.py build/wordram-timer/ip.img build/wordram-timer/sp.img \
    build/private/wordram-timer-us.iso build/private/wordram-timer-us.cue \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track build/private/wordram-timer-us-silence.bin
shasum -a 256 build/wordram-timer/ip.img build/wordram-timer/sp.img \
    build/private/wordram-timer-us.iso build/private/wordram-timer-us.cue \
    build/private/wordram-timer-us-silence.bin
