/* Sub-CPU: original two-stamp road, per-scanline ASIC trace, stopwatch record. */
.section .text
.global _start
_start:
module_start:
    .ascii "MAIN       "
    .byte 0
    .word 0x0100
    .word 0
    .long 0
    .long module_end-module_start
    .long callbacks-module_start
    .long 0
callbacks:
    .word initialize-callbacks
    .word main_loop-callbacks
    .word interrupt-callbacks
    .word user_call-callbacks
    .word 0
initialize:
main_loop:
    rts
interrupt:
    movem.l %d0-%d7/%a0-%a2,-(%sp)
    move.w 0xff801e,%d7
    cmpi.w #0x574d,%d7
    beq mode_ready
    move.w %d7,%d0
    andi.w #0xf000,%d0
    cmpi.w #0x5000,%d0
    bne done
wait_sub:
    btst #0,0xff8003
    bne.s wait_sub

    lea road_stamps(%pc),%a0
    lea 0x080000,%a1
    move.w #191,%d0
copy_stamps:
    move.w (%a0)+,(%a1)+
    dbf %d0,copy_stamps
    lea 0x0a0000,%a1
    move.w #255,%d0
grass_map:
    move.w #2,(%a1)+
    dbf %d0,grass_map
    lea 0x0a0010,%a1 /* road occupies source-map column 8 */
    move.w #15,%d0
road_map:
    move.w #1,(%a1)
    adda.w #32,%a1
    dbf %d0,road_map

    move.w %d7,%d0
    lsr.w #4,%d0
    andi.w #0x00ff,%d0
    divu.w #24,%d0
    swap %d0 /* remainder: 0..23 */
    mulu.w #512,%d0 /* 64 scanlines, 8 trace bytes each */
    lea road_traces(%pc),%a0
    lea 0(%a0,%d0.w),%a0
    lea 0x0b0000,%a1
    move.w #255,%d0
copy_trace:
    move.w (%a0)+,(%a1)+
    dbf %d0,copy_trace
    lea 0x090000,%a1
    move.w #1023,%d0
clear_output:
    move.w #0xffff,(%a1)+
    dbf %d0,clear_output

    move.w #0,0xff8058
    move.w #0x8000,0xff805a
    move.w #7,0xff805c
    move.w #0x4000,0xff805e
    move.w #0,0xff8060
    move.w #64,0xff8062
    move.w #64,0xff8064
    move.w 0xff800c,%d2
    move.w #0xc000,0xff8066
    move.l #0x000fffff,%d0
poll_asic:
    btst #7,0xff8058
    beq.s asic_done
    subq.l #1,%d0
    bne.s poll_asic
    move.w #0xe002,0xff802e
    bra return_ram
asic_done:
    move.w 0xff800c,%d4
    sub.w %d2,%d4
    andi.w #0x0fff,%d4
    move.w %d4,0x098000
    move.w %d7,%d0
    eori.w #0x8000,%d0
    move.w %d0,0xff802e
return_ram:
    move.b #1,0xff8003
done:
    movem.l (%sp)+,%d0-%d7/%a0-%a2
    rts
mode_ready:
    move.b #1,0xff8003
    move.w #0x4d52,0xff802e
    bra.s done
user_call:
    rts
.even
road_stamps:
    .incbin "build/perspective-road/road-stamps.bin"
road_traces:
    .incbin "build/perspective-road/road-traces.bin"
module_end:
