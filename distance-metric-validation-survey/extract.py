#!/usr/bin/env python3

"""
Extract Wang et al. (2019) data points.

Matthew Petroff, 2024

SVG was created by opening the page of Wang et al. (2019) with Fig. 9 on it in
Inkscape, deleting everything except for the Fig. 9 subplots, grouping only by
those subplots, scaling each group to 100px, making the document size
100px x 100px, centering the subplots, and exporting as an optimized SVG.
"""

import numpy as np

# Read SVG and group into the five subplots
with open("extract.svg") as infile:
    lines = infile.readlines()

lines = lines[3456:4616]
lines = [l.strip() for l in lines]
groups = [lines[i * 232 : (i + 1) * 232] for i in range(5)]


# Extract coordinates and colors
matrices = []
colors = []
for g in groups:
    matrices.append([])
    colors.append([])
    for i in range(1, 231):
        matrix = g[i].split("matrix(")[1].split(")")[0].split()
        matrices[-1].append([float(m) for m in matrix])
        colors[-1].append(g[i].split('fill="')[1].split('"')[0])

coords = np.mean([[e[4:] for e in m] for m in matrices], axis=0).T

colors6 = sorted(set(colors[0]))
colors7 = colors6 + list(set(colors6) ^ set(colors[1]))
colors8 = colors7 + list(set(colors7) ^ set(colors[3]))

color_idx = [[colors8.index(c) for c in color] for color in colors]

# Export for future reference
np.savez_compressed("points.npz", coords=coords, category=color_idx)

# Export for web-based survey
cat = np.array(color_idx).T
coords /= 100
coords -= 0.5
r = np.sqrt(coords[0] ** 2 + coords[1] ** 2)
theta = np.arctan2(coords[1], coords[0])
js = "const points = [\n"
for i in range(coords.shape[1]):
    js += (
        "  {"
        + f"r: {r[i]:.3f}, theta: {theta[i]:.3f}, cat: [{', '.join(map(str, cat[i]))}]"
        + "},\n"
    )
js = js[:-2] + "\n];"
with open("points.js", "w") as outfile:
    outfile.write(js)
