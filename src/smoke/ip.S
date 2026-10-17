/* Original Sega CD initial program for Phase 0.  The BIOS should enter here
 * on the main 68000; D0 is a debugger-visible marker. */
    .section .text
    .global _start
_start:
    move.l  #0x50443030, %d0    /* ASCII "PD00" */
idle:
    bra.s   idle
