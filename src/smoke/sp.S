/* Original Phase 0 sub-CPU system-program module. No proprietary boot code. */
.section .text
.global _start

_start:
module_start:
    .ascii "MAIN       "
    .byte 0                 /* BIOS module flag */
    .word 0x0100            /* Version */
    .word 0                 /* Normal module */
    .long 0                 /* No next module */
    .long module_end-module_start
    .long callbacks-module_start
    .long 0                 /* No requested Word RAM */

callbacks:
    .word initialize-callbacks
    .word main_loop-callbacks
    .word interrupt-callbacks
    .word user_call-callbacks
    .word 0

initialize:
    move.l #0x53503030,%d1  /* "SP00" debugger marker */
    rts
main_loop:
.ifdef HANDSHAKE
    cmpi.w  #0x5044, 0xff801e   /* main-to-sub command word: "PD" */
    bne.s   1f
    move.w  #0x5350, 0xff802e   /* sub-to-main reply word: "SP" */
1:
.endif
    rts
interrupt:
.ifdef LEVEL2_TEST
    cmpi.w  #0x5044, 0xff801e   /* only acknowledge this experiment's command */
    bne.s   1f
    move.l  #0x49323030, %d2    /* "I200" debugger marker */
    move.w  #0x4932, 0xff802e   /* reply only from the level-2 callback */
1:
.endif
.ifdef WORDRAM_TEST
    cmpi.w  #0x574d, 0xff801e   /* "WM": establish 2M mode */
    beq.s   switch_wordram_mode
    cmpi.w  #0x5752, 0xff801e   /* "WR": write the shared data */
    bne.s   wordram_done
wait_wordram_access:
    btst    #0, 0xff8003        /* RET clear: sub-CPU owns 2M Word RAM */
    bne.s   wait_wordram_access
    move.w  #0xabcd, 0x090000   /* same offset as main $210000 */
    move.w  #0x1234, 0x090002
    move.b  #0x01, 0xff8003     /* RET: return Word RAM to main-CPU */
    move.w  #0x5744, 0xff802e   /* "WD": done */
    bra.s   wordram_done
switch_wordram_mode:
    move.b  #0x01, 0xff8003     /* 2M mode, RET: main-CPU owns it */
    move.w  #0x4d52, 0xff802e   /* "MR": mode established */
wordram_done:
.endif
    rts
user_call:
    rts
module_end:
