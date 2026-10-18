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
idle:
    bra.s   idle

.align 2
message:
    .word 1,2,3,3,4,0,5,2,6,7,0,8,9
font:
    .incbin "build/smoke/font.bin"
