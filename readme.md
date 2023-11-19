# Creating accessible color cycles for data visualization

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.5806615.svg)](https://doi.org/10.5281/zenodo.5806615)
[![arXiv](https://img.shields.io/badge/arXiv-2107.02270-red)](https://arxiv.org/abs/2107.02270)

This code serves as a supplement to the paper titled _Accessible Color Sequences for Data Visualization_. It contains code for creating random color sets with a minimum perceptual distance enforced, for running a color-cycle aesthetic-preference survey, for creating a machine-learning aesthetic-preference model based on the survey results, and for creating final color cycles that balance accessibility with aesthetics. Additionally, it includes data resulting from the survey and the analysis.

The analysis was performed under Ubuntu 18.04 on a dual-socket system with Intel Xeon E5-2690 v4 CPUs and a Python 3.6.9 virtual environment defined by the `requirements.txt` file (installed with `pip==21.1.1`, `setuptools==56.2.0`, `wheel==0.36.2`).

Notebooks were executed with:
```
$ jupyter nbconvert --ExecutePreprocessor.timeout=-1 --ExecutePreprocessor.record_timing=False --to notebook --execute notebook.ipynb
```

## Final results

The final results of the present analysis are located in the `aesthetic-models/top-cycles.json` file. The top six-color color cycle is:
```
["#5790fc", "#f89c20", "#e42536", "#964a8b", "#9c9ca1", "#7a21dd"]
```
The top eight-color color cycle is:
```
["#1845fb", "#ff5e02", "#c91f16", "#c849a9", "#adad7d", "#86c8dd", "#578dff", "#656364"]
```
The top ten-color color cycle is:
```
["#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6", "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd"]
```


## Analysis steps

### Color-set generation

The `set-generation` directory contains scripts for generating color sets. The `gen_color_sets.py` script generates random color sets with perceptual-distance constraints. The sets used for the color-cycle survey can be regenerated with:
```
$ python3 gen_color_sets.py --num-colors 6 --min-light-dist 2 --min-color-dist 20 --include-bug
$ python3 gen_color_sets.py --num-colors 8 --min-light-dist 2 --min-color-dist 18 --include-bug
$ python3 gen_color_sets.py --num-colors 10 --min-light-dist 2 --min-color-dist 16 --include-bug
```
The final color sets can be regenerated with:
```
$ python3 gen_color_sets.py --num-colors 6 --min-light-dist 5.0 --min-color-dist 20 --max-j 80
$ python3 gen_color_sets.py --num-colors 8 --min-light-dist 4.2 --min-color-dist 18 --max-j 82
$ python3 gen_color_sets.py --num-colors 10 --min-light-dist 3.6 --min-color-dist 16 --max-j 84
```
Regenerating the color sets requires several thousand CPU hours. The `--include-bug` flag forces the script to include a bug that was present when the color sets used for the survey were generated, which affected how uniformly the color gamut was sampled.

The `max_dist_seq.py` script generates color cycles using the sequential-search method of Glasbey et al. (2007) extended to use CAM02-UCS and color-vision-deficiency simulations. The contents of Table 1 of the paper can be regenerated with:
```
$ python3 max_dist_seq.py --min-j 0 --max-j 100
$ python3 max_dist_seq.py --min-j 40 --max-j 90
```
This process is single-threaded, requires >60GB of memory, and takes a day or two.


### Color-cycle survey

The `survey` directory contains the code used to run the color-cycle survey. The `to_hcl.py` script was used to sort the color sets generated in the previous step by hue, then chroma, then lightness to be used for the survey. The `main.go` file contains the server backend code, which records survey responses to a text-based log file. The static files for the survey's frontend can be regenerated using `npm run build`.


### Color-cycle survey results

The `survey-results` directory contains the results of the color-cycle survey. The `parse-log.ipynb` notebook contains the code used to parse the survey results log file and contains summary statistics of the survey user sessions. The `results.db` SQLite database, which was created by the previously-mentioned notebook, contains the survey responses. To protect the privacy of the survey respondents, neither the log file used to create the results database nor the database's sessions table are included in this data release. Country codes were derived from partial IP addresses using the [2019-12-24 release](https://web.archive.org/web/20191227182412/https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.tar.gz) of the MaxMind GeoLite2 Country geolocation database. The SHA-256 hashes of the `results.log` and `GeoLite2-Country_20191224.mmdb` files (which are not included in this repository) are `4f4519dfb17e0cb459bb4f16d1656d46d893d56304c5ef7c136d81d851088cc8` and `9aedbe59990318581ec5d880716d3415e40bfc07280107112d6d7328c771e059`, respectively.


### Probabilistic color-name model

The `color-name-model` directory contains a reanalysis of the probabilistic color-name model described in Heer & Stone (2012). The `post-process-heer-stone.ipynb` notebook contains this analysis, which finds and merges synonymous color names and eliminates rarely-used color names. The `colornamemodel.npz` file contains the data of the post-processed model.


### Machine-learning aesthetic-preference models

The `aesthetic-models` directory contains the code and weights used to create and evaluate machine-learning models for aesthetic preference of color sets and cycles. The `set-analysis.ipynb` notebook contains the code used to create and train the color set model, while the `set-evaluation.ipynb` contains the code used to evaluate it. The `cycle-analysis.ipynb` notebook contains the code used to create and train the color cycle model, while the `cycle-evaluation.ipynb` notebook contains the code used to evaluate it. The `weights` subdirectory contains the model weights for both models. The `numpy-version` subdirectory contains a script for converting the weights from the TensorFlow format to a NumPy-compatible format and an example implementation for evaluating the model in NumPy, without the need for TensorFlow. The `set-scores.npz` file contains the scores for each of the input color sets, while the `top-sets.json` file contains the color sets with the highest scores. The `cycle-scores.npz` file contains the scores for each ordering of the color sets with the highest scores, and the `top-cycles.json` file contains the color cycles with the highest scores, which are the final results of the present analysis. The `additional-evaluation.ipynb` notebook looks at the various score ranges.

Note that the v1.0 release had a data loading bug, which affected the cycle model. Although it affected the model accuracy, it did not affect the final color cycles. The original model should not be used.


### Other analysis

The `other-analysis` directory contains code for performing other analyses on the data. The `max-min-dists.ipynb` notebook contains code for finding the color sets with the maximum minimum-perceptual distances, and the `min-max-dist-sets.json` file contains the results of this analysis. The `set-analysis-linear-model.ipynb` notebook contains an analysis of the survey responses based on a linear model. The `result-plots.ipynb` notebook generates the tables and plots for this repository's companion paper. The `compare-pair-preference-scores.ipynb` notebook evaluates the effectiveness of the aesthetic pair-preference model described in Gramazio et al. (2017) on the survey data. The notebook can be executed from the `src` directory of [Colorgorical](https://github.com/connorgr/colorgorical) using Git commit 90649656a57ce9743b00390473adce51a821cadc. Unfortunately, the Colorgorical repository does not include licensing information. The `cycle-comparison.ipynb` notebook evaluates the accessibility of a variety of existing color cycles and compiles the results into a table.


### Lightness analysis

The `lightness-analysis` directory contains a reanalysis of the scatter plot accessibility data collected by Smart & Szafir (2019). The `lightness-analysis.ipynb` notebook contains the code used to perform this analysis, which looks at how scatter-plot-marker lightness affects response times. The [color-shape_data_processed.csv](https://osf.io/nz2y7/) file has a SHA-256 hash of `c0fe510d1b673d26a9fa1085fc5da3017b27cc3814c6e587a1800a7a647c778d` but is not included in this repository as it was not distributed with explicit licensing information.



## License

The code contained in this repository is distributed under the [MIT License](https://opensource.org/licenses/MIT).

The included color-vision-deficiency simulation and color-distance calculation implementations (`set-generation/color_conversions.py`) are based on [Colorspacious](https://github.com/njsmith/colorspacious), which is [MIT licensed](https://github.com/njsmith/colorspacious/blob/v1.1.0/LICENSE.txt).

The `color-name-model/c3_data.json` file is from [C3 (Categorical Color Components)](https://github.com/StanfordHCI/c3/blob/d3576c7615ab0d6b2d81252a362599a9fd900d63/data/xkcd/c3_data.json), which is distributed under a [3-Clause BSD License](https://github.com/StanfordHCI/c3/blob/d3576c7615ab0d6b2d81252a362599a9fd900d63/LICENSE).

The resulting data files (including, but not limited to, the final color cycles and the `survey-results/results.db` file) are released into the public domain using the [CC0 1.0 Public Domain Dedication](https://creativecommons.org/publicdomain/zero/1.0/).



## Credits

This code was written by Matthew A. Petroff ([ORCID:0000-0002-4436-4215](https://orcid.org/0000-0002-4436-4215)).

The included scatter plot lightness analysis is based on data collected by:
> Stephen Smart and Danielle Albers Szafir. 2019. Measuring the Separability of Shape, Size, and Color in Scatterplots. In _Proceedings of the 2019 CHI Conference on Human Factors in Computing Systems (CHI '19)_. ACM Press, New York, 14 pages. [doi:10.1145/3290605.3300899](https://doi.org/10.1145/3290605.3300899)

The included color naming model is based on work by:
> Jeffrey Heer and Maureen Stone. 2012. Color naming models for color selection, image editing and palette design. In _Proceedings of the SIGCHI Conference on Human Factors in Computing Systems_ (Austin, Texas) _(CHI '12)_. ACM Press, New York, 1007--1016. [doi:10.1145/2207676.2208547](https://doi.org/10.1145/2207676.2208547)

which used data collected by Randall Munroe's [xkcd color survey](https://blog.xkcd.com/2010/05/03/color-survey-results/).

A comparison is made to a pair-preference model developed by:
> Connor C. Gramazio, David H. Laidlaw, and Karen B. Schloss. 2017. Colorgorical: Creating discriminable and preferable color palettes for information visualization. _IEEE Transactions on Visualization and Computer Graphics_ 23, 1 (Jan. 2017), 521--530. [doi:10.1109/tvcg.2016.2598918](https://doi.org/10.1109/tvcg.2016.2598918)

The color-vision-deficiency simulation is based on:
> Gustavo M. Machado, Manuel M. Oliveira, and Leandro A. F. Fernandes. 2009. A Physiologically-based Model for Simulation of Color Vision Deficiency. _IEEE Transactions on Visualization and Computer Graphics_ 15, 6 (Nov. 2009), 1291--1298. [doi:10.1109/tvcg.2009.113](https://doi.org/10.1109/tvcg.2009.113)
