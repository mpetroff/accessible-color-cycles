import gzip
import numpy as np
import colorspacious


def to_jab(color):
    """
    Convert hex color code (without `#`) to CAM02-UCS.
    """
    rgb = [(int(i[:2], 16), int(i[2:4], 16), int(i[4:], 16)) for i in color]
    jab = colorspacious.cspace_convert(rgb, "sRGB255", "CAM02-UCS")
    return jab.astype(np.float32)


def sort_colors_by_j(colors):
    """
    Sorts colors by CAM02-UCS J' axis.
    """
    return colors[np.lexsort(colors[:, ::-1].T, 0)]


def sort_colors_by_a(colors):
    """
    Sorts colors by CAM02-UCS a' axis.
    """
    return colors[np.argsort(colors[:, ::-1].T[1])]


def sort_colors_by_b(colors):
    """
    Sorts colors by CAM02-UCS b' axis.
    """
    return colors[np.argsort(colors[:, ::-1].T[2])]


# The next four functions are based on functions in:
# https://github.com/keras-team/keras/blob/2.3.0/keras/backend/numpy_backend.py


def conv(x, w):
    return np.sum(x * w.T[0][..., np.newaxis], axis=1)


def depthwise_conv(x, w):
    return np.array([np.convolve(x[j], w[j, 0], "same") for j in range(w.shape[0])])


def elu(x):
    return x * (x > 0) + (np.exp(x) - 1) * (x < 0)


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


class Dense(object):
    def __init__(self, kernel, bias):
        self.kernel = kernel
        self.bias = bias

    def __call__(self, inputs):
        outputs = np.dot(inputs, self.kernel)
        outputs += self.bias
        return elu(outputs)


class SeparableConv1D(object):
    def __init__(self, depthwise_kernel, pointwise_kernel, bias):
        self.depthwise_kernel = depthwise_kernel
        self.pointwise_kernel = pointwise_kernel
        self.bias = bias

    def __call__(self, inputs):
        outputs = depthwise_conv(inputs, self.depthwise_kernel)
        outputs = conv(outputs, self.pointwise_kernel)
        outputs += self.bias
        return elu(outputs)


class SetModel(object):
    def __init__(self, filename):
        # Load model weights
        layers = []
        with gzip.open(filename, "rb") as infile:
            weight_file = np.load(infile)
            for i in range(weight_file["ensemble_count"]):
                layers.append({})
                for key in ["1j", "2j", "1a", "2a", "1b", "2b"]:
                    kernel = weight_file[key + f"_{i:03d}_kernel"]
                    bias = weight_file[key + f"_{i:03d}_bias"]
                    layers[i][key] = Dense(kernel, bias)
                for key in ["3j", "4j", "5j", "3a", "4a", "5a", "3b", "4b", "5b"]:
                    depthwise_kernel = weight_file[key + f"_{i:03d}_depthwise_kernel"]
                    pointwise_kernel = weight_file[key + f"_{i:03d}_pointwise_kernel"]
                    bias = weight_file[key + f"_{i:03d}_bias"]
                    layers[i][key] = SeparableConv1D(
                        depthwise_kernel, pointwise_kernel, bias
                    )
        self.all_layers = layers

    @staticmethod
    def _eval_ensemble_instance(layers, input_a):
        """
        layers: dict with callable layers
        input_a: [colors sorted by J', colors sorted by a', colors sorted by b']; shape=(3 * num_colors,)
        """
        num_colors = input_a[0].shape[0] // 3

        # Create network
        inputs_a_j = [input_a[0][i * 3 : (i + 1) * 3] for i in range(num_colors)]
        inputs_a_a = [input_a[1][i * 3 : (i + 1) * 3] for i in range(num_colors)]
        inputs_a_b = [input_a[2][i * 3 : (i + 1) * 3] for i in range(num_colors)]

        # Share layers between colors
        x_a_j = [layers["1j"](i / 100) for i in inputs_a_j]
        x_a_a = [layers["1a"](i / 100) for i in inputs_a_a]
        x_a_b = [layers["1b"](i / 100) for i in inputs_a_b]

        x_a_j = [layers["2j"](i) for i in x_a_j]
        x_a_a = [layers["2a"](i) for i in x_a_a]
        x_a_b = [layers["2b"](i) for i in x_a_b]

        # Combine colors into sets
        x_a_j = np.vstack(x_a_j).T
        x_a_a = np.vstack(x_a_a).T
        x_a_b = np.vstack(x_a_b).T

        # Share layers between color sets
        x_a_j = layers["3j"](x_a_j)
        x_a_a = layers["3a"](x_a_a)
        x_a_b = layers["3b"](x_a_b)

        x_a_j = layers["4j"](x_a_j)
        x_a_a = layers["4a"](x_a_a)
        x_a_b = layers["4b"](x_a_b)

        x_a_j = layers["5j"](x_a_j)
        x_a_a = layers["5a"](x_a_a)
        x_a_b = layers["5b"](x_a_b)

        # Average outputs
        x_a_j = np.mean(x_a_j)
        x_a_a = np.mean(x_a_a)
        x_a_b = np.mean(x_a_b)

        # Final non-linear activation
        x_a_j = sigmoid(x_a_j)
        x_a_a = sigmoid(x_a_a)
        x_a_b = sigmoid(x_a_b)

        # Final averaging of sub-ensemble
        return np.mean([x_a_j, x_a_a, x_a_b])

    def __call__(self, rgb_colors, average=True):
        jab = to_jab(rgb_colors)
        sorted_by_j = sort_colors_by_j(jab).flatten()
        sorted_by_a = sort_colors_by_a(jab).flatten()
        sorted_by_b = sort_colors_by_b(jab).flatten()
        inputs = (sorted_by_j, sorted_by_a, sorted_by_b)
        scores = np.array(
            [SetModel._eval_ensemble_instance(l, inputs) for l in self.all_layers]
        )
        if average:
            return np.mean(scores)
        return scores


class CycleModel(object):
    def __init__(self, filename):
        # Load model weights
        layers = []
        with gzip.open(filename, "rb") as infile:
            weight_file = np.load(infile)
            for i in range(weight_file["ensemble_count"]):
                layers.append({})
                for key in ["1", "2"]:
                    kernel = weight_file[key + f"_{i:03d}_kernel"]
                    bias = weight_file[key + f"_{i:03d}_bias"]
                    layers[i][key] = Dense(kernel, bias)
                for key in ["3", "4", "5"]:
                    depthwise_kernel = weight_file[key + f"_{i:03d}_depthwise_kernel"]
                    pointwise_kernel = weight_file[key + f"_{i:03d}_pointwise_kernel"]
                    bias = weight_file[key + f"_{i:03d}_bias"]
                    layers[i][key] = SeparableConv1D(
                        depthwise_kernel, pointwise_kernel, bias
                    )
        self.all_layers = layers

    @staticmethod
    def _eval_ensemble_instance(layers, input_a):
        """
        layers: dict with callable layers
        input_a: color cycle; shape=(3 * num_colors,)
        """
        num_colors = input_a.shape[0] // 3

        # Create network
        inputs_a = [input_a[i * 3 : (i + 1) * 3] for i in range(num_colors)]

        # Share layers between colors
        x_a = [layers["1"](i / 100) for i in inputs_a]
        x_a = [layers["2"](i) for i in x_a]

        # Combine colors into sets
        x_a = np.vstack(x_a).T

        # Share layers between color sets
        x_a = layers["3"](x_a)
        x_a = layers["4"](x_a)
        x_a = layers["5"](x_a)

        # Average outputs
        x_a = np.mean(x_a)

        # Final non-linear activation
        return sigmoid(x_a)

    def __call__(self, rgb_colors, average=True):
        jab = to_jab(rgb_colors).flatten()
        scores = np.array(
            [CycleModel._eval_ensemble_instance(l, jab) for l in self.all_layers]
        )
        if average:
            return np.mean(scores)
        return scores
