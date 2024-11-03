Icom IC-R6 Manager  [WIP]
=========================


Simple TK application for manage Icom IC-R6 scanner memory.

Features:
- load and save ifc file
- clone data from and to radio
- edit channels, banks, scan links / edges
- display autowrite channels
- change settings


WARNING
-------
This is software i alfa state. Tested only on EUR version of IR-R6.

Cloning from and to device seems to be quite safe operation. In my test
sending broken data to radio cause at least memory reset.

But I not responsible if someone damage/brick own device using this software.
Using at on own risk.


Requirements
-------------
- Python 3.11+
- Tkinter
- pyserial


Credits
-------
Based on Chirp project (https://chirpmyradio.com) and work
https://github.com/jbradsha/chirp/


Licence
-------

Copyright (c) Karol Będkowski, 2024
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

For details please see COPYING file.


.. vim:spell spelllang=en:
