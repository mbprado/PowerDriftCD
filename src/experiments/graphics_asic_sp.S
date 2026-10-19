/* Original Sega CD ASIC fixture. Source data are generated locally. */
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
    cmpi.w #0x574d,%d7       /* WM: establish 2M mode */
    beq mode_ready
    cmpi.w #0x4700,%d7       /* G0: identity */
    blo done
    cmpi.w #0x4703,%d7       /* G3: scale and rotation */
    bhi done
wait_sub:
    btst #0,0xff8003
    bne.s wait_sub

    /* One 16x16 original stamp, stamp number 1 at Word RAM byte $80. */
    lea stamp(%pc),%a0
    lea 0x080080,%a1
    move.w #63,%d0
copy_stamp:
    move.w (%a0)+,(%a1)+
    dbf %d0,copy_stamp
    /* Small 256x256 map at Word RAM byte $20000, all entries stamp 1. */
    lea 0x0a0000,%a1
    move.w #255,%d0
fill_map:
    move.w #1,(%a1)+
    dbf %d0,fill_map

    move.w %d7,%d0
    andi.w #3,%d0
    lsl.w #1,%d0
    lea trace_table(%pc),%a0
    move.w 0(%a0,%d0.w),%d0
    adda.w %d0,%a0
    lea 0x0b0000,%a1
    move.w #63,%d0
copy_trace:
    move.w (%a0)+,(%a1)+
    dbf %d0,copy_trace
    lea 0x090000,%a1
    move.w #63,%d0
clear_output:
    move.w #0xffff,(%a1)+
    dbf %d0,clear_output

    move.w #0,0xff8058       /* 16x16 stamp, 256x256 map */
    move.w #0x8000,0xff805a  /* map byte $20000 */
    move.w #1,0xff805c       /* two vertical 8-pixel cells */
    move.w #0x4000,0xff805e  /* output byte $10000 */
    move.w #0,0xff8060       /* aligned pixel offset */
    move.w #16,0xff8062      /* output width in pixels */
    move.w #16,0xff8064      /* output height in pixels */
    move.w #0xc000,0xff8066  /* trace byte $30000; starts ASIC */
    move.l #0x000fffff,%d0
wait_asic:
    btst #7,0xff8058        /* high byte GRON bit 15 */
    beq.s asic_done
    subq.l #1,%d0
    bne.s wait_asic
    move.w #0xe001,0xff802e
    bra return_ram
asic_done:
    move.w %d7,%d0
    ori.w #0x0100,%d0
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
trace_table:
    .word trace_identity-trace_table,trace_scale-trace_table
    .word trace_rotate-trace_table,trace_combined-trace_table
stamp:
    .incbin "build/graphics-asic/stamp.bin"
trace_identity:
    .incbin "build/graphics-asic/trace-identity.bin"
trace_scale:
    .incbin "build/graphics-asic/trace-scale.bin"
trace_rotate:
    .incbin "build/graphics-asic/trace-rotate.bin"
trace_combined:
    .incbin "build/graphics-asic/trace-combined.bin"
module_end:
