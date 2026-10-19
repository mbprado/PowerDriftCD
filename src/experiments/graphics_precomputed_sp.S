/* Original precomputed comparison: one-time copy of 48 32x32 images. */
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
    movem.l %d0/%a0-%a1,-(%sp)
    cmpi.w #0x574d,0xff801e
    beq.s mode_ready
    cmpi.w #0x5750,0xff801e
    bne.s done
wait_sub:
    btst #0,0xff8003
    bne.s wait_sub
    lea frames(%pc),%a0
    lea 0x080000,%a1
    move.w #12287,%d0 /* 48 × 512 bytes */
copy_frames:
    move.w (%a0)+,(%a1)+
    dbf %d0,copy_frames
    move.b #1,0xff8003
    move.w #0x5052,0xff802e
    bra.s done
mode_ready:
    move.b #1,0xff8003
    move.w #0x4d52,0xff802e
done:
    movem.l (%sp)+,%d0/%a0-%a1
    rts
user_call:
    rts
.even
frames:
    .incbin "build/graphics-asic-bench/animation-32-48frames.bin"
module_end:
