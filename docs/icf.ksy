meta:
  id: icr6mem
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
    doc: pos 0x6b00 - 0x6bcf look like default band definition; read-only
    repeat: expr
    repeat-expr: 13

  - id: settings
    type: settings
    size: 64
    doc: pos 0x6bd0 - 0x6c0f

  - id: unknown_0x6c10
    size: 22
    doc: pos 0x6c10 - 0x6c1, always 0?

  - id: unknown_0x6c2
    type: u1
    doc: pos 0x6c2, related to settings or device state?

  - id: padding_0x6c27
    type: u1
    doc: pos 0x6c27, 0xff - padding?

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

  - id: unknown_0x6c54
    size: 2
    doc: 0x6c54 - 0x6c55  related to settings?

  - id: unknown_0x6c56
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
      # @0
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

      # @1
      - id: bank_pos
        type: u1
        doc: |
          position channel in bank; typical 0-99; but when bank
          is not set maybe 255

  scan_edge:
    seq:
      # 0
      - id: start
        type: u4le
        doc: freq * 3; hidden when not in acceptable range
      # 4
      - id: end
        type: u4le
        doc: freq * 3; hidden when not in acceptable range

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
      - id: unknown_b0
        type: b7
        doc: always 0b1111111

      # 1
      - id: unknown_b1
        type: u1
        doc: always 0xFF ?

      # 2
      - id: hidden2
        type: b1
        doc: the same as hidden1
      - id: unknown_b2
        type: b7
        doc: always 0b1111111

      # 3
      - id: unknown_b3
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
        doc: always 0? pad?
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
          channels use "auto" only for Japan model, not use "-" steps;
          for broadcast there is available additional 9k step; for aviation band
          - 8.33k

      # 4
      - id: unknown_b4_1
        type: b2
        doc: alawys 0; padding
      - id: duplex
        type: b2
        enum: duplex
      - id: unknown_b4_2
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
      - id: unknown_b7
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
      - id: unknown_b10
        type: b4
        doc: always 0 - paddign; probably canceller_freq lower 4 bits
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
      - id: unknown_0x6bd0
        size: 12
        doc: pos 0x6bd0; probably padding

      # @12
      - id: unknown_b12
        size: 1
        doc: pos 0x6bdc - 0

      # @13
      - id: unknown_b13
        type: b6
        doc: unused? padding?
      - id: func_dial_step
        type: b2

      # @14
      - id: unknown_b14
        type: b5
        doc: 0? unused? padding?
      - id: priority_scan_type
        type: b3
        enum: priority_scan_type

      # @15
      - id: unknown_b15
        type: b7
        doc: padding?
      - id: key_beep
        type: b1

      # @16
      - id: unknown_b16
        type: b2
        doc: padding?
      - id: beep_level
        type: b6
        doc: 0=Volume, levels 1-39

      # @17
      - id: unknown_b17
        type: b6
        doc: padding?
      - id: backlight
        type: b2

      # @18
      - id: unknown_b18
        type: b7
        doc: padding?
      - id: power_save
        type: b1

      # @19
      - id: unknown_b19
        type: b7
        doc: padding?
      - id: am_ant
        type: b1

      # @20
      - id: unknown_b20
        type: b7
        doc: padding?
      - id: fm_ant
        type: b1

      # @21
      - id: unknown_b21
        type: b7
        doc: padding?
      - id: set_expand
        type: b1

      # @22
      - id: unknown_b22
        type: b5
        doc: padding?
      - id: key_lock
        type: b2

      # @23
      - id: unknown_b23
        type: b7
        doc: padding?
      - id: dial_speed_up
        type: b1

      # @24
      - id: unknown_b24
        type: b7
        doc: padding?
      - id: monitor
        type: b1

      # @25
      - id: unknown_b25
        type: b5
        doc: padding?
      - id: auto_power_off
        type: b3

      # @26
      - id: unknown_b26
        type: b4
        doc: padding?
      - id: pause_timer
        type: b4

      # @27
      - id: unknown_b27
        type: b5
        doc: padding?
      - id: resume_timer
        type: b3

      # @28
      - id: unknown_b28
        type: b7
        doc: padding?
      - id: stop_beep
        type: b1

      # @29
      - id: unknown_b29
        type: b5
        doc: padding?
      - id: lcd_contrast
        type: b3

      # @30
      - id: wx_alert
        type: u1
        doc: 0=off, 1=on

      # @31
      - id: unknown_b31
        type: b7
        doc: padding?
      - id: af_filer_fm
        type: b1

      # @32
      - id: unknown_b32
        type: b7
        doc: padding?
      - id: af_filer_wfm
        type: b1

      # @33
      - id: unknown_b33
        type: b7
        doc: padding?
      - id: af_filer_am
        type: b1

      # @34
      - id: civ_address
        type: u1

      # @35
      - id: unknown_b35
        type: b5
        doc: padding?
      - id: civ_baud_rate
        type: b3

      # @36
      - id: unknown_b36
        type: b7
        doc: padding?
      - id: civ_transceive
        type: b1

      # @37
      - id: unknown_b37
        type: b7
        doc: padding?
      - id: charging_type
        type: b1

      # @38
      - id: padding_0x6bf6
        size: 9
        doc: padding? 9x 0xff

      # @47
      - id: scanning_band
        type: u1
        enum: scanning_band

      # @48
      - id: unknown_b48
        size: 2

      # @50
      - id: scanning_bank
        type: u1
        doc: 0=ALL; rest - banks num
        enum: scanning_bank

      # @51
      - id: unknown_b51
        type: u1

      # @52
      - id: unknown_b52_1
        type: b1
        doc: padding?
      - id: scan_enabled
        type: b1
      - id: unknown_b52_2
        type: b1
        doc: unused?
      - id: dial_function
        type: b1
      - id: mem_scan_priority
        type: b1
      - id: scan_mode
        type: b1
        doc: 0=VF0, 1=MEM
      - id: mem_display_type
        type: b2
        enum: mem_display_type

      # @53
      - id: unknown_b53_1
        type: b1
        doc: unknown, padding?
      - id: unprotected_frequency_flag
        type: b1
        doc: probably
      - id: autowrite_memory
        type: b1
      - id: keylock
        type: b1
      - id: program_skip_scan
        type: b1
      - id: unknown_b53_2
        type: b1
        doc: unused?
      - id: priority_scan
        type: b1
      - id: scan_direction
        type: b1
        doc: 0=down; 1=up

      # @54
      - id: scan_vfo_type
        type: u1
        enum: scan_vfo_type

      # @55
      - id: scan_mem_type
        type: u1
        enum: scan_mem_type

      # @56
      - id: mem_chan_data
        type: u2le
        doc: current memory selected; 0-1300 -> channel; 1300+ ????

      # @58
      - id: padding_0x6c0a
        type: u1
        doc: padding? 0xff

      # @59
      - id: wx_channel
        type: u1
        doc: wx channel - 0-9 -> 1-10

      # @60
      - id: unknown_b50x2
        size: 2

      # @62
      - id: padding_0x6c0e
        size: 2
        doc: 0xffff

  bank_links:
    seq:
      # @0
      - id: bank_link_1
        type: u1

      # @1
      - id: bank_link_2
        type: u1

      # @2
      - id: unknown_b2
        type: b2
        doc: padding?
      - id: bank_link_3
        type: b6

  band:
    # this is mostly guess; base 0x6b00
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
        doc: dscs

      # @11
      - id: unknown_b11
        type: u1
        doc: |
          unknown flags for offset & freq?; look like 4bit for offset
          and 4bit for frequency multpiler; not used

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
      - id: unknown_b13_1
        type: b1
        doc: padding?
      - id: vsc
        type: b1
      - id: canceller
        type: b2
      - id: unknown_b13_2
        type: b1
        doc: unused?
      - id: af
        type: b1
      - id: polarity
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

  scan_vfo_type:
    0: all
    1: band
    2: p_link0
    3: p_link1
    4: p_link2
    5: p_link3
    6: p_link4
    7: p_link5
    8: p_link6
    9: p_link7
    10: p_link8
    11: p_link9
    12: prog0
    13: prog1
    14: prog2
    15: prog3
    16: prog4
    17: prog5
    18: prog6
    19: prog7
    20: prog8
    21: prog9
    22: prog10
    23: prog11
    24: prog12
    25: prog13
    26: prog14
    27: prog15
    28: prog16
    29: prog17
    31: prog18
    32: prog19
    33: prog20
    34: prog21
    35: prog22
    36: prog23
    37: prog24

  scan_mem_type:
    0: m_all
    1: b_all
    2: b_link
    3: bank_a
    4: bank_b
    5: bank_c
    6: bank_d
    7: bank_e
    8: bank_f
    9: bank_g
    10: bank_h
    11: bank_i
    12: bank_j
    13: bank_k
    14: bank_l
    15: bank_m
    16: bank_n
    17: bank_o
    18: bank_p
    19: bank_q
    20: bank_r
    21: bank_t
    22: bank_u
    23: bank_w
    24: bank_y

  scanning_bank:
    0: m_all
    1: bank_a
    2: bank_b
    3: bank_c
    4: bank_d
    5: bank_e
    6: bank_f
    7: bank_g
    8: bank_h
    9: bank_i
    10: bank_j
    11: bank_k
    12: bank_l
    13: bank_m
    14: bank_n
    15: bank_o
    16: bank_p
    17: bank_q
    18: bank_r
    19: bank_t
    20: bank_u
    21: bank_w
    22: bank_y

  scanning_band:
    1: broadcast
    2: f5m
    3: f50m
    4: fm
    5: air
    6: f144m
    7: f300m
    8: f430m
    9: f800m
    10: f1200m

  priority_scan_type:
    0: priority_scan_off
    1: mem_ch
    2: mem_ch_beep
    5: mem_scan
    6: mem_scan_beep


  mem_display_type:
    0: freq
    1: b_name
    2: m_name
    3: chanl
