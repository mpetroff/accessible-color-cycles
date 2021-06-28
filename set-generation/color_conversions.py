"""
A limited, Numba-optimized library for color conversion and CVD simulation.

Based on [colorspacious](https://github.com/njsmith/colorspacious)


The MIT License (MIT)

Copyright (c) 2014-2018 Colorspacious developers
Copyright (c) 2018-2021 Matthew Petroff <https://mpetroff.net>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import numpy as np
import numba

#
# Basic colorspaces: conversions between sRGB, XYZ
#


@numba.njit
def sRGB1_linear_to_sRGB1(sRGB1_linear):
    out = sRGB1_linear.copy()
    linear_portion = sRGB1_linear <= 0.0031308
    a = 0.055
    out[linear_portion] = sRGB1_linear[linear_portion] * 12.92
    out[~linear_portion] = (1 + a) * sRGB1_linear[~linear_portion] ** (1 / 2.4) - a
    return out


@numba.njit
def sRGB1_to_sRGB1_linear(sRGB1):
    """Convert sRGB (as floats in the 0-to-1 range) to linear sRGB."""
    out = sRGB1.copy()
    linear_portion = sRGB1 < 0.04045
    a = 0.055
    out[linear_portion] = sRGB1[linear_portion] / 12.92
    out[~linear_portion] = ((sRGB1[~linear_portion] + a) / (a + 1)) ** 2.4
    return out


XYZ100_to_sRGB1_matrix = np.array(
    [
        # This is the exact matrix specified in IEC 61966-2-1:1999
        [3.2406, -1.5372, -0.4986],
        [-0.9689, 1.8758, 0.0415],
        [0.0557, -0.2040, 1.0570],
    ],
    dtype=np.float64,
)

sRGB1_to_XYZ100_matrix = np.linalg.inv(XYZ100_to_sRGB1_matrix)


@numba.njit
def XYZ100_to_sRGB1_linear(XYZ100):
    """Convert XYZ to linear sRGB, where XYZ is normalized so that reference
    white D65 is X=95.05, Y=100, Z=108.90 and sRGB is on the 0-1 scale. Linear
    sRGB has a linear relationship to actual light, so it is an appropriate
    space for simulating light (e.g. for alpha blending).
    """
    return np.dot(XYZ100_to_sRGB1_matrix, XYZ100) / 100.0


@numba.njit
def sRGB1_linear_to_XYZ100(sRGB1_linear):
    return np.dot(sRGB1_to_XYZ100_matrix, sRGB1_linear) * 100.0


#
# CIECAM02
#

M_CAT02 = np.asarray(
    [[0.7328, 0.4296, -0.1624], [-0.7036, 1.6975, 0.0061], [0.0030, 0.0136, 0.9834]]
)

M_HPE = np.asarray(
    [
        [0.38971, 0.68898, -0.07868],
        [-0.22981, 1.18340, 0.04641],
        [0.00000, 0.00000, 1.00000],
    ]
)
# These are very well-conditioned matrices (condition numbers <4), so just
# taking the inverse is fine, and it simplifies things below.
M_CAT02_inv = np.linalg.inv(M_CAT02)
M_HPE_M_CAT02_inv = np.dot(M_HPE, M_CAT02_inv)
M_CAT02_M_HPE_inv = np.dot(M_CAT02, np.linalg.inv(M_HPE))

h_i = np.asarray([20.14, 90.00, 164.25, 237.53, 380.14])
e_i = np.asarray([0.8, 0.7, 1.0, 1.2, 0.8])
H_i = np.asarray([0.0, 100.0, 200.0, 300.0, 400.0])

# sRGB specifies a D65 monitor and a D50 ambient. CIECAM02 doesn't really
# know how to deal with this discrepancy; it appears that the usual thing
# to do is just to use D65 for the whitepoint.
XYZ100_w = np.array([95.047, 100, 108.883])  # D65
Y_b = 20
# To compute L_A:
#   illuminance in lux / pi = luminance in cd/m^2
#   luminance in cd/m^2 / 5 = L_A (the "grey world assumption")
# See Moroney (2000), "Usage guidelines for CIECAM97s".
# sRGB illuminance is 64 lux.
L_A = (64 / np.pi) / 5
F = 1.0
c = 0.69
N_c = 1.0
RGB_w = np.dot(M_CAT02, XYZ100_w)
D = np.clip(F * (1 - (1 / 3.6) * np.exp((-L_A - 42) / 92)), 0, 1)
D_RGB = D * XYZ100_w[1] / RGB_w + 1 - D
# Fairchild (2013), pages 290-292, recommends using this equation
# instead, though notes that it doesn't make much difference as part
# of a full CIECAM02 system. (It matters more if you're only using
# pieces.)
# D_RGB = D * 100 / RGB_w + 1 - D
k = 1 / (5 * L_A + 1)
F_L = 0.2 * k ** 4 * (5 * L_A) + 0.1 * (1 - k ** 4) ** 2 * (5 * L_A) ** (1.0 / 3)
n = Y_b / XYZ100_w[1]
z = 1.48 + np.sqrt(n)
N_bb = 0.725 * (1 / n) ** 0.2
N_cb = N_bb  # ??

RGB_wc = D_RGB * RGB_w
RGBprime_w = np.dot(M_HPE_M_CAT02_inv, RGB_wc)
tmp = ((F_L * RGBprime_w) / 100) ** 0.42
RGBprime_aw = 400 * (tmp / (tmp + 27.13)) + 0.1
A_w = (np.dot([2, 1, 1.0 / 20], RGBprime_aw) - 0.305) * N_bb

# XYZ100 must have shape (3,) or (3, n)
@numba.njit
def XYZ100_to_CIECAM02(XYZ100):
    """Computes CIECAM02 appearance correlates for the given tristimulus
    value(s) XYZ (normalized to be on the 0-100 scale).
    """

    #### Step 1

    RGB = np.dot(M_CAT02, XYZ100)

    #### Step 2

    RGB_C = D_RGB * RGB

    #### Step 3

    RGBprime = np.dot(M_HPE_M_CAT02_inv, RGB_C)

    #### Step 4

    RGBprime_signs = np.sign(RGBprime)

    tmp = (F_L * RGBprime_signs * RGBprime / 100) ** 0.42
    RGBprime_a = RGBprime_signs * 400 * (tmp / (tmp + 27.13)) + 0.1

    #### Step 5

    a = np.dot(np.array([1, -12.0 / 11, 1.0 / 11]), RGBprime_a)
    b = np.dot(np.array([1.0 / 9, 1.0 / 9, -2.0 / 9]), RGBprime_a)
    h_rad = np.arctan2(b, a)
    h = np.rad2deg(h_rad) % 360

    # #### Step 6

    # hprime = h, unless h < 20.14, in which case hprime = h + 360.
    if h < 20.14:
        hprime = h + 360.0
    else:
        hprime = h
    # we use 0-based indexing, so our i is one less than the reference
    # formulas' i.
    i = np.searchsorted(h_i, hprime, side="right") - 1
    tmp = (hprime - h_i[i]) / e_i[i]
    H = H_i[i] + ((100 * tmp) / (tmp + (h_i[i + 1] - hprime) / e_i[i + 1]))

    #### Step 7

    A = (np.dot(np.array([2, 1, 1.0 / 20]), RGBprime_a) - 0.305) * N_bb
    if A < 0:
        A = np.nan

    #### Step 8

    J = 100 * (A / A_w) ** (c * z)

    #### Step 9

    # Q = _J_to_Q(J)

    #### Step 10

    e = (12500.0 / 13) * N_c * N_cb * (np.cos(h_rad + 2) + 3.8)
    t = e * np.sqrt(a ** 2 + b ** 2) / np.dot(np.array([1, 1, 21.0 / 20]), RGBprime_a)

    C = t ** 0.9 * (J / 100) ** 0.5 * (1.64 - 0.29 ** n) ** 0.73
    M = C * F_L ** 0.25

    return np.array([J, M, h])


@numba.njit
def CIECAM02_to_XYZ100(J, M, h):
    """Return the unique tristimulus values that have the given CIECAM02
    appearance correlates under these viewing conditions.
    Returned tristimulus values will be on the 0-100 scale, not the 0-1
    scale.
    """

    #### Step 1: conversions to get JCh

    C = M / F_L ** 0.25

    #### Step 2

    t = (C / (np.sqrt(J / 100) * (1.64 - 0.29 ** n) ** 0.73)) ** (1 / 0.9)
    e_t = 0.25 * (np.cos(np.deg2rad(h) + 2) + 3.8)
    A = A_w * (J / 100) ** (1 / (c * z))

    # an awkward way of calculating 1/t such that 1/0 -> inf
    if t < 1e-30:
        one_over_t = np.inf
    else:
        one_over_t = 1 / t

    p_1 = (50000.0 / 13) * N_c * N_cb * e_t * one_over_t
    p_2 = A / N_bb + 0.305
    p_3 = 21.0 / 20

    #### Step 3

    sin_h = np.sin(np.deg2rad(h))
    cos_h = np.cos(np.deg2rad(h))

    # to avoid divide-by-zero (or divide-by-eps) issues, we use different
    # computations when |sin_h| > |cos_h| and vice-versa
    num = p_2 * (2 + p_3) * (460.0 / 1403)
    denom_part2 = (2 + p_3) * (220.0 / 1403)
    denom_part3 = (-27.0 / 1403) + p_3 * (6300.0 / 1403)

    if np.abs(sin_h) >= np.abs(cos_h):
        p_4 = p_1 / sin_h
        b = num / (p_4 + denom_part2 * (cos_h / sin_h) + denom_part3)
        a = b * cos_h / sin_h
    else:
        p_5 = p_1 / cos_h
        a = num / (p_5 + denom_part2 + denom_part3 * (sin_h / cos_h))
        b = a * sin_h / cos_h

    #### Step 4

    p2ab = np.array([p_2, a, b])
    RGBprime_a_matrix = (
        1.0
        / 1403
        * np.array(
            ([460.0, 451.0, 288.0], [460.0, -891.0, -261.0], [460.0, -220.0, -6300.0])
        )
    )

    RGBprime_a = np.dot(RGBprime_a_matrix, p2ab)

    #### Step 5

    RGBprime = (
        np.sign(RGBprime_a - 0.1)
        * (100 / F_L)
        * ((27.13 * np.abs(RGBprime_a - 0.1)) / (400 - np.abs(RGBprime_a - 0.1)))
        ** (1 / 0.42)
    )

    #### Step 6

    RGB_C = np.dot(M_CAT02_M_HPE_inv, RGBprime)

    #### Step 7

    RGB = RGB_C / D_RGB

    #### Step 8

    XYZ100 = np.dot(M_CAT02_inv, RGB)

    return XYZ100


#
# Conversion functions
#


@numba.njit
def CVD_forward_protanomaly(sRGB, severity):
    mat = machado_et_al_2009_matrix_protanomaly(severity)
    return np.dot(mat, sRGB)


@numba.njit
def CVD_forward_deuteranomaly(sRGB, severity):
    mat = machado_et_al_2009_matrix_deuteranomaly(severity)
    return np.dot(mat, sRGB)


@numba.njit
def CVD_forward_tritanomaly(sRGB, severity):
    mat = machado_et_al_2009_matrix_tritanomaly(severity)
    return np.dot(mat, sRGB)


@numba.njit
def jab_to_rgb_linear(jab):
    jmh = Jpapbp_to_JMh(jab)
    xyz100 = CIECAM02_to_XYZ100(J=jmh[0], M=jmh[1], h=jmh[2])
    srgb1_linear = XYZ100_to_sRGB1_linear(xyz100)
    return srgb1_linear


@numba.njit
def rgb_linear_to_jab(srgb1_linear):
    xyz100 = sRGB1_linear_to_XYZ100(srgb1_linear)
    jmh = XYZ100_to_CIECAM02(xyz100)
    jab = JMh_to_Jpapbp(jmh)
    return jab


#
# CVD simulation
#

# Matrices for simulating anomalous color vision from:
#   Machado, Oliveira, & Fernandes (2009). A Physiologically-based Model for
#   Simulation of Color Vision Deficiency. doi: 10.1109/TVCG.2009.113
#
#   http://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html


@numba.njit
def machado_et_al_2009_matrix_protanomaly(severity):
    """Retrieve a matrix for simulating anomalous color vision.

    :param cvd_type: One of "protanomaly", "deuteranomaly", or "tritanomaly".
    :param severity: A value between 0 and 100.

    :returns: A 3x3 CVD simulation matrix as computed by Machado et al
             (2009).

    These matrices were downloaded from:

      http://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html

    which is supplementary data from :cite:`Machado-CVD`.

    If severity is a multiple of 10, then simply returns the matrix from that
    webpage. For other severities, performs linear interpolation.
    """

    MACHADO_ET_AL_MATRIX_protanomaly = np.array(
        (
            (
                [1.000000, 0.000000, -0.000000],
                [0.000000, 1.000000, 0.000000],
                [-0.000000, -0.000000, 1.000000],
            ),
            (
                [0.856167, 0.182038, -0.038205],
                [0.029342, 0.955115, 0.015544],
                [-0.002880, -0.001563, 1.004443],
            ),
            (
                [0.734766, 0.334872, -0.069637],
                [0.051840, 0.919198, 0.028963],
                [-0.004928, -0.004209, 1.009137],
            ),
            (
                [0.630323, 0.465641, -0.095964],
                [0.069181, 0.890046, 0.040773],
                [-0.006308, -0.007724, 1.014032],
            ),
            (
                [0.539009, 0.579343, -0.118352],
                [0.082546, 0.866121, 0.051332],
                [-0.007136, -0.011959, 1.019095],
            ),
            (
                [0.458064, 0.679578, -0.137642],
                [0.092785, 0.846313, 0.060902],
                [-0.007494, -0.016807, 1.024301],
            ),
            (
                [0.385450, 0.769005, -0.154455],
                [0.100526, 0.829802, 0.069673],
                [-0.007442, -0.022190, 1.029632],
            ),
            (
                [0.319627, 0.849633, -0.169261],
                [0.106241, 0.815969, 0.077790],
                [-0.007025, -0.028051, 1.035076],
            ),
            (
                [0.259411, 0.923008, -0.182420],
                [0.110296, 0.804340, 0.085364],
                [-0.006276, -0.034346, 1.040622],
            ),
            (
                [0.203876, 0.990338, -0.194214],
                [0.112975, 0.794542, 0.092483],
                [-0.005222, -0.041043, 1.046265],
            ),
            (
                [0.152286, 1.052583, -0.204868],
                [0.114503, 0.786281, 0.099216],
                [-0.003882, -0.048116, 1.051998],
            ),
        ),
        dtype=np.float64,
    )

    assert 0 <= severity <= 100

    fraction = severity % 10

    low = int(severity - fraction) // 10
    high = low + 1
    # assert low <= severity <= high

    low_matrix = MACHADO_ET_AL_MATRIX_protanomaly[low]
    if severity == 100:
        # Don't try interpolating between 100 and 110, there is no 110...
        return low_matrix
    high_matrix = MACHADO_ET_AL_MATRIX_protanomaly[high]
    return (1 - fraction / 10.0) * low_matrix + fraction / 10.0 * high_matrix


@numba.njit
def machado_et_al_2009_matrix_deuteranomaly(severity):
    """Retrieve a matrix for simulating anomalous color vision.

    :param cvd_type: One of "protanomaly", "deuteranomaly", or "tritanomaly".
    :param severity: A value between 0 and 100.

    :returns: A 3x3 CVD simulation matrix as computed by Machado et al
             (2009).

    These matrices were downloaded from:

      http://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html

    which is supplementary data from :cite:`Machado-CVD`.

    If severity is a multiple of 10, then simply returns the matrix from that
    webpage. For other severities, performs linear interpolation.
    """

    MACHADO_ET_AL_MATRIX_deuteranomaly = np.array(
        (
            (
                [1.000000, 0.000000, -0.000000],
                [0.000000, 1.000000, 0.000000],
                [-0.000000, -0.000000, 1.000000],
            ),
            (
                [0.866435, 0.177704, -0.044139],
                [0.049567, 0.939063, 0.011370],
                [-0.003453, 0.007233, 0.996220],
            ),
            (
                [0.760729, 0.319078, -0.079807],
                [0.090568, 0.889315, 0.020117],
                [-0.006027, 0.013325, 0.992702],
            ),
            (
                [0.675425, 0.433850, -0.109275],
                [0.125303, 0.847755, 0.026942],
                [-0.007950, 0.018572, 0.989378],
            ),
            (
                [0.605511, 0.528560, -0.134071],
                [0.155318, 0.812366, 0.032316],
                [-0.009376, 0.023176, 0.986200],
            ),
            (
                [0.547494, 0.607765, -0.155259],
                [0.181692, 0.781742, 0.036566],
                [-0.010410, 0.027275, 0.983136],
            ),
            (
                [0.498864, 0.674741, -0.173604],
                [0.205199, 0.754872, 0.039929],
                [-0.011131, 0.030969, 0.980162],
            ),
            (
                [0.457771, 0.731899, -0.189670],
                [0.226409, 0.731012, 0.042579],
                [-0.011595, 0.034333, 0.977261],
            ),
            (
                [0.422823, 0.781057, -0.203881],
                [0.245752, 0.709602, 0.044646],
                [-0.011843, 0.037423, 0.974421],
            ),
            (
                [0.392952, 0.823610, -0.216562],
                [0.263559, 0.690210, 0.046232],
                [-0.011910, 0.040281, 0.971630],
            ),
            (
                [0.367322, 0.860646, -0.227968],
                [0.280085, 0.672501, 0.047413],
                [-0.011820, 0.042940, 0.968881],
            ),
        ),
        dtype=np.float64,
    )

    assert 0 <= severity <= 100

    fraction = severity % 10

    low = int(severity - fraction) // 10
    high = low + 1
    # assert low <= severity <= high

    low_matrix = MACHADO_ET_AL_MATRIX_deuteranomaly[low]
    if severity == 100:
        # Don't try interpolating between 100 and 110, there is no 110...
        return low_matrix
    high_matrix = MACHADO_ET_AL_MATRIX_deuteranomaly[high]
    return (1 - fraction / 10.0) * low_matrix + fraction / 10.0 * high_matrix


@numba.njit
def machado_et_al_2009_matrix_tritanomaly(severity):
    """Retrieve a matrix for simulating anomalous color vision.

    :param cvd_type: One of "protanomaly", "deuteranomaly", or "tritanomaly".
    :param severity: A value between 0 and 100.

    :returns: A 3x3 CVD simulation matrix as computed by Machado et al
             (2009).

    These matrices were downloaded from:

      http://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html

    which is supplementary data from :cite:`Machado-CVD`.

    If severity is a multiple of 10, then simply returns the matrix from that
    webpage. For other severities, performs linear interpolation.
    """

    MACHADO_ET_AL_MATRIX_tritanomaly = np.array(
        (
            (
                [1.000000, 0.000000, -0.000000],
                [0.000000, 1.000000, 0.000000],
                [-0.000000, -0.000000, 1.000000],
            ),
            (
                [0.926670, 0.092514, -0.019184],
                [0.021191, 0.964503, 0.014306],
                [0.008437, 0.054813, 0.936750],
            ),
            (
                [0.895720, 0.133330, -0.029050],
                [0.029997, 0.945400, 0.024603],
                [0.013027, 0.104707, 0.882266],
            ),
            (
                [0.905871, 0.127791, -0.033662],
                [0.026856, 0.941251, 0.031893],
                [0.013410, 0.148296, 0.838294],
            ),
            (
                [0.948035, 0.089490, -0.037526],
                [0.014364, 0.946792, 0.038844],
                [0.010853, 0.193991, 0.795156],
            ),
            (
                [1.017277, 0.027029, -0.044306],
                [-0.006113, 0.958479, 0.047634],
                [0.006379, 0.248708, 0.744913],
            ),
            (
                [1.104996, -0.046633, -0.058363],
                [-0.032137, 0.971635, 0.060503],
                [0.001336, 0.317922, 0.680742],
            ),
            (
                [1.193214, -0.109812, -0.083402],
                [-0.058496, 0.979410, 0.079086],
                [-0.002346, 0.403492, 0.598854],
            ),
            (
                [1.257728, -0.139648, -0.118081],
                [-0.078003, 0.975409, 0.102594],
                [-0.003316, 0.501214, 0.502102],
            ),
            (
                [1.278864, -0.125333, -0.153531],
                [-0.084748, 0.957674, 0.127074],
                [-0.000989, 0.601151, 0.399838],
            ),
            (
                [1.255528, -0.076749, -0.178779],
                [-0.078411, 0.930809, 0.147602],
                [0.004733, 0.691367, 0.303900],
            ),
        ),
        dtype=np.float64,
    )

    assert 0 <= severity <= 100

    fraction = severity % 10

    low = int(severity - fraction) // 10
    high = low + 1
    # assert low <= severity <= high

    low_matrix = MACHADO_ET_AL_MATRIX_tritanomaly[low]
    if severity == 100:
        # Don't try interpolating between 100 and 110, there is no 110...
        return low_matrix
    high_matrix = MACHADO_ET_AL_MATRIX_tritanomaly[high]
    return (1 - fraction / 10.0) * low_matrix + fraction / 10.0 * high_matrix


#
# CAM02-UCS (Luo, et al 2006)
#

KL = 1.0
c1 = 0.007
c2 = 0.0228


@numba.njit
def JMh_to_Jpapbp(JMh):
    J = JMh[..., 0]
    M = JMh[..., 1]
    h = JMh[..., 2]
    Jp = (1 + 100 * c1) * J / (1 + c1 * J)
    Jp = Jp / KL
    Mp = (1.0 / c2) * np.log(1 + c2 * M)
    ap, bp = color_polar2cart(Mp, h)
    return np.array([Jp, ap, bp])


@numba.njit
def Jpapbp_to_JMh(Jpapbp):
    Jp = Jpapbp[..., 0]
    ap = Jpapbp[..., 1]
    bp = Jpapbp[..., 2]
    Jp = Jp * KL
    J = -Jp / (c1 * Jp - 100 * c1 - 1)
    Mp, h = color_cart2polar(ap, bp)
    M = (np.exp(c2 * Mp) - 1) / c2
    return np.array([J, M, h])


#
# Utility functions
#

# Using color conventions: degrees 0-360
@numba.njit
def color_cart2polar(a, b):
    h_rad = np.arctan2(b, a)
    h = np.rad2deg(h_rad) % 360
    r = np.hypot(a, b)
    return (r, h)


@numba.njit
def color_polar2cart(r, h):
    h_rad = np.deg2rad(h)
    return (r * np.cos(h_rad), r * np.sin(h_rad))


@numba.njit
def cam02de(c1, c2):
    diff = np.abs(c1 - c2)
    return np.sqrt(np.sum(diff * diff, axis=-1))
