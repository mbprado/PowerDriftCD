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
    .ifdef ROAD_COMPARE
    moveq #0,%d0
    .endif
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
    .ifdef ROAD_COMPARE
    btst #3,%d7 /* comparison command bit: 0 full trace, 1 runtime trace */
    bne.s compare_runtime_data
    mulu.w #512,%d0
    lea road_traces(%pc),%a0
    bra.s compare_data_ready
compare_runtime_data:
    mulu.w #132,%d0
    lea road_compact(%pc),%a0
compare_data_ready:
    .else
    .ifdef RUNTIME_TRACE
    mulu.w #132,%d0 /* 4 camera bytes + 64 curve/ridge pairs */
    lea road_compact(%pc),%a0
    .else
    mulu.w #512,%d0 /* 64 scanlines, 8 trace bytes each */
    lea road_traces(%pc),%a0
    .endif
    .endif
    lea 0(%a0,%d0.w),%a0
    lea 0x0b0000,%a1
    .ifdef ROAD_COMPARE
    btst #3,%d7
    beq compare_copy_trace
    .endif
    .ifdef RUNTIME_TRACE
    move.w 0xff800c,0x098004
    movea.l %a0,%a2
    move.b (%a0)+,%d5
    ext.w %d5 /* signed bank: -2..2 */
    moveq #0,%d6
    move.b (%a0)+,%d6 /* horizon */
    addq.l #2,%a0 /* phase offset and padding remain at a2+2 */
    moveq #0,%d3 /* output scanline */
build_trace:
    move.w %d3,%d2
    sub.w %d6,%d2
    bpl.s depth_ready
    moveq #0,%d2
depth_ready:
    moveq #16,%d1
    cmpi.w #45,%d2
    blt.s test_middle
    moveq #4,%d1
    bra.s scale_ready
test_middle:
    cmpi.w #30,%d2
    blt.s test_near
    moveq #8,%d1
    bra.s scale_ready
test_near:
    cmpi.w #15,%d2
    blt.s scale_ready
    moveq #12,%d1
scale_ready:
    move.b (%a0)+,%d4
    ext.w %d4 /* signed curve sample */
    move.w %d3,%d0
    subi.w #32,%d0
    muls.w %d5,%d0
    asr.l #3,%d0 /* signed floor division by eight */
    add.w %d4,%d0
    addi.w #136,%d0
    lsl.w #3,%d0
    move.w %d1,%d4
    lsl.w #5,%d4
    sub.w %d4,%d0
    move.w %d0,(%a1)+ /* source X start */

    move.b (%a0)+,%d4
    ext.w %d4 /* signed ridge sample */
    move.w %d2,%d0
    mulu.w %d2,%d0
    divu.w #48,%d0
    sub.w %d0,%d4
    move.w %d2,%d0
    mulu.w #3,%d0
    add.w %d0,%d4
    addi.w #20,%d4
    moveq #0,%d0
    move.b 2(%a2),%d0
    add.w %d0,%d4
    lsl.w #3,%d4
    move.w %d5,%d0
    lsl.w #5,%d0
    sub.w %d0,%d4
    move.w %d4,(%a1)+ /* source Y start */
    move.w %d1,%d0
    lsl.w #8,%d0
    move.w %d0,(%a1)+ /* X step */
    move.w %d5,%d0
    lsl.w #8,%d0
    move.w %d0,(%a1)+ /* Y step */
    addq.w #1,%d3
    cmpi.w #64,%d3
    bne build_trace
    move.w 0xff800c,%d0
    sub.w 0x098004,%d0
    andi.w #0x0fff,%d0
    move.w %d0,0x098002 /* isolated trace preparation window */
    .ifdef ROAD_COMPARE
    bra trace_ready
compare_copy_trace:
    move.w 0xff800c,0x098004
    move.w #255,%d0
compare_copy_loop:
    move.w (%a0)+,(%a1)+
    dbf %d0,compare_copy_loop
    move.w 0xff800c,%d0
    sub.w 0x098004,%d0
    andi.w #0x0fff,%d0
    move.w %d0,0x098002
trace_ready:
    .endif
    .else
    move.w #255,%d0
copy_trace:
    move.w (%a0)+,(%a1)+
    dbf %d0,copy_trace
    .endif
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
    .ifdef ROAD_COMPARE
    .incbin "build/perspective-road/road-traces.bin"
road_compact:
    .incbin "build/perspective-road/road-compact.bin"
    .else
    .ifndef RUNTIME_TRACE
    .incbin "build/perspective-road/road-traces.bin"
    .else
road_compact:
    .incbin "build/perspective-road/road-compact.bin"
    .endif
    .endif
module_end:
