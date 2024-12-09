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
    doc: pos 0 - 0x513f

  - id: autowrite_channels
    type: channel
    size: 16
    repeat: expr
    repeat-expr: 200
    doc: pos 0x5140 - 0x5dbf

  - id: scan_edges
    type: scan_edge
    size: 16
    repeat: expr
    repeat-expr: 25
    doc: pos 0x5dc0 - 0x5f4f

  - id: padding_0x5f50
    size: 48
    doc: all values 0xff ? pos 0x5f50 - 0x5f7f

  - id: channels_flag
    type: channel_flag
    size: 2
    repeat: expr
    repeat-expr: 1300
    doc: pos 0x5f80 - 0x69a7

  - id: scan_edge_flags
    type: scan_edge_flags
    size: 4
    doc: something related to scan edgel 0x7F  / 0xFF; pos 0x69a8 - 0x6a0b
    repeat: expr
    repeat-expr: 25

  - id: padding_0x6a0c
    size: 4
    doc: not used? pos 0x6a0c - 0x6a0f

  - id: aw_channels_pos_hidden
    size: 1
    doc: probably bit set to 1 when aw channel is hidden; pos 0x6a10 - 0x6a28
    repeat: expr
    repeat-expr: 25

  - id: padding_0x6a29
    size: 7
    doc: always 0xff? not used? pos 0x6a29 - 0x6a2f

  - id: aw_channels_pos
    type: u1
    repeat: expr
    repeat-expr: 200
    doc: pos 0x6a30 - 0x6af7

  - id: padding_0x6af8
    size: 8
    doc: 8x 0xff (pad)?; unknown pos 0x6af8 - 0x6aff

  - id: bands
    type: band
    size: 16
    doc: device state? pos 0x6b00 - 0x6bcf look like default band definition; not changing
    repeat: expr
    repeat-expr: 13

  - id: settings
    type: settings
    size: 64
    doc: pos 0x6bd0 - 0x6c0f

  - id: unknown2_0x6c10
    size: 24
    doc: pos 0x6c10 - 0x6c27, related to settings or device state?

  - id: bank_links
    type: bank_links
    size: 3
    doc: pos 0x6c28 - 0x6c2a

  - id: padding_0x6c2b
    size: 1
    doc: 0xff  pos 0x6c2b unused?

  - id: scanlinks
    type: scanlink
    size: 4
    repeat: expr
    repeat-expr: 10
    doc: pos 0x6c2c - 0x6c53

  - id: unknown3_0x6c54
    size: 2
    doc: 0x6c54 - 0x6c55  related to settigns?

  - id: unknown4_0x6c56
    size: 1
    doc: 0x6c56  unused?

  - id: padding_0x6c57
    size: 169
    doc: always 0xff?; pos 0x6c57 - 0x6cff

  - id: comment
    type: str
    size: 16
    encoding: ASCII
    doc: pos 0x6d00 - 0x6d0f

  - id: bank_names
    type: bank_name
    size: 8
    repeat: expr
    repeat-expr: 22
    doc: pos 0x6d10 - 0x6dbf

  - id: scanlink_names
    type: scanlink_name
    size: 8
    repeat: expr
    repeat-expr: 10
    doc: pos 0x6dc0 - 0x6e0f

  - id: padding_0x6e10
    size: 64
    doc: always 0xff?; pos 0x6e10 - 0x6e4f

  - id: footer
    contents: 'IcomCloneFormat3'
    doc: pos 0x6e50 - 0x6e5f

types:
  channel_flag:
    seq:
      - id: hide_channel
        type: b1
      - id: skip_mode
        type: b1
        doc: 0 - S; 1 = P
      - id: skip_enabled
        type: b1
        doc: 0=disabled, 1=enabled
      - id: bank
        type: b5
        doc: bank number (0-22); 31 when bank is not set

      - id: bank_pos
        type: u1
        doc: position channel in bank
        valid:
          min: 0
          max: 99

  scan_edge:
    seq:
      # 0
      - id: start
        type: u4le
        doc: freq * 3
      # 4
      - id: end
        type: u4le
        doc: freq * 3

      # 8
      - id: mode
        type: b4
        enum: mode_scan_edge
      - id: tuning_step
        type: b4
        enum: steps
        doc: scan edge use addidtional "-" scan edge

      # 9
      - id: padding
        type: b2
        doc: always 0
      - id: attenuator
        type: b2
      - id: start_flags_freq
        type: b2
        doc: start flags_freq? probably not used by radio
        enum: freq_mul
      - id: end_flags_freq
        type: b2
        doc: end flags_freq? probably not used by radio
        enum: freq_mul

      # 10
      - id: name
        type: str
        encoding: ASCII
        size: 6
        eos-error: false

  scan_edge_flags:
    seq:
      # 0
      - id: hidden1
        type: b1
      - id: unknown1
        type: b7
        doc: always 0b1111111

      # 1
      - id: unknown2
        type: u1
        doc: always 0xFF ?

      # 2
      - id: hidden2
        type: b1
        doc: the same as unknown1
      - id: unknown3
        type: b7
        doc: always 0b1111111

      # 3
      - id: unknown4
        type: u1
        doc: always 0xFF ?

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
        doc: bitmap for banks Y->A with 7 bit padding in last byte (0b11111110)

  channel:
    seq:
      # 0
      - id: freq0
        type: u1
        doc: lsb; complete freq=(freq3 << 16) | (freq2 << 8) | freq3

      # 1
      - id: freq1
        type: u1

      # 2
      - id: flags_offset
        type: b2
        doc: |
          2 bits for offset
          8.333k step is available only for air band
          If offset is 0 (dup flag is ignored) - use the same divisor
          as freq_mul.
          If offset > 0 - try:
            - use common divisor for offset and freq
            - use 9k divisor if available
            - use min useful divisor (5k, 6.25k, 8.333k)
          If any divisor can be used - round offset to value when any divisor
          can be used.
        enum: freq_mul
      - id: flags_freq
        type: b2
        doc: |
          2 bits for freq;
          8333.333 step is available only for air band
          if offset > 0 - try find common divisor; otherwise try:
            - use 9k divisor if applicable
            - find minimal useful divisor (5k, 6.25k, 8.333k)
          If any divisor can be used - round frequency to nearest value for
          which any divisor can be used.
        enum: freq_mul
      - id: flag_unknown
        type: b2
        doc: always 0?
      - id: freq2
        type: b2
        doc: msb; 1 bit usable

      # 3
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
        doc: |
          channels not use "auto" and "-" steps; for broadcast there
          is available additional 9k step; for aviation band - 8.33k

      # 4
      - id: unknown1
        type: b2
        doc: alawys 0
      - id: duplex
        type: b2
        enum: duplex
      - id: unknown3
        type: b1
        doc: |
          1 for invalid channels?  must be 0 - when enabled channel
          and tone_mode
      - id: tone_mode
        type: b3
        enum: tone_mode
        doc: only in fm mode

      # 5-6
      - id: offset
        type: u2le

      # 7
      - id: unknown2
        type: b2
        doc: 1 for invalid channels?  must be 0 when enabled channel?
      - id: tsql_freq
        type: b6

      # 8
      - id: polarity
        type: b1
        enum: polarity
      - id: dscs_code
        type: b7

      # 9-10
      - id: canceller_freq
        type: b9
        doc: range 30-300 -> 300Hz-3kHz; EU 228=2280Hz
      - id: unknown4
        type: b4
        doc: always 0 - paddign
      - id: vcs
        type: b1
        doc: enabling vcs - disable canceller
      - id: canceller
        type: b2
        doc: enabling canceller - disable vcs

      # 11-15
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
        doc: pos 0x6bd0 ; first byte related to market

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
        doc: somthing related to market

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

  band:
    # this is mostly guess
    seq:
      - id: freq
        type: u4le
        doc: band end frequency (freq * 3)

      # @4
      - id: offset
        type: u4le
        doc: offset (freq * 3)

      # @8
      - id: tuning_step
        type: u1
        enum: steps

      # @9
      - id: tsql_freq
        type: u1

      # @10
      - id: dscs_code
        type: u1
        doc: with polarity? rather not

      # @11
      - id: unknown6
        type: u1
        doc: unknown flags for offset & freq?

      # @12
      - id: duplex
        type: b2
        doc: duplex?
      - id: mode
        type: b2
        enum: mode
      - id: tone_mode
        type: b4
        doc: tone mode?

      # @13
      - id: unknown8
        type: b1
      - id: vsc
        type: b1
      - id: canceller
        type: b2
      - id: unknown8a
        type: b1
      - id: polarity
        type: b1
      - id: af
        type: b1
      - id: attenuator
        type: b1

      # @14
      - id: canceller_freq
        type: u2le

enums:
  mode:
    0: fm
    1: wfm
    2: am
    3: mode_auto

  mode_scan_edge:
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
    0: normal
    1: reverse
