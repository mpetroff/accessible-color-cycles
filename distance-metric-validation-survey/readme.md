# Distance metric validation survey

This directory contains code for conducting a validation survey of the color
distance metric used in this work. This validation survey is based on:

> Y. Wang et al., "Optimizing Color Assignment for Perception of Class
> Separability in Multiclass Scatterplots," in IEEE Transactions on Visualization
> and Computer Graphics, vol. 25, no. 1, pp. 820-829, Jan. 2019,
> doi: 10.1109/TVCG.2018.2864912


## Extracting scatter plot points from figure

The supplementary material for Wang et al. (2019) does not include coordinates
of the scatter plot points used in the survey they conducted. Thus, these were
extracted from the paper. The `extract.svg` file was created by opening the
page of Wang (2019) with Fig. 9 on it in Inkscape, deleting everything except
for the Fig. 9 subplots, grouping only by those subplots, scaling each group to
100px, making the document size 100px x 100px, centering the subplots, and
exporting as an optimized SVG. The `extract.py` script was then used to extract
the points from the SVG as `points.js` and `points.npz`.


## Calculating best orders

The JavaScript code provided in the supplementary material for Wang et al. (2019)
was monkey-patched to use the $\Delta E_{cvd}$ color distance metric used in
the present work. As the code did not include a license, it is not
redistributed here. It can be acquired either from IEEE as the official
supplementary material file `tvcg-2864912-mm.zip`:

```
$ sha1sum tvcg-2864912-mm.zip 
06e9cc2c90f93c36ed8fd46849735fdb9a1d1f68  tvcg-2864912-mm.zip
$ unzip tvcg-2864912-mm.zip tvcg-2864912-mm/code/js/getSigmasAndScores.js tvcg-2864912-mm/code/js/util.js tvcg-2864912-mm/code/js/lib/d3.js tvcg-2864912-mm/code/js/lib/flann.js
```

or from the author's website as `supp.zip`
(which is also in the Internet Archive's Wayback Machine):

```
$ wget https://www.yunhaiwang.net/infovis18/color/supp.zip
$ sha1sum supp.zip 
bc8f32514d36567bd414dd6313472a29fdb9577b  supp.zip
$ unzip supp.zip supp/code/js/getSigmasAndScores.js supp/code/js/util.js supp/code/js/lib/d3.js supp/code/js/lib/flann.js
$ mv supp tvcg-2864912-mm
```

The $\Delta E_{cvd}$ color distance metric is implemented with the help of the
files in the `js` directory. The modified Wang et al. (2019) metric is
calculated for each possible order of a given color palette, and the best order
is chosen.

To calculate the best order for each color cycle, open the `calc_best_orders.html`
file in a web browser and wait for the results to be displayed. The results are
saved as `cycles_in_best_order.js`.


## Calculating random angles, orders, plot numbers

For the survey, the questions are asked in the same order each time, with the
scatter points rotated at the same angle each time, and the same plot variant
used each time. To randomly generate the data used for this, the
`gen_angles_order.py` script was used. The results are recorded in
`anglesorderplotnum.js`.


## Running survey

The survey is executed by opening the `index.html` file, which relies on the
`anglesorderplotnum.js`, `bulma.min.css`, `cycles_in_best_order.js`, and
`points.js` files. The results are logged by `POST` requests to the `log.php`
file, which writes the responses to a `log.txt` file.


## Credits

* [d3-cam02](https://github.com/connorgr/d3-cam02), CAM02-UCS implementation
* [Color Cycle Picker](https://github.com/mpetroff/color-cycle-picker), CVD simulation implementation
* [Colorspacious](https://github.com/njsmith/colorspacious), Basis for CVD simulation implementation
* [Bulma](https://bulma.io/), Front-end CSS framework

CVD simulation is based on:

> G. M. Machado, M. M. Oliveira and L. A. F. Fernandes, "A Physiologically-based
> Model for Simulation of Color Vision Deficiency," in _IEEE Transactions on
> Visualization and Computer Graphics_, vol. 15, no. 6, pp. 1291-1298,
> Nov.-Dec. 2009. [doi:10.1109/TVCG.2009.113](https://doi.org/10.1109/TVCG.2009.113)
