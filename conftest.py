# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""

"""
import logging
import sys
from contextlib import suppress

with suppress(ImportError):
    import icecream

    icecream.install()

try:
    import snoop

    snoop.install()
except ImportError:
    pass


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
