/* Original US Sega CD IP: 2048 checked 2M Word RAM exchanges and a timer-only
 * control loop. Results reside in main RAM $FF1000..$FF1025. The locally held
 * startup bytes used to boot private test discs are never included here. */
.section .text
.global _start

.equ CONTROL,       0xff1000
.equ EXCHANGE,      0xff1010
.equ CONTROL_COUNT, 0xff1020
.equ EXCHANGE_COUNT,0xff1022
.equ FAIL_COMMAND,  0xff1024
.equ STOPWATCH,     0xa1200c
.equ ITERATIONS,    2048

/* Each result block: elapsed.l +0, observed wraps.w +4, largest gap.w +6,
 * previous reading.w +8, first reading.w +10, last reading.w +12. */
_start:
    move.l  #0x4c325354, %d3    /* L2ST: entered long test */
    clr.w   CONTROL_COUNT
    clr.w   EXCHANGE_COUNT
    clr.w   FAIL_COMMAND
    move.w  #0x574d, 0xa1201e  /* WM: ask sub-CPU for 2M mode */
    move.b  #0x81, 0xa12000
wait_mode:
    cmpi.w  #0x4d52, 0xa1202e  /* MR: mode request completed */
    bne.s   wait_mode
wait_main:
    move.b  0xa12003, %d0
    andi.b  #0x05, %d0
    cmpi.b  #0x01, %d0          /* MODE=0 and RET=1 */
    bne.s   wait_main
    clr.w   0xa1201e

    lea     CONTROL, %a0
    bsr     timer_reset
    moveq   #1, %d6
control_loop:
    bsr     timer_sample        /* two reads and accounting per iteration */
    move.w  %d6, %d7
    ori.w   #0x6000, %d7
    bsr     timer_sample
    move.w  %d6, CONTROL_COUNT
    addq.w  #1, %d6
    cmpi.w  #ITERATIONS+1, %d6
    bne.s   control_loop
    bsr     timer_sample
    move.w  8(%a0), 12(%a0)

    lea     EXCHANGE, %a0
    bsr     timer_reset
    moveq   #1, %d6
exchange_loop:
    bsr     timer_sample
    move.w  %d6, %d7
    ori.w   #0x6000, %d7
    move.w  %d7, 0x210000
    move.w  %d7, %d0
    not.w   %d0
    move.w  %d0, 0x210002
    move.w  %d7, 0xa1201e
    move.b  #0x02, 0xa12003   /* yield 2M Word RAM */
wait_sub:
    btst    #0, 0xa12003
    bne.s   wait_sub
    move.b  #0x81, 0xa12000   /* request sub-CPU level 2 */
    move.w  %d7, %d4
    eori.w  #0xc000, %d4      /* expected reply $A001..$A800 */
wait_reply:
    move.w  0xa1202e, %d0
    cmp.w   %d4, %d0
    beq.s   got_reply
    andi.w  #0xf000, %d0
    cmpi.w  #0xe000, %d0      /* bad seed in sub-CPU callback */
    beq.s   exchange_fail
    bra.s   wait_reply
got_reply:
    clr.w   0xa1201e         /* prevent command replay */
wait_return:
    btst    #0, 0xa12003
    beq.s   wait_return
    move.w  0x210000, %d0
    move.w  0x210002, %d1
    move.w  %d7, %d4
    not.w   %d4
    cmp.w   %d4, %d0
    bne.s   exchange_fail
    move.w  %d7, %d4
    eori.w  #0x5a5a, %d4
    cmp.w   %d4, %d1
    bne.s   exchange_fail
    bsr     timer_sample
    move.w  %d6, EXCHANGE_COUNT
    addq.w  #1, %d6
    cmpi.w  #ITERATIONS+1, %d6
    bne     exchange_loop
    bsr     timer_sample
    move.w  8(%a0), 12(%a0)
    move.l  #0x4c324f4b, %d3  /* L2OK: all 2048 data checks passed */
    bra.s   idle
exchange_fail:
    move.w  %d7, FAIL_COMMAND
    move.l  #0x4c455252, %d3  /* LERR: bad seed, reply, or data */
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

/* Every adjacent read must be less than one 4096-tick lap apart. Accumulating
 * all modular gaps retains whole-batch wraps that start/end subtraction loses. */
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
