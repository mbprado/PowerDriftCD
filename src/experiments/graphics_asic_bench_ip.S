/* Main CPU checks full output checksum and records 27 timing samples. */
.section .text
.global _start
.equ RESULTS,0xff1200
.equ ERROR,0xff13f0
_start:
    move.l #0x47425354,%d3  /* GBST */
    move.w #0x574d,0xa1201e
    move.b #0x81,0xa12000
wait_mode:
    cmpi.w #0x4d52,0xa1202e
    bne.s wait_mode
wait_main:
    move.b 0xa12003,%d0
    andi.b #5,%d0
    cmpi.b #1,%d0
    bne.s wait_main
    clr.w 0xa1201e
    lea order_table(%pc),%a4
    lea expected_sums(%pc),%a5
    lea RESULTS,%a6
    moveq #26,%d6
next_case:
    moveq #0,%d7
    move.b (%a4)+,%d7
    move.w %d6,%d0
    lsl.w #4,%d0
    or.w %d7,%d0
    ori.w #0x5000,%d0
    move.w %d0,0xa1201e
    move.w 0xa1200c,%d4
    move.b #2,0xa12003
wait_ownership:
    btst #0,0xa12003
    bne.s wait_ownership
    move.b #0x81,0xa12000
    move.w %d0,%d5
    eori.w #0x8000,%d5
wait_reply:
    move.w 0xa1202e,%d0
    cmp.w %d5,%d0
    beq.s got_reply
    cmpi.w #0xe002,%d0
    beq fail_timeout
    bra.s wait_reply
got_reply:
    clr.w 0xa1201e
wait_return:
    btst #0,0xa12003
    beq.s wait_return
    move.w 0xa1200c,%d0
    sub.w %d4,%d0
    andi.w #0x0fff,%d0
    move.w %d7,(%a6)+
    move.w %d0,(%a6)+ /* complete ownership + callback + ASIC path */
    move.w 0x218000,(%a6)+ /* sub ASIC interval */
    move.w 0x218002,(%a6)+ /* sub timer read control */
    /* size = 16 << floor(case/3) */
    move.w %d7,%d0
    divu.w #3,%d0
    andi.l #0xffff,%d0
    move.w #16,%d2
    lsl.w %d0,%d2
    mulu.w %d2,%d2
    lsr.l #2,%d2
    subq.w #1,%d2
    lea 0x210000,%a0
    moveq #0,%d1
checksum:
    moveq #0,%d0
    move.w (%a0)+,%d0
    add.l %d0,%d1
    dbf %d2,checksum
    move.w %d7,%d0
    lsl.w #2,%d0
    cmp.l 0(%a5,%d0.w),%d1
    bne fail_checksum
    move.l %d1,(%a6)+
    dbf %d6,next_case
    move.l #0x47424f4b,%d3 /* GBOK */
    bra idle
fail_checksum:
    move.w %d7,ERROR
    move.l %d1,ERROR+2
    move.l 0(%a5,%d0.w),ERROR+6
    move.l #0x47424552,%d3 /* GBER */
    bra idle
fail_timeout:
    move.l #0x4742544f,%d3 /* GBTO */
idle:
    bra.s idle
.even
order_table:
    .byte 0,1,2,3,4,5,6,7,8
    .byte 8,7,6,5,4,3,2,1,0
    .byte 0,1,2,3,4,5,6,7,8
    .even
expected_sums:
    .include "build/graphics-asic-bench/expected-sums.inc"
