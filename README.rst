Icom IC-R6 Manager  1.x
========================

Simple TK application for manage Icom IC-R6 scanner memory.

Features:

- Load and save ICF file
- Clone data from and to radio
- Edit channels, banks, scan links / edges; reordering, CTRL-C/CTRL-V
  operations.
- Display autowrite channels, clear entries.
- Change radio settings
- Export data in csv format
- Find channels by frequency, name; find duplicated channels.

Additional tools are available in included cli tool (icom_icr6_cli).


Missing:

- detect radio version; there is some workarounds.


Cloning to / from radio sometimes ends with error (OutOfSync, Checksum error).
This problem (in my case) are related to home-made cable and repeat operation
usually help.
Clone to radio sometimes require restart device to use new settings.


WARNING
-------
This is software is alpha state. Tested only on EUR version of IR-R6, but
should support other versions as well.

Cloning from and to device seems to be quite safe operation. In my test
sending broken data to radio cause at least memory reset.

But I not responsible if someone damage/brick own device using this software.
Using at on own risk.


Requirements
-------------
- Python 3.11+ with Tkinter
- tksheet 7+
- pyserial


Installation
------------

``pip install .``

or

``pipx install .``


Using
-----

GUI:

``icom_icr6 <optional icf filename>``

CLI:

``icom_icr6_cli <commands``.

Run with ``-h`` for available commands and options.


Credits
-------
Based on Chirp project (https://chirpmyradio.com) and work
https://github.com/jbradsha/chirp/


Licence
-------

Copyright (c) Karol Będkowski, 2024-2025
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

For details please see COPYING file.


.. vim:spell spelllang=en:
