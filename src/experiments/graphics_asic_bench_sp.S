/* Sub-CPU ASIC-only stopwatch window, excluding setup and Word RAM transfer. */
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
    rts
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
    move.w %d7,%d0
    andi.w #15,%d0
    cmpi.w #8,%d0
    bhi done
wait_sub:
    btst #0,0xff8003
    bne.s wait_sub

    lea stamp(%pc),%a0
    lea 0x080080,%a1
    move.w #63,%d0
copy_stamp:
    move.w (%a0)+,(%a1)+
    dbf %d0,copy_stamp
    lea 0x0a0000,%a1
    move.w #255,%d0
fill_map:
    move.w #1,(%a1)+
    dbf %d0,fill_map

    move.w %d7,%d0
    andi.w #15,%d0
    move.w %d0,%d6
    lsl.w #2,%d0
    lea case_table(%pc),%a2
    move.w 0(%a2,%d0.w),%d1
    lea 0(%a2,%d1.w),%a0
    move.w 2(%a2,%d0.w),%d5 /* pixel width and height */
    lea 0x0b0000,%a1
    move.w %d5,%d0
    lsl.w #2,%d0
    subq.w #1,%d0
copy_trace:
    move.w (%a0)+,(%a1)+
    dbf %d0,copy_trace
.ifdef ANIMATE_TRACE
    /* Move the source texture one pixel each frame, wrapping every 16. */
    move.w %d7,%d0
    lsr.w #4,%d0
    andi.w #15,%d0
    lsl.w #3,%d0 /* trace X start uses eighth-pixel units */
    lea 0x0b0000,%a1
    move.w %d5,%d1
    subq.w #1,%d1
animate_line:
    add.w %d0,(%a1)
    adda.w #8,%a1
    dbf %d1,animate_line
.endif
    lea 0x090000,%a1
    move.w %d5,%d0
    mulu.w %d5,%d0
    lsr.l #2,%d0
    subq.w #1,%d0
clear_output:
    move.w #0xffff,(%a1)+
    dbf %d0,clear_output

    move.w #0,0xff8058
    move.w #0x8000,0xff805a
    move.w %d5,%d0
    lsr.w #3,%d0
    subq.w #1,%d0
    move.w %d0,0xff805c
    move.w #0x4000,0xff805e
    move.w #0,0xff8060
    move.w %d5,0xff8062
    move.w %d5,0xff8064

    /* Timer-read control, then ASIC start-to-GRON-clear interval. */
    move.w 0xff800c,%d2
    move.w 0xff800c,%d3
    sub.w %d2,%d3
    andi.w #0x0fff,%d3
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
    move.w %d3,0x098002
    move.w %d2,0x098004
    move.w 0xff800c,%d0
    move.w %d0,0x098006
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
case_table:
    .word trace_16_scale-case_table,16
    .word trace_16_rotate-case_table,16
    .word trace_16_combined-case_table,16
    .word trace_32_scale-case_table,32
    .word trace_32_rotate-case_table,32
    .word trace_32_combined-case_table,32
    .word trace_64_scale-case_table,64
    .word trace_64_rotate-case_table,64
    .word trace_64_combined-case_table,64
stamp:
    .incbin "build/graphics-asic/stamp.bin"
trace_16_scale:
    .incbin "build/graphics-asic-bench/trace-16-scale.bin"
trace_16_rotate:
    .incbin "build/graphics-asic-bench/trace-16-rotate.bin"
trace_16_combined:
    .incbin "build/graphics-asic-bench/trace-16-combined.bin"
trace_32_scale:
    .incbin "build/graphics-asic-bench/trace-32-scale.bin"
trace_32_rotate:
    .incbin "build/graphics-asic-bench/trace-32-rotate.bin"
trace_32_combined:
    .incbin "build/graphics-asic-bench/trace-32-combined.bin"
trace_64_scale:
    .incbin "build/graphics-asic-bench/trace-64-scale.bin"
trace_64_rotate:
    .incbin "build/graphics-asic-bench/trace-64-rotate.bin"
trace_64_combined:
    .incbin "build/graphics-asic-bench/trace-64-combined.bin"
module_end:
