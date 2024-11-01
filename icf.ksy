meta:
  id: icf
  title: icf file
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

  - id: channels_flag
    type: channel_flag
    size: 2
    repeat: expr
    repeat-expr: 1300

  - id: unknown2
    size: 136

  - id: aw_channels_pos
    type: u1
    repeat: expr
    repeat-expr: 200

  - id: unknown2a
    size: 216

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
    size: 172

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

  - id: unknown4
    size: 64

  - id: footer
    contents: 'IcomCloneFormat3'

types:
  channel_flag:
    seq:
      - id: hide_channel
        type: b1
      - id: skip
        type: b2
      - id: bank
        type: b4

      - id: bank_pos
        type: u1

  scan_edge:
    seq:
      - id: start
        type: u4
      - id: end
        type: u4

      - id: disabled
        type: b1
      - id: mode
        type: b3
      - id: ts
        type: b4

      - id: unknown1
        type: b2
      - id: attn
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
        type: u2

  scanlink_name:
    seq:
      - id: name
        type: str
        size: 6
        encoding: ASCII
      - id: padding
        type: u2

  scanlink:
    seq:
      - id: map
        type: u4

  channel:
    seq:
      - id: freq0
        type: u1
        doc: lsb

      - id: freq1
        type: u1

      - id: flags
        type: b4
        doc: 2 bits for offset and 2 bits for freq
      - id: flag_unknown
        type: b2
        doc: probably always 0 - mayby 2 bits freq2
      - id: freq2
        type: b2
        doc: msb

      - id: af
        type: b1
      - id: attn
        type: b1
      - id: mode
        type: b2
      - id: ts
        type: b4

      - id: unknown1
        type: b2
      - id: duplex
        type: b2
      - id: unknown3
        type: b1
      - id: tone_mode
        type: b3

      - id: offset
        type: u2

      - id: unknown2
        type: b2
      - id: tsql_freq
        type: b6

      - id: polarity
        type: b1
      - id: dsc
        type: b7

      - id: canceller_freq
        type: b9
      - id: unknown4
        type: b4
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

    instances:
      freq:
        value: ((freq2 << 16) | (freq1 << 8) | freq0) * ((flags == 0) ? 5000 : (flags == 20 ? 6550 : (flags == 40 ? 8333.333 : 9000)))


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
