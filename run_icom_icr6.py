#! /usr/bin/env python3
# Copyright © 2024 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""

"""
import icecream
icecream.install()

try:
    import stackprinter

    stackprinter.set_excepthook(style="color",
                                suppressed_paths=[r"lib/python.*/site-packages/"])
except ImportError:
    try:
        from rich.traceback import install

        install()
    except ImportError:
        pass
try:
    import icecream

    icecream.install()
    icecream.ic.configureOutput(includeContext=True)

    import traceback

    def ic_stack(*args, **kwargs):
        ic("\n".join(traceback.format_stack()[:-2]), *args, **kwargs)

    import inspect

    class ShiftedIceCreamDebugger(icecream.IceCreamDebugger):
        def format(self, *args):
            # one more frame back
            call_frame = inspect.currentframe().f_back.f_back
            return self._format(call_frame, *args)

    sic = ShiftedIceCreamDebugger()

    def ic_trace(func):
        def wrapper(*args, **kwargs):
            sic(func, args, kwargs)
            res = func(*args, **kwargs)
            sic(func, res)
            return res

        return wrapper

    import builtins

    builtins.ic_stack = ic_stack
    builtins.ic_trace = ic_trace

except ImportError:  # Graceful fallback if IceCream isn't installed.
    pass

import typing as ty

try:
    from typeguard import install_import_hook

    install_import_hook("icom_icr6")
    print("WARN! typeguard hook installed")

    ty.TYPE_CHECKING = True

    import typeguard._checkers as checkers
    checkers.check_protocol = None  # agronholm/typeguard#465

except ImportError as err:
    print(err)


from icom_icr6 import main

main()
