        .include "helpers.inc"
        .include "samples.inc"
        .include "snd_commands.inc"
        .area   CODE
cmd_jmptable::
        jp      snd_command_unused                    ; 0
        jp      snd_command_01_prepare_for_rom_switch ; 1
        jp      stream_stop                           ; 2
        jp      snd_command_03_reset_driver           ; 3
        generated_commands_jmptable_entries           ; 4.. music, then sfx
        init_unused_cmd_jmptable
        generated_commands_implementation
