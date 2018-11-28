#!/usr/bin/env python3

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
