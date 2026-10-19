/* Original US Sega CD IP: four 2048-iteration stopwatch batches.
 * Results: main RAM $FF1000..$FF104B. Proprietary startup bytes are external. */
.section .text
.global _start

.equ CONTROL,    0xff1000
.equ IRQ_ONLY,   0xff1010
.equ OWNER_ONLY, 0xff1020
.equ FULL,       0xff1030
.equ COUNTS,     0xff1040
.equ FAIL_CMD,   0xff1048
.equ FAIL_PHASE, 0xff104a
.equ STOPWATCH,  0xa1200c
.equ ITERATIONS, 2048

/* Result block: elapsed.l, wraps.w, maximum modular gap.w, previous.w,
 * first.w, last.w. Each adjacent read must be <4096 ticks apart. */
_start:
    move.l  #0x50345354, %d3  /* P4ST: entered paired experiment */
    clr.l   COUNTS
    clr.l   COUNTS+4
    clr.w   FAIL_CMD
    clr.w   FAIL_PHASE
    move.w  #0x574d, 0xa1201e /* WM: establish 2M, main ownership */
    move.b  #0x81, 0xa12000
wait_mode:
    cmpi.w  #0x4d52, 0xa1202e
    bne.s   wait_mode
wait_main:
    move.b  0xa12003, %d0
    andi.b  #0x05, %d0
    cmpi.b  #0x01, %d0
    bne.s   wait_main
    clr.w   0xa1201e

.ifdef REVERSE_PHASES
    lea     FULL, %a0
    lea     COUNTS+6, %a1
    move.w  #0x6000, %d4
    bsr     run_batch
    lea     OWNER_ONLY, %a0
    lea     COUNTS+4, %a1
    move.w  #0x2000, %d4
    bsr     run_batch
    lea     IRQ_ONLY, %a0
    lea     COUNTS+2, %a1
    move.w  #0x1000, %d4
    bsr     run_batch
    lea     CONTROL, %a0
    lea     COUNTS, %a1
    moveq   #0, %d4
    bsr     run_batch
.else
    lea     CONTROL, %a0
    lea     COUNTS, %a1
    moveq   #0, %d4
    bsr     run_batch
    lea     IRQ_ONLY, %a0
    lea     COUNTS+2, %a1
    move.w  #0x1000, %d4
    bsr     run_batch
    lea     OWNER_ONLY, %a0
    lea     COUNTS+4, %a1
    move.w  #0x2000, %d4
    bsr     run_batch
    lea     FULL, %a0
    lea     COUNTS+6, %a1
    move.w  #0x6000, %d4
    bsr     run_batch
.endif
    move.l  #0x50344f4b, %d3  /* P4OK: all phases completed */
    bra     idle

run_batch:
    bsr     timer_reset
    moveq   #1, %d6
batch_loop:
    bsr     timer_sample
    move.w  %d6, %d7
    or.w    %d4, %d7
    tst.w   %d4
    beq     batch_end          /* bookkeeping only */
    cmpi.w  #0x1000, %d4
    beq     do_irq
    cmpi.w  #0x2000, %d4
    beq     do_ownership
    bra     do_full

do_irq:
    move.w  %d7, 0xa1201e
    move.b  #0x81, 0xa12000   /* INT2, no Word RAM transfer */
    move.w  %d7, %d5
    ori.w   #0x2000, %d5      /* expected $3001..$3800 */
    bra     wait_reply

do_ownership:
    move.w  %d7, 0xa1201e
    move.b  #0x02, 0xa12003   /* yield 2M Word RAM; no data access */
    bra     wait_sub

do_full:
    move.w  %d7, 0x210000
    move.w  %d7, %d0
    not.w   %d0
    move.w  %d0, 0x210002
    move.w  %d7, 0xa1201e
    move.b  #0x02, 0xa12003
wait_sub:
    btst    #0, 0xa12003
    bne.s   wait_sub
    move.b  #0x81, 0xa12000
    move.w  %d7, %d5
    cmpi.w  #0x2000, %d4
    bne.s   full_reply
    eori.w  #0x6000, %d5      /* ownership-only expected $4001..$4800 */
    bra.s   wait_reply
full_reply:
    eori.w  #0xc000, %d5      /* full expected $A001..$A800 */
wait_reply:
    move.w  0xa1202e, %d0
    cmp.w   %d5, %d0
    beq.s   got_reply
    andi.w  #0xf000, %d0
    cmpi.w  #0xe000, %d0      /* sub-CPU seed failure */
    beq     batch_fail
    bra.s   wait_reply
got_reply:
    clr.w   0xa1201e        /* prevent command replay */
    cmpi.w  #0x1000, %d4
    beq.s   batch_end
wait_return:
    btst    #0, 0xa12003
    beq.s   wait_return
    cmpi.w  #0x2000, %d4
    beq.s   batch_end
    move.w  0x210000, %d0
    move.w  0x210002, %d1
    move.w  %d7, %d2
    not.w   %d2
    cmp.w   %d2, %d0
    bne     batch_fail
    move.w  %d7, %d2
    eori.w  #0x5a5a, %d2
    cmp.w   %d2, %d1
    bne     batch_fail
batch_end:
    bsr     timer_sample
    move.w  %d6, (%a1)
    addq.w  #1, %d6
    cmpi.w  #ITERATIONS+1, %d6
    bne     batch_loop
    bsr     timer_sample
    move.w  8(%a0), 12(%a0)
    rts

batch_fail:
    move.w  %d7, FAIL_CMD
    move.w  %d4, FAIL_PHASE
    move.l  #0x50344552, %d3  /* P4ER: callback or data mismatch */
idle:
    bra.s   idle

timer_reset:
    clr.l   (%a0)
    clr.w   4(%a0)
    clr.w   6(%a0)
    move.w  STOPWATCH, %d0
    move.w  %d0, 8(%a0)
    move.w  %d0, 10(%a0)
    clr.w   12(%a0)
    rts

timer_sample:
    move.w  STOPWATCH, %d0
    move.w  8(%a0), %d1
    cmp.w   %d1, %d0
    bcc.s   no_wrap
    addq.w  #1, 4(%a0)
no_wrap:
    move.w  %d0, %d2
    sub.w   %d1, %d2
    andi.w  #0x0fff, %d2
    cmp.w   6(%a0), %d2
    bls.s   no_max
    move.w  %d2, 6(%a0)
no_max:
    andi.l  #0x00000fff, %d2
    add.l   %d2, (%a0)
    move.w  %d0, 8(%a0)
    rts
