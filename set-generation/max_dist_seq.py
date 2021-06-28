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
import time
import platform
import numpy as np
import numba
import color_conversions


#
# Configuration
#

parser = argparse.ArgumentParser(
    description="Generate maximally-distinct color cycle using sequential search.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "--num-colors", default=11, type=int, help="Number of colors in set"
)
parser.add_argument(
    "--cvd-severity",
    default=100,
    type=int,
    help="Severity percentage for CVD simulation",
)
parser.add_argument(
    "--min-j", default=40, type=int, help="Minimum color lightness (J')"
)
parser.add_argument(
    "--max-j", default=90, type=int, help="Maximum color lightness (J')"
)
args = parser.parse_args()

NUM_COLORS = args.num_colors
CVD_SEVERITY = args.cvd_severity
MIN_J = args.min_j
MAX_J = args.max_j

OUT_FILE = f"maxdistinct_nc{NUM_COLORS}_cvd{CVD_SEVERITY}_minj{MIN_J}_maxj{MAX_J}"


#
# Generate list of colors
#

# Since CAM02-UCS conversions are computationally expensive, but the
# 16.8 million possible 8-bit RGB colors easily fit in memory, we precompute
# the list of colors for normal color vision and three types of color vision
# deficiency.


@numba.njit
def calc_jab_colors(include_white):
    """
    Calculates CAM02-UCS colors for all 8-bit RGB colors with $J' \in [J'_{min}, J'_{max}]$.
    Also, optionally include white (#ffffff).
    """
    rgb_colors = np.empty((256 ** 3, 3), dtype=np.uint8)
    jab_colors = np.empty((256 ** 3, 3), dtype=np.float32)
    deut_jab_colors = np.empty((256 ** 3, CVD_SEVERITY, 3), dtype=np.float32)
    prot_jab_colors = deut_jab_colors.copy()
    trit_jab_colors = deut_jab_colors.copy()
    c = 0
    for i in range(256 ** 3):
        r = i % 256
        g = (i // 256) % 256
        b = i // (256 ** 2)
        rgb_linear = color_conversions.sRGB1_to_sRGB1_linear(
            np.array((r / 255, g / 255, b / 255))
        )
        jab = color_conversions.rgb_linear_to_jab(rgb_linear)
        if (jab[0] >= MIN_J and jab[0] <= MAX_J) or (
            include_white and i == 256 ** 3 - 1
        ):
            rgb_colors[c] = np.array((r, g, b))
            jab_colors[c] = jab
            for s in range(1, CVD_SEVERITY + 1):
                deut_jab_colors[c, s - 1] = color_conversions.rgb_linear_to_jab(
                    color_conversions.CVD_forward_deuteranomaly(rgb_linear, s)
                )
                prot_jab_colors[c, s - 1] = color_conversions.rgb_linear_to_jab(
                    color_conversions.CVD_forward_protanomaly(rgb_linear, s)
                )
                trit_jab_colors[c, s - 1] = color_conversions.rgb_linear_to_jab(
                    color_conversions.CVD_forward_tritanomaly(rgb_linear, s)
                )
            c += 1
    rgb_colors = rgb_colors[:c]
    jab_colors = jab_colors[:c]
    deut_jab_colors = deut_jab_colors[:c]
    prot_jab_colors = prot_jab_colors[:c]
    trit_jab_colors = trit_jab_colors[:c]
    return rgb_colors, jab_colors, deut_jab_colors, prot_jab_colors, trit_jab_colors


t = time.time()
RGB_COLORS, JAB_COLORS, DEUT_JAB_COLORS, PROT_JAB_COLORS, TRIT_JAB_COLORS = calc_jab_colors(
    True
)
print(f"Color list generated in {time.time() - t}s")


#
# Generate color cycle
#


@numba.njit
def gen_cycle():
    """Find optimal order using sequential method, starting with white."""

    jab_colors = np.empty((NUM_COLORS, 3), dtype=np.float32)
    deut_jab_colors = np.empty((NUM_COLORS, CVD_SEVERITY, 3), dtype=np.float32)
    prot_jab_colors = deut_jab_colors.copy()
    trit_jab_colors = deut_jab_colors.copy()
    rgb_colors = np.empty((NUM_COLORS, 3), dtype=np.uint8)
    min_dists = np.empty(NUM_COLORS, dtype=np.float32)

    # Start with white
    rgb_colors[0] = RGB_COLORS[-1]
    jab_colors[0] = JAB_COLORS[-1]
    deut_jab_colors[0] = DEUT_JAB_COLORS[-1]
    prot_jab_colors[0] = PROT_JAB_COLORS[-1]
    trit_jab_colors[0] = TRIT_JAB_COLORS[-1]
    min_dists[0] = 100

    for i in range(1, NUM_COLORS):
        # Find remaining valid colors
        max_idx = 0
        max_dist = 0
        for j in range(RGB_COLORS.shape[0]):
            dist = 1000
            for k in range(i):
                dist = min(
                    dist, color_conversions.cam02de(JAB_COLORS[j], jab_colors[k])
                )
                for s in range(CVD_SEVERITY):
                    dist = min(
                        dist,
                        color_conversions.cam02de(
                            DEUT_JAB_COLORS[j, s], deut_jab_colors[k, s]
                        ),
                    )
                    dist = min(
                        dist,
                        color_conversions.cam02de(
                            PROT_JAB_COLORS[j, s], prot_jab_colors[k, s]
                        ),
                    )
                    dist = min(
                        dist,
                        color_conversions.cam02de(
                            TRIT_JAB_COLORS[j, s], trit_jab_colors[k, s]
                        ),
                    )
            if dist > max_dist:
                max_dist = dist
                max_idx = j
        rgb_colors[i] = RGB_COLORS[max_idx]
        jab_colors[i] = JAB_COLORS[max_idx]
        deut_jab_colors[i] = DEUT_JAB_COLORS[max_idx]
        prot_jab_colors[i] = PROT_JAB_COLORS[max_idx]
        trit_jab_colors[i] = TRIT_JAB_COLORS[max_idx]
        min_dists[i] = max_dist

    return rgb_colors, min_dists


def gen_color_names(colors):
    """
    Convert RGB values into a hexadecimal color string.
    """
    color_names = []
    for color in colors:
        name = "{:02x}{:02x}{:02x}".format(*color)
        color_names.append(name)
    return color_names


t = time.time()
result = gen_cycle()
print(f"Color cycle generated in {time.time() - t}s")

with open(OUT_FILE + ".txt", "w") as out:
    out.write(f"# {OUT_FILE}\n")
    out.write("# Python " + platform.sys.version.replace("\n", "") + "\n")
    out.write(f"# NumPy {np.__version__}, Numba {numba.__version__}\n")
    color_names = gen_color_names(result[0])
    for i in range(NUM_COLORS):
        out.write(f"{color_names[i]} {result[1][i]:.3f}\n")
