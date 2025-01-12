#! /usr/bin/env python3
# Copyright © 2025 Karol Będkowski <Karol Będkowski@kkomp>
#
# Distributed under terms of the GPLv3 license.

"""
Parse and print content of raw ic-r6 memory or compare two raw files
using compiled ksy file
"""
import sys
import icecream
icecream.install()

import icr6mem

def print_object(obj: object, prefix: object = "") -> None:
    if not hasattr(obj, "__dict__"):
        print(prefix, "=", repr(obj))
        return

    for k, v in sorted(obj.__dict__.items()):
        if k[0] == "_":
            continue

        if isinstance(v, list):
            for idx, vv in enumerate(v):
                print_object(vv, f"{prefix}:{k}[{idx}]")

        else:
            print_object(v, f"{prefix}:{k}")



def compare_objects(obj1: object, obj2: object, prefix: str = "") -> None:
    """Both objects have the same attributes, sizes etc, so this work. """
    if not hasattr(obj1, "__dict__"):
        if obj1 != obj2:
            print(f"{prefix}: {obj1!r}  -->  {obj2!r}")

        return

    for k, v1 in obj1.__dict__.items():
        if k[0] == "_":
            continue

        v2 = getattr(obj2, k, None)

        if isinstance(v1, list) and isinstance(v2, list):
            for idx, (o1, o2) in enumerate(zip(v1, v2, strict=True)):
                compare_objects(o1, o2, f"{prefix}:{k}[{idx}]")

        else:
            compare_objects(v1, v2, f"{prefix}:{k}")




if len(sys.argv) == 2:
    mem = icr6mem.Icr6mem.from_file(sys.argv[1])
    print_object(mem)

elif len(sys.argv) == 3:
    mem1 = icr6mem.Icr6mem.from_file(sys.argv[1])
    mem2 = icr6mem.Icr6mem.from_file(sys.argv[2])
    compare_objects(mem1, mem2)

else:
    print("on or two file names required")
