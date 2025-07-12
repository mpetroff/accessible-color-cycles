#!/usr/bin/env python3

import numpy as np

np.random.seed(8452034)

angles = np.random.uniform(0, 360, 56)
order = np.random.permutation(56)
plotnum = np.random.randint(0, 2, 56)

output = "const angles = ["
output += ", ".join(f"{i:.1f}" for i in angles)
output += "];\n"

output += "const order = ["
output += ", ".join(str(i) for i in order)
output += "];\n"

output += "const plotnum = ["
output += ", ".join(str(i) for i in plotnum)
output += "];"

print(output)
