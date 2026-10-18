/* Original Phase 0 main-CPU IP. Draw HELLO SEGA CD using original 5x7 tiles.
 * The same position-independent payload can be previewed as a Genesis ROM;
 * that preview is not evidence of Sega CD disc boot. */
.section .text
.global _start
_start:
    move.l  #0x50443030, %d0     /* "PD00" entry marker */
    lea     0xc00004, %a0         /* VDP control */
    lea     0xc00000, %a1         /* VDP data */

    move.w  #0x8104, (%a0)        /* mode 5, display off */
    move.w  #0x8004, (%a0)        /* full-color mode */
    move.w  #0x8230, (%a0)        /* plane A table at VRAM 0xc000 */
    move.w  #0x8407, (%a0)        /* plane B table at VRAM 0xe000 */
    move.w  #0x8700, (%a0)        /* backdrop palette entry 0 */
    move.w  #0x8c00, (%a0)        /* H32 mode */
    move.w  #0x8f02, (%a0)        /* VRAM word auto-increment */
    move.w  #0x9001, (%a0)        /* 64 by 32-cell scroll planes */

    move.l  #0xc0000000, (%a0)    /* CRAM address 0 */
    move.w  #0, (%a1)             /* black; avoid a read-modify-write */
    move.w  #0x0eee, (%a1)        /* white */

    move.l  #0x40000000, (%a0)    /* clear all 64 KiB VRAM */
    moveq   #0, %d1
    move.w  #32767, %d2
clear_vram:
    move.w  %d1, (%a1)
    dbf     %d2, clear_vram

    move.l  #0x40200000, (%a0)    /* tile 1 begins at VRAM 0x0020 */
    lea     font(%pc), %a2
    move.w  #143, %d2             /* nine tiles, 16 words each */
copy_font:
    move.w  (%a2)+, (%a1)
    dbf     %d2, copy_font

    move.l  #0x46160003, (%a0)    /* plane A, row 12, column 11 */
    lea     message(%pc), %a2
    moveq   #12, %d2             /* 13 tile indices */
copy_message:
    move.w  (%a2)+, (%a1)
    dbf     %d2, copy_message

    move.w  #0x8144, (%a0)        /* display on */
.ifdef HANDSHAKE
    move.w  #0x5044, 0xa1201e    /* last main-to-sub command word: "PD" */
    move.b  #0x81, 0xa12000     /* enable and request sub-CPU level-2 interrupt */
wait_reply:
    cmpi.w  #0x5350, 0xa1202e   /* last sub-to-main status word: "SP" */
    bne.s   wait_reply
    move.l  #0x4d533030, %d3    /* "MS00": both CPUs exchanged a word */
.endif
.ifdef LEVEL2_TEST
    move.w  #0x5044, 0xa1201e    /* request marker: "PD" */
    move.b  #0x81, 0xa12000     /* request sub-CPU level-2 interrupt */
wait_level2:
    cmpi.w  #0x4932, 0xa1202e   /* interrupt callback reply: "I2" */
    bne.s   wait_level2
    move.l  #0x49323030, %d3    /* "I200": interrupt callback completed */
.endif
.ifdef WORDRAM_TEST
    move.w  #0x574d, 0xa1201e    /* "WM": ask sub-CPU for 2M mode, main owns */
    move.b  #0x81, 0xa12000
wait_wordram_mode:
    cmpi.w  #0x4d52, 0xa1202e   /* "MR": mode request handled */
    bne.s   wait_wordram_mode
wait_2m_main:
    btst    #2, 0xa12003        /* MODE must be clear */
    bne.s   wait_2m_main
    btst    #0, 0xa12003        /* RET must be set */
    beq.s   wait_2m_main
    move.w  #0x1357, 0x210000    /* seed the main-visible 2M Word RAM */
    move.w  #0x2468, 0x210002
    move.w  #0x5752, 0xa1201e    /* "WR": Word RAM request */
    move.b  #0x02, 0xa12003     /* DMNA: hand 2M Word RAM to sub-CPU */
wait_sub_ownership:
    btst    #0, 0xa12003        /* RET clears when sub-CPU owns Word RAM */
    bne.s   wait_sub_ownership
    move.b  #0x81, 0xa12000     /* invoke sub-CPU level-2 callback */
wait_wordram_reply:
    cmpi.w  #0x5744, 0xa1202e   /* "WD": sub-CPU finished its write */
    bne.s   wait_wordram_reply
wait_main_ownership:
    btst    #0, 0xa12003        /* RET set after sub-CPU returns Word RAM */
    beq.s   wait_main_ownership
    move.w  0x210000, %d4
    move.w  0x210002, %d5
    cmpi.w  #0xabcd, %d4
    bne.s   wordram_fail
    cmpi.w  #0x1234, %d5
    bne.s   wordram_fail
    move.l  #0x57523030, %d3    /* "WR00": verified round trip */
    bra.s   idle
wordram_fail:
    move.l  #0x57524552, %d3    /* "WRER": data mismatch */
.endif
.ifdef WORDRAM_REPEAT_TEST
    move.w  #0x574d, 0xa1201e    /* "WM": establish 2M mode */
    move.b  #0x81, 0xa12000
repeat_wait_mode:
    cmpi.w  #0x4d52, 0xa1202e   /* "MR": mode ready */
    bne.s   repeat_wait_mode
repeat_wait_main:
    move.b  0xa12003, %d0
    andi.b  #0x05, %d0          /* MODE=0, RET=1 */
    cmpi.b  #0x01, %d0
    bne.s   repeat_wait_main
    move.w  #0, 0xa1201e
    moveq   #1, %d6            /* fixed commands $6001..$6010 */
    moveq   #0, %d5            /* completed handoffs */
.ifdef WORDRAM_TIMER_TEST
    lea     timing_samples(%pc), %a3
    moveq   #0, %d3            /* accumulated stopwatch ticks */
    lea     timing_batch_start(%pc), %a4
    move.w  0xa1200c, (%a4)     /* batch start; main side can read, not reset */
.endif
repeat_handoff:
.ifdef WORDRAM_TIMER_TEST
    move.w  0xa1200c, %d2       /* shared stopwatch, before this transaction */
.endif
    move.w  %d6, %d7
    ori.w   #0x6000, %d7
    move.w  %d7, 0x210000
    move.w  %d7, %d0
    not.w   %d0
    move.w  %d0, 0x210002
    move.w  %d7, 0xa1201e
    move.b  #0x02, 0xa12003     /* main yields 2M Word RAM */
repeat_wait_sub:
    btst    #0, 0xa12003
    bne.s   repeat_wait_sub
    move.b  #0x81, 0xa12000     /* one level-2 request per handoff */
    move.w  %d7, %d4
    eori.w  #0xc000, %d4        /* expected status: $A001..$A010 */
repeat_wait_reply:
    move.w  0xa1202e, %d0
    cmp.w   %d4, %d0
    beq.s   repeat_return
    andi.w  #0xf000, %d0
    cmpi.w  #0xe000, %d0        /* sub-CPU rejected main's seed */
    beq.s   repeat_fail
    bra.s   repeat_wait_reply
repeat_return:
    move.w  #0, 0xa1201e      /* prevent a later interrupt replay */
repeat_wait_return:
    btst    #0, 0xa12003
    beq.s   repeat_wait_return
    move.w  0x210000, %d0
    move.w  0x210002, %d1
    move.w  %d7, %d4
    not.w   %d4
    cmp.w   %d4, %d0
    bne.s   repeat_fail
    move.w  %d7, %d4
    eori.w  #0x5a5a, %d4
    cmp.w   %d4, %d1
    bne.s   repeat_fail
.ifdef WORDRAM_TIMER_TEST
    move.w  0xa1200c, %d4
    sub.w   %d2, %d4
    andi.l  #0x0fff, %d4        /* one 12-bit modulo stopwatch interval */
    move.w  %d4, (%a3)+
    add.l   %d4, %d3
.endif
    move.w  %d6, %d5
    addq.w  #1, %d6
    cmpi.w  #17, %d6
    bne     repeat_handoff
.ifdef WORDRAM_TIMER_TEST
    lea     timing_total(%pc), %a4
    move.l  %d3, (%a4)
    move.w  0xa1200c, %d4
    lea     timing_batch_start(%pc), %a4
    sub.w   (%a4), %d4
    andi.w  #0x0fff, %d4
    lea     timing_batch_delta(%pc), %a4
    move.w  %d4, (%a4)
.endif
    move.l  #0x52313630, %d3    /* "R160": sixteen verified handoffs */
    bra     idle
repeat_fail:
    move.l  #0x52455252, %d3    /* "RERR": command/data mismatch */
.endif
idle:
    bra.s   idle

.align 2
message:
    .word 1,2,3,3,4,0,5,2,6,7,0,8,9
font:
    .incbin "build/smoke/font.bin"
.ifdef WORDRAM_TIMER_TEST
.align 2
timing_samples:
    .space 32                   /* sixteen stopwatch tick intervals */
timing_total:
    .long 0                    /* sum of the sixteen recorded intervals */
timing_batch_start:
    .word 0
timing_batch_delta:
    .word 0                    /* one modulo interval around the entire batch */
.endif
