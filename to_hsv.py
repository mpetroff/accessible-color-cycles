#!/usr/bin/env python3

import colorsys
import csv
import numpy as np
import argparse

parser = argparse.ArgumentParser(
    description="Sort color sets by HSV.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument('input', metavar='INPUT', help='Color sets to be sorted (space separated)')
args = parser.parse_args()

with open(args.input) as csv_file:
    with open(args.input.split('.')[0] + '_hsv_sorted.txt', 'w') as outfile:
        outfile.write(csv_file.readline())  # Copy header rows
        outfile.write(csv_file.readline())
        outfile.write(csv_file.readline())
        csv_reader = csv.reader(csv_file, delimiter=' ')
        for row in csv_reader:
            row = [i.strip() for i in row]
            rgb = [(int(i[:2], 16), int(i[2:4], 16), int(i[4:], 16)) for i in row]
            hsv = np.array([colorsys.rgb_to_hsv(*i) for i in rgb])
            new_row = ' '.join(np.array(row)[np.lexsort(hsv[:, ::-1].T)])
            outfile.write(new_row + '\n')
