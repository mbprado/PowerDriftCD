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
.ifdef WORDRAM_REPEAT_TEST
    movem.l %d0/%d7, -(%sp)
    move.w  0xff801e, %d7
    cmpi.w  #0x574d, %d7       /* "WM": establish 2M mode */
    beq.s   repeat_switch_mode
    move.w  %d7, %d0
    andi.w  #0xff00, %d0
    cmpi.w  #0x6000, %d0       /* one of sixteen numbered commands */
    bne.s   repeat_sub_done
repeat_wait_access:
    btst    #0, 0xff8003      /* RET=0: sub owns 2M Word RAM */
    bne.s   repeat_wait_access
    cmp.w   0x090000, %d7
    bne.s   repeat_bad_seed
    move.w  %d7, %d0
    not.w   %d0
    cmp.w   0x090002, %d0
    bne.s   repeat_bad_seed
    move.w  %d0, 0x090000
    move.w  %d7, %d0
    eori.w  #0x5a5a, %d0
    move.w  %d0, 0x090002
    move.b  #0x01, 0xff8003   /* return RAM before acknowledging */
    move.w  %d7, %d0
    eori.w  #0xc000, %d0
    move.w  %d0, 0xff802e
    bra.s   repeat_sub_done
repeat_bad_seed:
    move.b  #0x01, 0xff8003
    move.w  %d7, %d0
    andi.w  #0x00ff, %d0
    ori.w   #0xe000, %d0
    move.w  %d0, 0xff802e     /* error identifies failed command */
    bra.s   repeat_sub_done
repeat_switch_mode:
    move.b  #0x01, 0xff8003
    move.w  #0x4d52, 0xff802e
repeat_sub_done:
    movem.l (%sp)+, %d0/%d7
.endif
    rts
user_call:
    rts
module_end:
