;******************************************************************
; Ninja Massacre AY Music - BBC Micro VGC Player
; Based on vgm-player-bbc by Simon Morris
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

; Include the player library
INCLUDE "tools/vgm-player-bbc/lib/vgcplayer.asm"

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

    ; Initialize the VGM player
    lda #hi(vgm_stream_buffers)
    ldx #lo(vgm_data)
    ldy #hi(vgm_data)
    clc             ; clear carry = no looping (song plays once)
    jsr vgm_init

    ; Main playback loop - sync to vsync (50Hz)
    sei
.loop
    ; Wait for vsync
    lda #2
    .vsync1
    bit &FE4D
    beq vsync1
    sta &FE4D

    ; Update the player
    jsr vgm_update
    beq loop        ; 0 = still playing

    ; Song finished
    cli
    rts
}

.title_text
    EQUS "Ninja Massacre - BBC Micro", 13, 10
    EQUS "Music by Adam Waring (Codemasters 1989)", 13, 10
    EQUS "Converted from ZX Spectrum 128K AY", 13, 10, 10
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
