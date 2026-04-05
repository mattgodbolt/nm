;******************************************************************
; Ninja Massacre AY Music - BBC Micro VGC Player (Bass Enhanced)
; Based on vgm-player-bbc by Simon Morris
;
; Uses IRQ-driven volume toggling to synthesize bass frequencies
; below the SN76489's native 122Hz minimum.
; Requires BBC Master (65C02) or equivalent.
;******************************************************************

; Allocate vars in ZP
.zp_start
ORG &70
GUARD &8f

; Include common code headers here - these can declare ZP vars from the pool
INCLUDE "tools/vgm-player-bbc/lib/vgcplayer_config.h.asm"
INCLUDE "tools/vgm-player-bbc/lib/vgcplayer.h.asm"

.zp_end


\ ******************************************************************
\ * Main code
\ ******************************************************************

ORG &1900
GUARD &7c00

.start

; Include the bass-enhanced player library
; (uses 6522 VIA timer IRQs for software bass synthesis)
INCLUDE "tools/vgm-player-bbc/lib/vgcplayer_bass.asm"

ALIGN 256
.main
{
    ; Print title
    ldx #0
.print_loop
    lda title_text, x
    beq done_print
    jsr &FFEE       ; OSWRCH
    inx
    bne print_loop
.done_print

    ; Initialize IRQ handler for bass synthesis
    ; (hooks IRQ vector, sets up VIA timers)
    jsr irq_init

    ; Initialize the VGM player with a VGC data stream
    lda #hi(vgm_stream_buffers)
    ldx #lo(vgm_data)
    ldy #hi(vgm_data)
    clc             ; clear carry = no looping (song plays once)
    jsr vgm_init

    ; Main playback loop
    ; Note: interrupts must remain ENABLED between vgm_update calls
    ; so that the VIA timer IRQs can fire for bass synthesis.
    ; We only disable them briefly around vgm_update itself.
.loop
    ; Wait for vsync (VIA CA1 interrupt flag, bit 1)
    lda #2
    .vsync1
    bit &FE4D
    beq vsync1
    sta &FE4D

    ; Update the player (with interrupts disabled to avoid re-entrancy)
    sei
    jsr vgm_update
    cli

    beq loop        ; 0 = still playing

    ; Song finished
    rts
}

.title_text
    EQUS "Ninja Massacre - BBC Micro", 13, 10
    EQUS "Music by David Whittaker (Codemasters 1989)", 13, 10
    EQUS "Converted from ZX Spectrum 128K AY", 13, 10
    EQUS "Bass enhanced via IRQ-driven volume toggling", 13, 10, 10
    EQUS "Playing...", 13, 10
    EQUB 0

; Reserve space for VGM decode buffers (8x256 = 2KB)
.vgm_buffer_start
ALIGN 256
.vgm_stream_buffers
    SKIP 256*8
.vgm_buffer_end

; Include the music data
.vgm_data
INCBIN "song_0_sn.vgc"

.end

PRINT "Code size: ", ~(end - start), " bytes"
PRINT "VGC data at: &", ~vgm_data

SAVE "NMMusic", start, end, main
