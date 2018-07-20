#!/usr/bin/env python3

import colorsys
import csv
import numpy as np

with open('colors.csv') as csv_file:
    csv_reader = csv.reader(csv_file)
    for row in csv_reader:
        row = [i.strip() for i in row]
        rgb = [(int(i[1:3], 16), int(i[3:5], 16), int(i[5:], 16)) for i in row]
        hsv = np.array([colorsys.rgb_to_hsv(*i) for i in rgb])
        new_row = ', '.join(np.array(row)[np.lexsort(hsv[:, ::-1].T)])
        print(new_row)
