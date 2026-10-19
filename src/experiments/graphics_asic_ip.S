/* Main CPU orchestrates four ASIC validation cases and checks every output word. */
.section .text
.global _start
.equ RESULTS,0xff1100
_start:
    move.l #0x47305354,%d3  /* G0ST */
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
    lea expected_table(%pc),%a4
    lea RESULTS,%a2
    moveq #0,%d6
next_case:
    move.w %d6,%d7
    ori.w #0x4700,%d7
    move.w %d7,0xa1201e
    move.b #2,0xa12003
wait_ownership:
    btst #0,0xa12003
    bne.s wait_ownership
    move.b #0x81,0xa12000
    move.w %d7,%d5
    ori.w #0x0100,%d5
wait_reply:
    move.w 0xa1202e,%d0
    cmp.w %d5,%d0
    beq.s got_reply
    cmpi.w #0xe001,%d0
    beq fail_timeout
    bra.s wait_reply
got_reply:
    clr.w 0xa1201e
wait_return:
    btst #0,0xa12003
    beq.s wait_return
    move.w %d6,%d0
    lsl.w #1,%d0
    move.w 0(%a4,%d0.w),%d0
    lea 0(%a4,%d0.w),%a0
    lea 0x210000,%a1
    move.w #63,%d1
compare:
    move.w (%a1)+,%d0
    cmp.w (%a0)+,%d0
    bne.s fail_compare
    dbf %d1,compare
    move.w %d5,(%a2)+
    addq.w #1,%d6
    cmpi.w #4,%d6
    bne next_case
    move.l #0x47304f4b,%d3  /* G0OK */
    bra idle
fail_compare:
    move.w %d6,RESULTS+8
    move.w %d1,RESULTS+10
    move.w %d0,RESULTS+12
    move.w -2(%a0),RESULTS+14
    move.l #0x47304552,%d3  /* G0ER */
    bra idle
fail_timeout:
    move.l #0x4730544f,%d3  /* G0TO */
idle:
    bra.s idle
.even
expected_table:
    .word expected_identity-expected_table,expected_scale-expected_table
    .word expected_rotate-expected_table,expected_combined-expected_table
expected_identity:
    .incbin "build/graphics-asic/expected-identity.bin"
expected_scale:
    .incbin "build/graphics-asic/expected-scale.bin"
expected_rotate:
    .incbin "build/graphics-asic/expected-rotate.bin"
expected_combined:
    .incbin "build/graphics-asic/expected-combined.bin"
