let set1,
    set2,
    orders,
    drawMode,
    setPick;

const introductionDiv = document.querySelector('#introduction'),
    questionsDiv = document.querySelector('#questions'),
    directionsDiv = document.querySelector('#directions'),
    setsDiv = document.querySelector('#sets'),
    cyclesDiv = document.querySelector('#cycles'),
    picksDiv = document.querySelector('#picks'),
    numPicksDiv = document.querySelector('#numPicks'),
    messageElem = document.querySelector('#message');

const pickCycleDivs = [
    document.querySelector('#pickcycle1'),
    document.querySelector('#pickcycle2'),
    document.querySelector('#pickcycle3'),
    document.querySelector('#pickcycle4')
];

// Handle enabling / disable colorblindness type question in questionnaire
document.addEventListener('DOMContentLoaded', function() {
    const colorblindnessSelect = document.querySelector('#colorblindnessSelect'),
        colorblindnessSelectNA = colorblindnessSelect.item(0);
    Array.apply(null, document.querySelectorAll('input[name="ColorblindQ"]')).forEach(function(e) {
        e.onchange = function(evt) {
            if (evt.target.value == 'y') {
                colorblindnessSelect.remove(0);
                colorblindnessSelect.disabled = false;
            } else {
                colorblindnessSelect.add(colorblindnessSelectNA, 0);
                colorblindnessSelect.disabled = true;
            }
        };
    });

    // Initialize page
    submit(-1);
});


/**
 * Handle submitting answers.
 * @param {number} orderPick - For initialization, -1; for submitting
 *  questionnaire, -2; else color cycle pick number
 */
function submit(orderPick) {
    const xhr = new XMLHttpRequest();
    xhr.open(orderPick == -1 ? 'GET' : 'POST', '/colors');
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE && xhr.status == 200) {
            const response = JSON.parse(xhr.response);
            if (response.Question) {
                // User has not yet started survey, so show introduction
                introductionDiv.style.display = 'inline';
                return;
            }
            // User is continuing survey, so display next color set choice
            set1 = response.Set1;
            set2 = response.Set2;
            orders = response.Orders;
            drawMode = response.DrawMode;
            for (let i = 0; i < 10; i++) {
                const s1 = document.querySelector('#s1c' + i).style,
                    s2 = document.querySelector('#s2c' + i).style;
                if (i < set1.length) {
                    s1.background = '#' + set1[i];
                    s2.background = '#' + set2[i];
                    s1.display = s2.display = '';
                } else {
                    s1.display = s2.display = 'none';
                }
            }
            ctx1.clearRect(0, 0, canvas1.width, canvas1.height);
            ctx2.clearRect(0, 0, canvas2.width, canvas2.height);
            if (drawMode < 2) {
                const s = drawMode == 0 ? 4 : 8;
                drawScatter(ctx1, s, set1);
                drawScatter(ctx2, s, set2);
            } else {
                const s = drawMode == 2 ? 2 : 4;
                drawLine(ctx1, s, set1);
                drawLine(ctx2, s, set2);
            }
            directionsDiv.style.display = 'none';
            cyclesDiv.style.display = 'none';
            for (let j = 0; j < 4; j++) {
                pickCycleDivs[j].removeAttribute('disabled');
                pickCycleDivs[j].classList.remove('is-loading');
            }
            setsDiv.style.display = 'inline';
            numPicksDiv.textContent = response.Picks;
            picksDiv.style.display = 'inline';
            if (response.Picks == 10 || response.Picks == 25 ||
                (response.Picks > 0 && response.Picks % 50 == 0)) {
                let msg = 'You&rsquo;ve submitted ' + response.Picks + ' responses! ';
                if (response.Picks == 10)
                    msg += 'Please consider sharing this survey with your friends and colleagues.';
                else if (response.Picks == 25)
                    msg += 'Your contributions will hopefully help improve scientific visualization.';
                else
                    msg += 'Thank you for your contribution.';
                document.querySelector('#messageText').innerHTML = msg;
                messageElem.style.display = 'block';
            } else {
                messageElem.style.display = 'none';
            }
        }
    };
    if (orderPick == -1) {
        // Initialize page (GET request)
        xhr.send();
    } else if (orderPick == -2) {
        // Send questionnaire responses
        const formData = new FormData(document.querySelector('#questionnaire'));
        if (!document.getElementsByName('Consent')[0].checked) {
            alert('You must consent to data collection to continue.');
            return;
        }
        const cbq = document.getElementsByName('ColorblindQ');
        if (!(cbq[0].checked && cbq[1].checked && cbq[2].checked && cbq[3].checked))
            formData.append('ColorblindQ', 'dna');
        if (formData.has) {
            if (!formData.has('ColorblindTypeQ'))
                formData.append('ColorblindTypeQ', formData.get('ColorblindQ') == 'y' ? 'dna' : 'na');
        } else {
            // Microsoft Edge doesn't properly implement FormData...
            if (document.querySelector('#colorblindnessSelect').disabled)
                formData.append('ColorblindTypeQ', 'na');
        }
        formData.append('WindowWidth', Math.round(window.innerWidth / 100));
        formData.append('WindowOrientation', window.innerWidth / window.innerHeight >= 1 ? 'l' : 'p');
        xhr.send(formData);
    } else {
        // Send color set / cycle picks
        const formData = new FormData();
        formData.append('Set1', set1);
        formData.append('Set2', set2);
        formData.append('Orders', orders);
        formData.append('DrawMode', drawMode);
        formData.append('SetPick', setPick);
        formData.append('OrderPick', orderPick);
        xhr.send(formData);
    }
}

/**
 * Display color cycle options.
 * @param {number} pick - Color set pick
 */
function cycles(pick) {
    setPick = pick;
    const pickedSet = pick == 1 ? set1 : set2;
    for (let i = 1; i <= 4; i++)
        for (let j = 0; j < 10; j++) {
            const r = document.querySelector('#c' + i + 'r' + j).style;
            if (j < pickedSet.length) {
                document.querySelector('#c' + i + 'c' + j).style.background = '#' + pickedSet[orders[i-1][j]];
                r.display = '';
            } else {
                r.display = 'none';
            }
        }
    setsDiv.style.display = 'none';
    cyclesDiv.style.display = 'inline';
}

// Initialize click handlers for answering survey
for (let i = 1; i <= 2; i++) {
    document.querySelector('#pickset' + i).addEventListener('click', function(e) {
        e.preventDefault();
        cycles(i);
    });
}
for (let i = 0; i < 4; i++) {
    pickCycleDivs[i].addEventListener('click', function(e) {
        e.preventDefault();
        e.target.classList.add('is-loading');
        for (let j = 0; j < 4; j++)
            pickCycleDivs[j].setAttribute('disabled', true);
        submit(i);
    });
}

// Initialize click handlers for starting survey
document.querySelector('#introductionRead').addEventListener('click', function(e) {
    e.preventDefault();
    introductionDiv.style.display = 'none';
    questionsDiv.style.display = 'inline';
    window.scrollTo(0, 0);
});
document.querySelector('#submitAnswers').addEventListener('click', function(e) {
    e.preventDefault();
    const formData = new FormData(document.querySelector('#questionnaire'));
    if (!document.getElementsByName('Consent')[0].checked) {
        alert('You must consent to data collection to continue.');
        return;
    }
    questionsDiv.style.display = 'none';
    directionsDiv.style.display = 'inline';
    window.scrollTo(0, 0);
});
document.querySelector('#directionsRead').addEventListener('click', function(e) {
    e.preventDefault();
    e.target.classList.add('is-loading');
    submit(-2);
    window.scrollTo(0, 0);
});

// Initialize click handler for creating new survey session
document.querySelector('#newSession').addEventListener('click', function(e) {
    e.preventDefault();
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/colors/new');
    xhr.onreadystatechange = function() {
        if (xhr.readyState == XMLHttpRequest.DONE)
            window.location.reload(true);
    };
    xhr.send();
});



//
// Functions for rendering color set visualizations
//

// Dimensions of visualizations
const size = 200,
    dpr = window.devicePixelRatio || 1;

// Initialize canvases
const canvas1 = document.getElementById('canvas1');
canvas1.width = canvas1.height = size * dpr;
const ctx1 = canvas1.getContext('2d');
ctx1.scale(dpr, dpr);
const canvas2 = document.getElementById('canvas2');
canvas2.width = canvas2.height = size * dpr;
const ctx2 = canvas2.getContext('2d');
ctx2.scale(dpr, dpr);

// List of point positions for scatter plot visualizations
const scatter_positions = [
    [0.766, 0.204],
    [0.593, 0.488],
    [0.379, 0.353],
    [0.211, 0.517],
    [0.657, 0.796],
    [0.836, 0.506],
    [0.454, 0.785],
    [0.732, 0.658],
    [0.543, 0.251],
    [0.418, 0.546],
    [0.164, 0.721],
    [0.205, 0.263],
];

/**
 * Draw a scatter plot visualization.
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} radius - Dot radius
 * @param {Array} radius - Array of colors to draw
 */
function drawScatter(ctx, radius, colors) {
    for (let i = 0; i < Math.min(colors.length, scatter_positions.length); i++) {
        const p = scatter_positions[i];
        ctx.beginPath();
        ctx.fillStyle = '#' + colors[i];
        ctx.arc(p[0] * size, p[1] * size, radius, 0, 2 * Math.PI);
        ctx.fill();
    }
}

// Coordinates for drawing lines for line plot visualizations
const lines = {
    6: [
        [ 0.096, 0.107, 0.083, 0.116, 0.087, 0.053, 0.089, 0.093, 0.007, 0.064],
        [ 0.207, 0.251, 0.315, 0.331, 0.307, 0.17 , 0.213, 0.271, 0.333, 0.279],
        [ 0.447, 0.425, 0.452, 0.353, 0.431, 0.359, 0.381, 0.455, 0.498, 0.407],
        [ 0.577, 0.522, 0.593, 0.51 , 0.593, 0.661, 0.555, 0.644, 0.55 , 0.536],
        [ 0.819, 0.787, 0.774, 0.823, 0.782, 0.715, 0.703, 0.691, 0.764, 0.816],
        [ 0.91 , 0.894, 0.94 , 0.887, 0.948, 0.933, 0.918, 0.853, 0.843, 0.972]
    ],
    8: [
        [ 0.016, 0.092, 0.044, 0.062, 0.103, 0.118, 0.002, 0.061, 0.005, 0.098],
        [ 0.141, 0.209, 0.202, 0.233, 0.196, 0.249, 0.157, 0.127, 0.133, 0.179],
        [ 0.311, 0.359, 0.258, 0.266, 0.316, 0.329, 0.344, 0.283, 0.347, 0.316],
        [ 0.473, 0.494, 0.46 , 0.477, 0.388, 0.461, 0.486, 0.416, 0.48 , 0.386],
        [ 0.562, 0.5  , 0.569, 0.502, 0.603, 0.602, 0.62 , 0.583, 0.624, 0.518],
        [ 0.671, 0.663, 0.653, 0.683, 0.667, 0.747, 0.716, 0.644, 0.682, 0.632],
        [ 0.837, 0.855, 0.793, 0.869, 0.861, 0.812, 0.797, 0.805, 0.867, 0.818],
        [ 0.89 , 0.921, 0.912, 0.932, 0.882, 0.932, 0.883, 0.995, 0.916, 0.91 ]
    ],
    10: [
        [ 0.074, 0.068, 0.068, 0.035, 0.068, 0.078, 0.079, 0.076, 0.022, 0.073],
        [ 0.181, 0.171, 0.131, 0.152, 0.133, 0.116, 0.177, 0.112, 0.196, 0.118],
        [ 0.283, 0.207, 0.218, 0.268, 0.273, 0.254, 0.226, 0.264, 0.233, 0.224],
        [ 0.331, 0.342, 0.32 , 0.325, 0.373, 0.384, 0.305, 0.343, 0.346, 0.383],
        [ 0.412, 0.459, 0.406, 0.422, 0.494, 0.49 , 0.458, 0.446, 0.477, 0.456],
        [ 0.544, 0.591, 0.562, 0.599, 0.597, 0.54 , 0.581, 0.544, 0.565, 0.564],
        [ 0.682, 0.65 , 0.638, 0.607, 0.651, 0.64 , 0.681, 0.661, 0.609, 0.654],
        [ 0.726, 0.758, 0.766, 0.776, 0.786, 0.775, 0.739, 0.737, 0.738, 0.767],
        [ 0.886, 0.803, 0.845, 0.871, 0.874, 0.85 , 0.827, 0.895, 0.811, 0.882],
        [ 0.916, 0.924, 0.978, 0.956, 0.96 , 0.959, 0.984, 0.978, 0.982, 0.95 ]
    ]
};

/**
 * Draw a line plot visualization.
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {number} radius - Line thickness
 * @param {Array} radius - Array of colors to draw
 */
function drawLine(ctx, thickness, colors) {
    ctx.lineWidth = thickness;
    for (let i = 0; i < colors.length; i++) {
        ctx.beginPath();
        ctx.strokeStyle = '#' + colors[i];
        ctx.moveTo(0.05 * size, lines[colors.length][i][0] * (size - 10) + 5);
        for (let j = 1; j < 10; j++)
            ctx.lineTo((0.05 + j / 10) * size, lines[colors.length][i][j] * (size - 10) + 5);
        ctx.stroke();
    }
}

// For drawing color cycle visualization for introduction
const canvasIntro1 = document.getElementById('canvas-intro1'),
    canvasIntro2 = document.getElementById('canvas-intro2'),
    canvasIntro3 = document.getElementById('canvas-intro3');
canvasIntro1.width = canvasIntro1.height = size * dpr;
canvasIntro2.width = canvasIntro2.height = size * dpr;
canvasIntro3.width = canvasIntro3.height = size * dpr;
const ctxIntro1 = canvasIntro1.getContext('2d'),
    ctxIntro2 = canvasIntro2.getContext('2d'),
    ctxIntro3 = canvasIntro3.getContext('2d');
ctxIntro1.scale(dpr, dpr);
ctxIntro2.scale(dpr, dpr);
ctxIntro3.scale(dpr, dpr);
const tab10 = ['1f77b4', 'ff7f0e', '2ca02c', 'd62728', '9467bd',
               '8c564b', 'e377c2', '7f7f7f', 'bcbd22', '17becf'],
    tab10deut100 = ['456cb3', 'c4ae05', '968838', '8b7c1f', '5d7bbb',
                    '6f684a', '99a3bf', '7f7f7f', 'ceb932', '96a5cf'],
    tab10prot100 = ['5a79b7', 'a59100', 'a39119', '615725', '5279c0',
                    '635d4a', '7c92c5', '7f7f7f', 'cdb500', 'adb6d0'];
drawLine(ctxIntro1, 4, tab10);
drawLine(ctxIntro2, 4, tab10deut100);
drawLine(ctxIntro3, 4, tab10prot100);

// Show a message if something goes wrong
window.onerror = function() {
    alert('Something went wrong...')
};
