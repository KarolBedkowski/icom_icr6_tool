meta:
  id: icr6
  title: icom ic-r6 memory map
  endian: be
  bit-endian: be
seq:
  - id: channels
    type: channel
    size: 16
    repeat: expr
    repeat-expr: 1300

  - id: autowrite_channels
    type: channel
    size: 16
    repeat: expr
    repeat-expr: 200

  - id: scan_edges
    type: scan_edge
    size: 16
    repeat: expr
    repeat-expr: 25

  - id: unknown1
    size: 48
    doc: 0xff ?

  - id: channels_flag
    type: channel_flag
    size: 2
    repeat: expr
    repeat-expr: 1300

  - id: unknown2
    size: 121
    doc: 0x7F  / 0xFF

  - id: unknown2a
    size: 15

  - id: aw_channels_pos
    type: u1
    repeat: expr
    repeat-expr: 200

  - id: unknown2b
    size: 216
    doc: 8x 0xff (pad) ?; device state?

  - id: settings
    type: settings
    size: 64

  - id: unknown3
    size: 24

  - id: bank_links
    type: bank_links
    size: 3

  - id: unknown3b
    size: 1

  - id: scanlinks
    type: scanlink
    size: 4
    repeat: expr
    repeat-expr: 10

  - id: unknown3a
    size: 3

  - id: unknown3aconst
    size: 169
    doc: always 0xff?

  - id: comment
    type: str
    size: 16
    encoding: ASCII

  - id: bank_names
    type: bank_name
    size: 8
    repeat: expr
    repeat-expr: 22

  - id: scanlink_names
    type: scanlink_name
    size: 8
    repeat: expr
    repeat-expr: 10

  - id: unknown4const
    size: 64
    doc: always 0xff?

  - id: footer
    contents: 'IcomCloneFormat3'

types:
  channel_flag:
    seq:
      - id: hide_channel
        type: b1
      - id: skip
        type: b2
        doc: skips - none, S, none, P
      - id: bank
        type: b4
        doc: bank number (0-22); 31 when bank is not set

      - id: bank_pos
        type: u1
        doc: position channel in bank
        valid:
          min: 0
          max: 99

  scan_edge:
    seq:
      - id: start
        type: u4le
        doc: freq * 3
      - id: end
        type: u4le
        doc: freq * 3

      - id: disabled
        type: b1
      - id: mode
        type: b3
        enum: mode
      - id: tuning_step
        type: b4
        enum: steps

      - id: unknown1
        type: b2
      - id: attenuator
        type: b2
      - id: unknown2
        type: b4

      - id: name
        type: str
        encoding: ASCII
        size: 6
        eos-error: false

  bank_name:
    seq:
      - id: name
        type: str
        size: 6
        encoding: ASCII
      - id: padding
        type: u2le

  scanlink_name:
    seq:
      - id: name
        type: str
        size: 6
        encoding: ASCII
      - id: padding
        type: u2le

  scanlink:
    seq:
      - id: map
        type: u4be
        doc: bitmap for banks Y->A

  channel:
    seq:
      - id: freq0
        type: u1
        doc: lsb

      - id: freq1
        type: u1

      - id: flags_offset
        type: b2
        doc: 2 bits for offset
        enum: freq_mul
      - id: flags_freq
        type: b2
        doc: 2 bits for freq
        enum: freq_mul
      - id: flag_unknown
        type: b2
        doc: always 0?
      - id: freq2
        type: b2
        doc: msb

      - id: af
        type: b1
      - id: attenuator
        type: b1
      - id: mode
        type: b2
        enum: mode
      - id: tuning_step
        type: b4
        enum: steps

      - id: unknown1
        type: b2
        doc: wlawys 0??
      - id: duplex
        type: b2
        enum: duplex
      - id: unknown3
        type: b1
        doc: 1 for invalid channels?
      - id: tone_mode
        type: b3
        enum: tone_mode

      - id: offset
        type: u2le

      - id: unknown2
        type: b2
      - id: tsql_freq
        type: b6

      - id: polarity
        type: b1
        enum: polarity
      - id: dscs_code
        type: b7

      - id: canceller_freq
        type: b9
      - id: unknown4
        type: b4
        doc: always 0
      - id: vcs
        type: b1
      - id: canceller
        type: b2

      - id: name_pad
        type: b4
      - id: name
        type: b6
        repeat: expr
        repeat-expr: 6


  settings:
    seq:
      - id: unknown0
        size: 13

      # @13
      - id: unknown1
        type: b6
      - id: func_dial_step
        type: b2

      # @14
      - id: unknown2
        size: 1

      # @15
      - id: unknown3
        type: b7
      - id: key_beep
        type: b1

      # @16
      - id: unknown4
        type: b2
      - id: beep_level
        type: b6

      # @17
      - id: unknown4a
        type: b6
      - id: backlight
        type: b2

      # @18
      - id: unknown5
        type: b7
      - id: power_save
        type: b1

      # @19
      - id: unknown6
        type: b7
      - id: am_ant
        type: b1

      # @20
      - id: unknown7
        type: b7
      - id: fm_ant
        type: b1

      # @21
      - id: unknown7a
        type: b7
      - id: set_expand
        type: b1

      # @22
      - id: unknown7b
        type: b5
      - id: key_lock
        type: b2

      # @23
      - id: unknown7c
        type: b7
      - id: dial_speed_up
        type: b1

      # @24
      - id: unknown7d
        type: b7
      - id: monitor
        type: b1

      # @25
      - id: unknown8
        type: b5
      - id: auto_power_off
        type: b3

      # @26
      - id: unknown8b
        type: b4
      - id: pause_timer
        type: b4

      # @27
      - id: unknown8c
        type: b5
      - id: resume_timer
        type: b3

      # @28
      - id: unknown8d
        type: b7
      - id: stop_beep
        type: b1

      # @29
      - id: unknown8a
        type: b5
      - id: lcd_contrast
        type: b3

      # @30
      - id: unknown8e
        size: 1

      # @31
      - id: unknown8f
        type: b7
      - id: af_filer_fm
        type: b1

      # @32
      - id: unknown8f1
        type: b7
      - id: af_filer_wfm
        type: b1

      # @33
      - id: unknown8g
        type: b7
      - id: af_filer_am
        type: b1

      # @34
      - id: civ_address
        type: u1

      # @35
      - id: unknown9
        type: b5
      - id: civ_baud_rate
        type: b3

      # @36
      - id: unknown10
        type: b7
      - id: civ_transceive
        type: b1

      # @37
      - id: unknown11a
        type: b7
      - id: charging_type
        type: b1

      # @38
      - id: unknown11
        size: 14

      # @52
      - id: unknown12
        type: b3
      - id: dial_function
        type: b1
      - id: unknown13
        type: b2
      - id: mem_display_type
        type: b2

      # @53
      - id: unknown14a
        type: b4
      - id: program_skip_scan
        type: b1
      - id: unknown14b
        type: b3

      # @54
      - id: unknown14
        size: 10

  bank_links:
    seq:
      # @60
      - id: bank_link_1
        type: u1

      # @61
      - id: bank_link_2
        type: u1

      # @62
      - id: unknown14c
        type: b2
      - id: bank_link_3
        type: b6

enums:
  mode:
    0: fm
    1: wfm
    2: am
    3: auto
    4: not_set

  steps:
    0: step_5
    1: step_6_25
    2: step_8_333333
    3: step_9
    4: step_10
    5: step_12_5
    6: step_15
    7: step_20
    8: step_25
    9: step_30
    10: step_50
    11: step_100
    12: step_125
    13: step_200
    14: step_auto

  freq_mul:
    0: freq_mul_5000
    1: freq_mul_6250
    2: freq_mul_8333
    3: freq_mul_9000

  duplex:
    0: none
    1: minus
    2: plus
    3: unk

  tone_mode:
    0: none
    1: tsql
    2: tsql_r
    3: dtcs
    4: dtcs_r

  polarity:
    0: reverse
    1: normal
