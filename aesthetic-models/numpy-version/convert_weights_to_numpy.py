#!/usr/bin/env python3

"""
Copyright (c) 2021 Matthew Petroff

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

import gzip
import os
import shutil
import numpy as np
import h5py

ENSEMBLE_COUNT = 100

# Set model
weights = {"ensemble_count": ENSEMBLE_COUNT}
for i in range(ENSEMBLE_COUNT):
    with gzip.open(f"../weights/set_model_weights_{i:03d}.h5.gz", "rb") as infile:
        weight_file = h5py.File(infile, "r")
        for key in ["l1j", "l2j", "l1a", "l2a", "l1b", "l2b"]:
            kernel = np.array(weight_file[key][key]["kernel:0"])
            bias = np.array(weight_file[key][key]["bias:0"])
            weights[key[1:] + f"_{i:03d}_kernel"] = kernel
            weights[key[1:] + f"_{i:03d}_bias"] = bias
        for key in ["l3j", "l4j", "l5j", "l3a", "l4a", "l5a", "l3b", "l4b", "l5b"]:
            depthwise_kernel = np.array(weight_file[key][key]["depthwise_kernel:0"])
            pointwise_kernel = np.array(weight_file[key][key]["pointwise_kernel:0"])
            bias = np.array(weight_file[key][key]["bias:0"])

            # Adjust format
            depthwise_kernel = np.flipud(depthwise_kernel)
            depthwise_kernel = np.transpose(depthwise_kernel, (1, 2, 0))
            pointwise_kernel = np.flipud(pointwise_kernel)
            pointwise_kernel = np.transpose(pointwise_kernel, (1, 2, 0))
            bias = np.expand_dims(bias, 0).T

            weights[key[1:] + f"_{i:03d}_depthwise_kernel"] = depthwise_kernel
            weights[key[1:] + f"_{i:03d}_pointwise_kernel"] = pointwise_kernel
            weights[key[1:] + f"_{i:03d}_bias"] = bias

npz_filename = "set_model_weights.npz"
np.savez(npz_filename, **weights)
# Recompressing the NPZ file reduces its file size considerably since it contains
# many small arrays, which are otherwise only compressed separately.
with open(npz_filename, "rb") as infile:
    with gzip.open(npz_filename + ".gz", "wb") as outfile:
        shutil.copyfileobj(infile, outfile)
os.remove(npz_filename)


# Cycle model
weights = {"ensemble_count": ENSEMBLE_COUNT}
for i in range(ENSEMBLE_COUNT):
    with gzip.open(f"../weights/cycle_model_weights_{i:03d}.h5.gz", "rb") as infile:
        weight_file = h5py.File(infile, "r")
        for key in ["l1", "l2"]:
            kernel = np.array(weight_file[key][key]["kernel:0"])
            bias = np.array(weight_file[key][key]["bias:0"])
            weights[key[1:] + f"_{i:03d}_kernel"] = kernel
            weights[key[1:] + f"_{i:03d}_bias"] = bias
        for key in ["l3", "l4", "l5"]:
            depthwise_kernel = np.array(weight_file[key][key]["depthwise_kernel:0"])
            pointwise_kernel = np.array(weight_file[key][key]["pointwise_kernel:0"])
            bias = np.array(weight_file[key][key]["bias:0"])

            # Adjust format
            depthwise_kernel = np.flipud(depthwise_kernel)
            depthwise_kernel = np.transpose(depthwise_kernel, (1, 2, 0))
            pointwise_kernel = np.flipud(pointwise_kernel)
            pointwise_kernel = np.transpose(pointwise_kernel, (1, 2, 0))
            bias = np.expand_dims(bias, 0).T

            weights[key[1:] + f"_{i:03d}_depthwise_kernel"] = depthwise_kernel
            weights[key[1:] + f"_{i:03d}_pointwise_kernel"] = pointwise_kernel
            weights[key[1:] + f"_{i:03d}_bias"] = bias

npz_filename = "cycle_model_weights.npz"
np.savez(npz_filename, **weights)
# Recompressing the NPZ file reduces its file size considerably since it contains
# many small arrays, which are otherwise only compressed separately.
with open(npz_filename, "rb") as infile:
    with gzip.open(npz_filename + ".gz", "wb") as outfile:
        shutil.copyfileobj(infile, outfile)
os.remove(npz_filename)
