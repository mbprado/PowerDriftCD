#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: sh scripts/build-handshake.sh LOCAL_US_STARTUP_PREFIX" >&2
    exit 2
fi

prefix=$1
cd "$(dirname "$0")/.."
if [ ! -f "$prefix" ]; then
    echo "local startup prefix not found: $prefix" >&2
    exit 2
fi
mkdir -p build/handshake build/private
python3 tools/make_smoke_font.py
m68k-elf-as -m68000 --defsym HANDSHAKE=1 -o build/handshake/ip.o src/smoke/ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/handshake/ip.elf build/handshake/ip.o
m68k-elf-objcopy -O binary build/handshake/ip.elf build/handshake/ip.img
m68k-elf-as -m68000 --defsym HANDSHAKE=1 -o build/handshake/sp.o src/smoke/sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/handshake/sp.elf build/handshake/sp.o
m68k-elf-objcopy -O binary build/handshake/sp.elf build/handshake/sp.img
python3 tools/make_smoke_cd.py build/handshake/ip.img build/handshake/sp.img \
    build/private/handshake-us.iso build/private/handshake-us.cue \
    --region U --startup-prefix "$prefix" \
    --silent-audio-track build/private/handshake-us-silence.bin
shasum -a 256 build/handshake/ip.img build/handshake/sp.img \
    build/private/handshake-us.iso build/private/handshake-us.cue \
    build/private/handshake-us-silence.bin
