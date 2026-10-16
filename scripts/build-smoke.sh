#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
mkdir -p build/smoke
m68k-elf-as -m68000 -o build/smoke/ip.o src/smoke/ip.S
m68k-elf-ld -Ttext=0 -e _start -o build/smoke/ip.elf build/smoke/ip.o
m68k-elf-objcopy -O binary build/smoke/ip.elf build/smoke/ip.img
m68k-elf-as -m68000 -o build/smoke/sp.o src/smoke/sp.S
m68k-elf-ld -Ttext=0 -e _start -o build/smoke/sp.elf build/smoke/sp.o
m68k-elf-objcopy -O binary build/smoke/sp.elf build/smoke/sp.img
python3 tools/make_smoke_cd.py build/smoke/ip.img build/smoke/sp.img build/smoke/smoke.iso build/smoke/smoke.cue
shasum -a 256 build/smoke/ip.img build/smoke/sp.img build/smoke/smoke.iso
