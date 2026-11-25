;;; DEViLBOX/ArcadeGame addition to ngdevkit nullsound (upstream 8756cbd): Furnace F8xx / F9xx.
;;; Furnace F8xx/F9xx stop any volume slide, then add/subtract xx (chip scale) to the current
;;; volume once, clamped to [0, channel max]. The channel state layout is common to FM, SSG and
;;; ADPCM-B (struct-fx.inc), so one op serves all three; the max is the one each channel type
;;; stores in VOL_CTX+SLIDE_MAX at init (FM 0x7f, SSG 0x0f, ADPCM-B 0xff).
;;; Registered at opcode slots 0x32 / 0x4d in the patched tools/nullsound/stream.s.

        .module nullsound

        .include "struct-fx.inc"
        .include "pipeline.inc"

        .area  CODE

;;; VOL_STEP_UP
;;; Raise the channel volume by a fixed step, stop the volume slide
;;; ------
;;; ix: state for channel
;;; [ hl ]: step
vol_step_u::
        ld      a, VOL16+1(ix)
        add     a, (hl)
        jr      c, _vol_step_max
        cp      VOL_CTX+SLIDE_MAX(ix)
        jr      c, _vol_step_set
        jr      z, _vol_step_set
_vol_step_max:
        ld      a, VOL_CTX+SLIDE_MAX(ix)
        jr      _vol_step_set

;;; VOL_STEP_DOWN
;;; Lower the channel volume by a fixed step, stop the volume slide
;;; ------
;;; ix: state for channel
;;; [ hl ]: step
vol_step_d::
        ld      a, VOL16+1(ix)
        sub     (hl)
        jr      nc, _vol_step_set
        xor     a
_vol_step_set:
        inc     hl
        res     BIT_FX_SLIDE, FX(ix)
        ld      VOL(ix), a
        ld      VOL16+1(ix), a
        ld      VOL16(ix), #0
        ;; reload configured vol at the next pipeline run
        set     BIT_LOAD_VOL, PIPELINE(ix)
        ld      a, #1
        ret
