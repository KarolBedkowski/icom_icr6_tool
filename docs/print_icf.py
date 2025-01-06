#! /usr/bin/env python3
# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Parse and print content of ic-r6 memory using compiled ksy file.
"""
import sys

import icr6mem

def print_object(obj: object, prefix: object = "") -> None:
    if not hasattr(obj, "__dict__"):
        print(prefix, repr(obj))
        return

    print(prefix, obj.__class__.__name__, {
        k:v  for k, v in obj.__dict__.items()
        if k[0] != "_" and not isinstance(v, list)
    })

    for k, v in obj.__dict__.items():
        if k[0] != "_" and isinstance(v, list):
            for idx, o in enumerate(v):
                print_object(o, f"{k}[{idx}]")


if len(sys.argv) != 2:
    print("file name required")
else:
    mem = icr6mem.Icr6mem.from_file(sys.argv[1])
    print_object(mem)
