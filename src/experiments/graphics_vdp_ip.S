/* ASIC image to Genesis VDP; build flags select size, pacing, and transfer path. */
.section .text
.global _start
.equ VDP_DATA,0xc00000
.equ VDP_CTRL,0xc00004
.equ STOPWATCH,0xa1200c
.equ RESULTS,0xff3000
.equ ERROR,0xff3f00
.equ STAGING,0xff6000
.equ PRESTAGE_TICKS,0xff2ff0
.equ READY_TICKS,0xff2ff2
.equ VERIFY_STAGE_START,0xff2ff4
.ifdef SIZE_64
.equ TILE_DIM,8
.equ COPY_WORDS,1024
.equ CASE_BASE,6
.else
.equ TILE_DIM,4
.equ COPY_WORDS,256
.equ CASE_BASE,3
.endif
.ifdef FRAME_DIV_2
.equ FRAMES,60
.else
.equ FRAMES,120
.endif
_start:
    move.l #0x47565354,%d3 /* GVST */
    lea VDP_CTRL,%a0
    lea VDP_DATA,%a1
    move.w #0x8104,(%a0) /* mode 5, display off, DMA off */
    move.w #0x8004,(%a0)
    move.w #0x8230,(%a0) /* plane A at $C000 */
    move.w #0x8407,(%a0) /* plane B at $E000 */
    move.w #0x8700,(%a0)
    move.w #0x8c00,(%a0) /* H32 */
    move.w #0x8f02,(%a0)
    move.w #0x9001,(%a0) /* 64x32 cells */
    move.l #0xc0000000,(%a0)
    lea palette(%pc),%a2
    move.w #15,%d0
palette_loop:
    move.w (%a2)+,(%a1)
    dbf %d0,palette_loop
    move.l #0x40000000,(%a0)
    moveq #0,%d0
    move.w #32767,%d1
clear_vram:
    move.w %d0,(%a1)
    dbf %d1,clear_vram
    lea plane_commands(%pc),%a2
    moveq #0,%d0 /* row */
plane_row:
    move.l (%a2)+,(%a0)
    moveq #0,%d1 /* column */
plane_column:
    move.w %d1,%d2
.ifdef SIZE_64
    lsl.w #3,%d2
.else
    lsl.w #2,%d2
.endif
    add.w %d0,%d2
    addq.w #1,%d2
    move.w %d2,(%a1)
    addq.w #1,%d1
    cmpi.w #TILE_DIM,%d1
    bne.s plane_column
    addq.w #1,%d0
    cmpi.w #TILE_DIM,%d0
    bne.s plane_row
    move.w #0x8144,(%a0) /* display on */

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
    moveq #0,%d6 /* frame and unique command sequence */
    moveq #CASE_BASE,%d7 /* first scaling case */
.ifdef PRECOMPUTED
    bsr preload_frames
.endif
    bsr request_asic
.ifdef PRESTAGE_DMA
.ifndef ROAD_RUNTIME_COMBINED
    bsr prestage_next
.endif
.endif
    lea RESULTS,%a6
    moveq #0,%d5 /* previous frame-start stopwatch */
.ifdef ROAD_RUNTIME
    clr.w READY_TICKS
.endif
frame_loop:
.ifdef FRAME_DIV_2
    /* Skip one complete VBlank so uploads target 30 Hz. */
skip_vblank_end:
    move.w (%a0),%d0
    btst #3,%d0
    bne.s skip_vblank_end
skip_vblank_start:
    move.w (%a0),%d0
    btst #3,%d0
    beq.s skip_vblank_start
.endif
    /* Observe a fresh VBlank edge, then upload one transformed image. */
wait_vblank_end:
    move.w (%a0),%d0
    btst #3,%d0
    bne.s wait_vblank_end
wait_vblank_start:
    move.w (%a0),%d0
    btst #3,%d0
    beq.s wait_vblank_start
    move.w STOPWATCH,%d0
    move.w %d0,%d1
    sub.w %d5,%d1
    andi.w #0x0fff,%d1
    move.w %d0,%d5
    move.w %d6,(%a6)+
    move.w %d7,(%a6)+
.ifdef DMA_ONLY
    moveq #1,%d2
.else
    move.w %d6,%d2
    andi.w #1,%d2
.endif
.ifdef REVERSE_TRANSFER
    eori.w #1,%d2
.endif
    move.w %d2,(%a6)+ /* 0 CPU, 1 staged DMA */
    move.w %d1,(%a6)+ /* frame interval, first sample ignored */
    tst.w %d2
    bne staged_dma
cpu_upload:
    clr.w (%a6)+ /* no staging */
    move.w STOPWATCH,%d1
    move.l #0x40200000,(%a0)
.ifdef PRECOMPUTED
    movea.l %a5,%a2
.else
    lea 0x210000,%a2
.endif
    move.w #COPY_WORDS-1,%d0
cpu_copy:
    move.w (%a2)+,(%a1)
    dbf %d0,cpu_copy
    bra upload_done
staged_dma:
.ifdef PRESTAGE_DMA
    move.w PRESTAGE_TICKS,(%a6)+
    move.w STOPWATCH,%d1
.else
    move.w STOPWATCH,%d1
.ifdef PRECOMPUTED
    movea.l %a5,%a2
.else
    lea 0x210000,%a2
.endif
    lea STAGING,%a3
    move.w #COPY_WORDS-1,%d0
stage_copy:
    move.w (%a2)+,(%a3)+
    dbf %d0,stage_copy
    move.w STOPWATCH,%d0
    sub.w %d1,%d0
    andi.w #0x0fff,%d0
    move.w %d0,(%a6)+
    move.w STOPWATCH,%d1
.endif
    move.w #0x8154,(%a0) /* DMA on, display on */
    move.w #0x9300,(%a0) /* low byte of DMA length */
.ifdef SIZE_64
    move.w #0x9404,(%a0) /* 1024 words */
.else
    move.w #0x9401,(%a0)
.endif
    move.w #0x9500,(%a0) /* $FF6000 / 2 = $7FB000 */
    move.w #0x96b0,(%a0)
    move.w #0x977f,(%a0)
    move.w #0x4020,(%a0) /* VRAM $0020, DMA command */
    move.w #0x0080,(%a0)
wait_dma:
    move.w (%a0),%d0
    btst #1,%d0
    bne.s wait_dma
    move.w #0x8144,(%a0) /* DMA off after completion */
upload_done:
    move.w STOPWATCH,%d0
    sub.w %d1,%d0
    andi.w #0x0fff,%d0
    move.w %d0,(%a6)+ /* upload/setup interval */
    move.w (%a0),%d0
    andi.w #8,%d0
    move.w %d0,(%a6)+ /* VBlank still asserted at completion */
.ifdef PRECOMPUTED
    clr.w (%a6)+ /* no runtime ASIC work */
.else
    move.w 0x218000,(%a6)+ /* prior ASIC start-to-busy-clear */
.endif
    move.w %d4,(%a6)+ /* prior ownership/prepare/ASIC/return */
.ifdef ROAD_RUNTIME
    move.w 0x218002,(%a6)+ /* prior sub-CPU trace construction */
    move.w READY_TICKS,(%a6)+ /* prior work ready after VBlank start */
.endif

    addq.w #1,%d6
    cmpi.w #FRAMES,%d6
    beq all_done
    move.w %d6,%d0
    divu.w #3,%d0
    swap %d0
    move.w %d0,%d7
    addq.w #CASE_BASE,%d7
    bsr request_asic
.ifdef PRESTAGE_DMA
.ifndef ROAD_RUNTIME_COMBINED
    bsr prestage_next
.endif
.endif
.ifdef ROAD_RUNTIME
    move.w STOPWATCH,%d0
    sub.w %d5,%d0
    andi.w #0x0fff,%d0
    move.w %d0,READY_TICKS
.endif
    bra frame_loop
all_done:
    move.l #0x47564f4b,%d3 /* GVOK */
    bra idle

request_asic:
.ifdef PRECOMPUTED
    move.w %d6,%d0
    divu.w #48,%d0
    swap %d0
    lsl.w #8,%d0
    add.w %d0,%d0 /* 512 bytes per precomputed output */
    lea 0x200000,%a5
    adda.w %d0,%a5
    moveq #0,%d4 /* no per-frame ownership/ASIC path */
.else
    move.w %d6,%d0
    lsl.w #4,%d0
    or.w %d7,%d0
    ori.w #0x5000,%d0
    move.w %d0,0xa1201e
    move.w %d0,%d2
    eori.w #0x8000,%d2
    move.w STOPWATCH,%d4
    move.b #2,0xa12003
wait_ownership:
    btst #0,0xa12003
    bne.s wait_ownership
    move.b #0x81,0xa12000
wait_reply:
    move.w 0xa1202e,%d0
    cmp.w %d2,%d0
    beq.s got_reply
    cmpi.w #0xe002,%d0
    beq fail_timeout
    bra.s wait_reply
got_reply:
    clr.w 0xa1201e
wait_return:
    btst #0,0xa12003
    beq.s wait_return
    move.w STOPWATCH,%d0
    sub.w %d4,%d0
    andi.w #0x0fff,%d0
    move.w %d0,%d4
.endif
    /* Every output word is checked before VDP upload. */
.ifdef PRECOMPUTED
    movea.l %a5,%a2
.else
    lea 0x210000,%a2
.endif
    move.w #COPY_WORDS-1,%d1
    moveq #0,%d2
.ifdef ROAD_RUNTIME_COMBINED
    move.w STOPWATCH,VERIFY_STAGE_START
    lea STAGING,%a3
.endif
sum_loop:
    moveq #0,%d0
    move.w (%a2)+,%d0
.ifdef ROAD_RUNTIME_COMBINED
    move.w %d0,(%a3)+
.endif
    add.l %d0,%d2
    dbf %d1,sum_loop
.ifdef ROAD_RUNTIME_COMBINED
    move.w STOPWATCH,%d0
    sub.w VERIFY_STAGE_START,%d0
    andi.w #0x0fff,%d0
    move.w %d0,PRESTAGE_TICKS /* checksum and staging together */
.endif
.ifdef ROAD_TRACE
    move.w %d6,%d0
.else
.ifdef ANIMATE_TRACE
    move.w %d6,%d0
.else
    move.w %d7,%d0
.endif
.endif
    lsl.w #2,%d0
.ifdef ROAD_TRACE
    lea road_sums(%pc),%a2
.else
.ifdef ANIMATE_TRACE
    lea animation_sums(%pc),%a2
.else
    lea expected_sums(%pc),%a2
.endif
.endif
    cmp.l 0(%a2,%d0.w),%d2
    bne fail_checksum
    rts
.ifdef PRESTAGE_DMA
prestage_next:
.ifdef DMA_ONLY
    bra.s prestage_copy
.endif
    btst #0,%d6
    bne.s prestage_copy
    clr.w PRESTAGE_TICKS
    rts
prestage_copy:
    move.w STOPWATCH,%d1
    lea 0x210000,%a2
    lea STAGING,%a3
    move.w #COPY_WORDS-1,%d0
prestage_loop:
    move.w (%a2)+,(%a3)+
    dbf %d0,prestage_loop
    move.w STOPWATCH,%d0
    sub.w %d1,%d0
    andi.w #0x0fff,%d0
    move.w %d0,PRESTAGE_TICKS
    rts
.endif
.ifdef PRECOMPUTED
preload_frames:
    move.w #0x5750,0xa1201e /* WP: copy 48 original precomputed frames */
    move.w STOPWATCH,%d4
    move.b #2,0xa12003
preload_wait_sub:
    btst #0,0xa12003
    bne.s preload_wait_sub
    move.b #0x81,0xa12000
preload_wait_reply:
    cmpi.w #0x5052,0xa1202e
    bne.s preload_wait_reply
    clr.w 0xa1201e
preload_wait_return:
    btst #0,0xa12003
    beq.s preload_wait_return
    move.w STOPWATCH,%d0
    sub.w %d4,%d0
    andi.w #0x0fff,%d0
    move.w %d0,ERROR+0x20 /* one-time preloading cost */
    rts
.endif
fail_checksum:
    move.w %d6,ERROR
    move.w %d7,ERROR+2
    move.l %d2,ERROR+4
    move.l 0(%a2,%d0.w),ERROR+8
    move.l #0x47564552,%d3 /* GVER */
    bra idle
fail_timeout:
    move.l #0x4756544f,%d3 /* GVTO */
idle:
    bra.s idle
.even
plane_commands:
.ifdef SIZE_64
    .long 0x45180003,0x45980003,0x46180003,0x46980003
    .long 0x47180003,0x47980003,0x48180003,0x48980003
.else
    .long 0x461c0003,0x469c0003,0x471c0003,0x479c0003
.endif
palette:
.ifdef ROAD_TRACE
    .word 0x0000,0x0000,0x00a0,0x0060
    .word 0x0000,0x0000,0x0000,0x0888
    .word 0x0000,0x0000,0x000e,0x0000
    .word 0x0000,0x0000,0x00ee,0x0eee
.else
    .word 0x0000,0x000e,0x00e0,0x0e00
    .word 0x00ee,0x0e0e,0x0ee0,0x0888
    .word 0x0444,0x0008,0x0080,0x0800
    .word 0x0088,0x0808,0x0880,0x0eee
.endif
expected_sums:
    .include "build/graphics-asic-bench/expected-sums.inc"
.ifdef ANIMATE_TRACE
animation_sums:
    .include "build/graphics-asic-bench/animation-32-sums.inc"
.endif
.ifdef ROAD_TRACE
road_sums:
    .include "build/perspective-road/road-sums.inc"
.endif
