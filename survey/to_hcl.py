#!/usr/bin/env python3

"""
Copyright (c) 2018-2021 Matthew Petroff

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import argparse
import csv
import platform
import numpy as np
import colorspacious

parser = argparse.ArgumentParser(
    description="Sort color sets by HCL (hue, chroma, luminance) [CAM02-UCS based].",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "input", metavar="INPUT", help="Color sets to be sorted (space separated)"
)
args = parser.parse_args()

with open(args.input) as csv_file:
    with open(args.input.split(".")[0] + "_hcl_sorted.txt", "w") as outfile:
        # Copy header rows
        outfile.write(csv_file.readline())
        outfile.write(csv_file.readline())
        outfile.write(csv_file.readline())
        # Record environment
        outfile.write("# Python " + platform.sys.version.replace("\n", "") + "\n")
        outfile.write(
            f"# NumPy {np.__version__}, Colorspacious {colorspacious.__version__}\n"
        )
        csv_reader = csv.reader(csv_file, delimiter=" ")
        for row in csv_reader:
            row = [i.strip() for i in row]
            rgb = [(int(i[:2], 16), int(i[2:4], 16), int(i[4:], 16)) for i in row]
            jab = [colorspacious.cspace_convert(i, "sRGB255", "CAM02-UCS") for i in rgb]
            hcl = np.array(
                [
                    [np.arctan2(i[2], i[1]), np.sqrt(i[1] ** 2 + i[2] ** 2), i[0]]
                    for i in jab
                ]
            )
            new_row = " ".join(np.array(row)[np.lexsort(hcl[:, ::-1].T)])
            outfile.write(new_row + "\n")
