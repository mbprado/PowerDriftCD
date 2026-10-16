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
    rts
interrupt:
    rts
user_call:
    rts
module_end:
