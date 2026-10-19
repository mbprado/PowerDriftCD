/* Original Sega CD sub-CPU module for four paired main-CPU stopwatch phases. */
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
    move.l  #0x53503430, %d1  /* SP40: module loaded */
    rts
main_loop:
    rts
interrupt:
    movem.l %d0/%d7, -(%sp)
    move.w  0xff801e, %d7
    cmpi.w  #0x574d, %d7     /* WM: 2M mode, main ownership */
    beq     switch_mode
    move.w  %d7, %d0
    andi.w  #0xf000, %d0
    cmpi.w  #0x1000, %d0
    beq.s   irq_only
    cmpi.w  #0x2000, %d0
    beq.s   ownership_only
    cmpi.w  #0x6000, %d0
    beq.s   full_exchange
    bra     callback_done

irq_only:
    move.w  %d7, %d0
    ori.w   #0x2000, %d0
    move.w  %d0, 0xff802e
    bra     callback_done

ownership_only:
    bsr     wait_access
    move.b  #0x01, 0xff8003  /* return 2M Word RAM */
    move.w  %d7, %d0
    eori.w  #0x6000, %d0
    move.w  %d0, 0xff802e
    bra     callback_done

full_exchange:
    bsr     wait_access
    cmp.w   0x090000, %d7
    bne.s   bad_seed
    move.w  %d7, %d0
    not.w   %d0
    cmp.w   0x090002, %d0
    bne.s   bad_seed
    move.w  %d0, 0x090000
    move.w  %d7, %d0
    eori.w  #0x5a5a, %d0
    move.w  %d0, 0x090002
    move.b  #0x01, 0xff8003
    move.w  %d7, %d0
    eori.w  #0xc000, %d0
    move.w  %d0, 0xff802e
    bra     callback_done
bad_seed:
    move.b  #0x01, 0xff8003
    move.w  %d7, %d0
    andi.w  #0x00ff, %d0
    ori.w   #0xe000, %d0
    move.w  %d0, 0xff802e
    bra     callback_done

switch_mode:
    move.b  #0x01, 0xff8003
    move.w  #0x4d52, 0xff802e
callback_done:
    movem.l (%sp)+, %d0/%d7
    rts
wait_access:
    btst    #0, 0xff8003
    bne.s   wait_access
    rts
user_call:
    rts
module_end:
