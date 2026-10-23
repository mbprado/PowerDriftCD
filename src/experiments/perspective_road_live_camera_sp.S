/* Sub-CPU: build ASIC traces from five main-CPU communication words. */
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
    movem.l %d0-%d7/%a0-%a4,-(%sp)
    move.w 0xff801e,%d7
    cmpi.w #0x574d,%d7
    beq mode_ready
    moveq #0,%d0
    move.w %d7,%d0
    andi.w #0xf000,%d0
    cmpi.w #0x5000,%d0
    bne done
wait_sub:
    btst #0,0xff8003
    bne.s wait_sub

    lea road_stamps(%pc),%a0
    lea 0x080000,%a1
 .ifdef ROAD_WIDE_GEOMETRY
  .ifdef ROAD_WIDE_MOTION
    move.w #1087,%d0
  .else
    move.w #447,%d0
  .endif
 .else
    move.w #191,%d0
 .endif
copy_stamps:
    move.w (%a0)+,(%a1)+
    dbf %d0,copy_stamps
    lea 0x0a0000,%a1
    move.w #255,%d0
grass_map:
 .ifdef ROAD_WIDE_GEOMETRY
  .ifdef ROAD_WIDE_MOTION
    move.w #16,(%a1)+
  .else
    move.w #6,(%a1)+
  .endif
 .else
    move.w #2,(%a1)+
 .endif
    dbf %d0,grass_map
 .ifdef ROAD_WIDE_GEOMETRY
  .ifdef ROAD_WIDE_MOTION
    lea 0x0a000c,%a1 /* five road columns, three width variants */
    move.w #15,%d6
    moveq #1,%d4
motion_road_map:
    move.w %d4,%d0
    move.w %d0,(%a1)+
    addq.w #1,%d0
    move.w %d0,(%a1)+
    addq.w #1,%d0
    move.w %d0,(%a1)+
    addq.w #1,%d0
    move.w %d0,(%a1)+
    addq.w #1,%d0
    move.w %d0,(%a1)
    adda.w #24,%a1
    addq.w #5,%d4
    cmpi.w #16,%d4
    blt.s motion_map_width_ready
    moveq #1,%d4
motion_map_width_ready:
    dbf %d6,motion_road_map
  .else
    lea 0x0a000c,%a1 /* five road stamps occupy columns 6..10 */
    move.w #15,%d0
wide_road_map:
    move.w #1,(%a1)+
    move.w #2,(%a1)+
    move.w #3,(%a1)+
    move.w #4,(%a1)+
    move.w #5,(%a1)
    adda.w #24,%a1
    dbf %d0,wide_road_map
  .endif
 .else
    lea 0x0a0010,%a1 /* road occupies source-map column 8 */
    move.w #15,%d0
road_map:
    move.w #1,(%a1)
    adda.w #32,%a1
    dbf %d0,road_map
 .endif

    move.w 0xff800c,0x098004
    move.w 0xff8018,0x098006 /* texture offset */
    move.w 0xff8014,%d5 /* signed bank */
    move.w 0xff8016,%d6 /* horizon */
    lea road_curve_sine(%pc),%a0
    move.w 0xff8010,%d0 /* curve phase */
    adda.w %d0,%a0 /* independent curve phase, then one entry per scanline */
    lea road_curve_sine_end(%pc),%a3
    lea road_ridge_sine(%pc),%a2
    move.w 0xff8012,%d0 /* ridge phase */
    adda.w %d0,%a2 /* independent ridge phase, then three per scanline */
    lea road_ridge_sine_end(%pc),%a4
    lea 0x0b0000,%a1
    moveq #0,%d3 /* output scanline */
build_trace:
    move.w %d3,%d2
    sub.w %d6,%d2
    bpl.s depth_ready
    moveq #0,%d2
depth_ready:
.ifdef ROAD_WIDE
 .ifdef ROAD_WIDE_GEOMETRY
    moveq #10,%d1
 .else
    moveq #12,%d1
 .endif
.else
    moveq #16,%d1
.endif
    cmpi.w #45,%d2
    blt.s test_middle
    moveq #4,%d1
    bra.s scale_ready
test_middle:
    cmpi.w #30,%d2
    blt.s test_near
.ifdef ROAD_WIDE
 .ifdef ROAD_WIDE_GEOMETRY
    moveq #5,%d1
 .else
    moveq #6,%d1
 .endif
.else
    moveq #8,%d1
.endif
    bra.s scale_ready
test_near:
    cmpi.w #15,%d2
    blt.s scale_ready
.ifdef ROAD_WIDE
 .ifdef ROAD_WIDE_GEOMETRY
    moveq #5,%d1
 .else
    moveq #8,%d1
 .endif
.else
    moveq #12,%d1
.endif
scale_ready:
    move.b (%a0)+,%d4
    ext.w %d4 /* signed curve sample */
    cmpa.l %a3,%a0
    bne.s curve_index_ready
    lea road_curve_sine(%pc),%a0
curve_index_ready:
    move.w %d3,%d0
    subi.w #32,%d0
    muls.w %d5,%d0
    asr.l #3,%d0 /* signed floor division by eight */
    add.w %d4,%d0
    addi.w #136,%d0
    lsl.w #3,%d0
    move.w %d1,%d4
.ifdef ROAD_WIDE
    lsl.w #6,%d4
.else
    lsl.w #5,%d4
.endif
    sub.w %d4,%d0
    move.w %d0,(%a1)+ /* source X start */

    move.b (%a2),%d4
    adda.w #3,%a2
    cmpa.l %a4,%a2
    blt.s ridge_index_ready
    suba.w #192,%a2
ridge_index_ready:
    ext.w %d4 /* signed ridge sample */
    move.w %d2,%d0
    mulu.w %d2,%d0
    divu.w #48,%d0
    sub.w %d0,%d4
    move.w %d2,%d0
    mulu.w #3,%d0
    add.w %d0,%d4
.ifdef ROAD_WIDE
    addi.w #28,%d4
.else
    addi.w #20,%d4
.endif
    move.w 0x098006,%d0
    add.w %d0,%d4
    lsl.w #3,%d4
    move.w %d5,%d0
.ifdef ROAD_WIDE
    lsl.w #6,%d0
.else
    lsl.w #5,%d0
.endif
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
    lea 0x090000,%a1
.ifdef ROAD_WIDE
    move.w #2047,%d0
.else
    move.w #1023,%d0
.endif
clear_output:
    move.w #0xffff,(%a1)+
    dbf %d0,clear_output

    move.w #0,0xff8058
    move.w #0x8000,0xff805a
    move.w #7,0xff805c
    move.w #0x4000,0xff805e
    move.w #0,0xff8060
.ifdef ROAD_WIDE
    move.w #128,0xff8062
.else
    move.w #64,0xff8062
.endif
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
    movem.l (%sp)+,%d0-%d7/%a0-%a4
    rts
mode_ready:
    move.b #1,0xff8003
    move.w #0x4d52,0xff802e
    bra.s done
user_call:
    rts
.even
road_stamps:
 .ifdef ROAD_WIDE_GEOMETRY
  .ifdef ROAD_WIDE_MOTION
    .incbin "build/perspective-road/road-wide-motion-stamps.bin"
  .else
    .incbin "build/perspective-road/road-wide-geometry-stamps.bin"
  .endif
 .else
    .incbin "build/perspective-road/road-stamps.bin"
 .endif
road_curve_sine:
    .incbin "build/perspective-road/road-curve-sine.bin"
road_curve_sine_end:
road_ridge_sine:
    .incbin "build/perspective-road/road-ridge-sine.bin"
road_ridge_sine_end:
module_end:
