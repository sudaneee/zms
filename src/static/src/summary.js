/* Result summary charts: small hand-made SVG charts (no library).
   Bars are <= 24px thick with a 4px rounded data end, square at the baseline;
   touching segments are separated by a 2px surface gap; every mark has a
   tooltip on hover and keyboard focus, and every chart has a table view. */
(function () {
  'use strict';
  var data = JSON.parse(document.getElementById('summary-data').textContent);
  var NS = 'http://www.w3.org/2000/svg';
  var GRADES = ['A', 'B', 'C', 'D', 'E', 'F', 'ABS'];
  var GRADE_NAMES = {A: 'A (70+)', B: 'B (60–69)', C: 'C (50–59)', D: 'D (45–49)', E: 'E (40–44)', F: 'F (below 40)', ABS: 'ABS (absent)'};
  var tooltip = document.getElementById('chart-tooltip');

  function css(name) { return getComputedStyle(document.body).getPropertyValue(name).trim(); }
  function gradeColor(g) { return css('--grade-' + g); }
  function el(tag, attrs, parent) {
    var node = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(node);
    return node;
  }
  function text(parent, x, y, value, cls, anchor) {
    var t = el('text', {x: x, y: y, 'class': cls || '', 'text-anchor': anchor || 'start'}, parent);
    t.textContent = value;
    return t;
  }
  function svg(container, width, height) {
    container.textContent = '';
    return el('svg', {viewBox: '0 0 ' + width + ' ' + height, width: width, height: height,
                      preserveAspectRatio: 'xMinYMin meet'}, container);
  }
  function width(container) { return Math.max(280, Math.round(container.getBoundingClientRect().width)); }
  function niceMax(v) {
    if (v <= 0) return 1;
    var p = Math.pow(10, Math.floor(Math.log10(v))), n = v / p;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
  }
  function measure(parent, value) {
    var t = text(parent, -9999, -9999, value, 'label');
    var w = t.getComputedTextLength();
    parent.removeChild(t);
    return w;
  }
  // A bar with a 4px rounded data end and a square base.
  function columnPath(x, y, w, h) {
    var r = Math.min(4, w / 2, h);
    return 'M' + x + ',' + (y + h) + 'V' + (y + r) + 'Q' + x + ',' + y + ' ' + (x + r) + ',' + y +
      'H' + (x + w - r) + 'Q' + (x + w) + ',' + y + ' ' + (x + w) + ',' + (y + r) + 'V' + (y + h) + 'Z';
  }
  function barPath(x, y, w, h, roundEnd) {
    var r = roundEnd ? Math.min(4, h / 2, w) : 0;
    return 'M' + x + ',' + y + 'H' + (x + w - r) + 'Q' + (x + w) + ',' + y + ' ' + (x + w) + ',' + (y + r) +
      'V' + (y + h - r) + 'Q' + (x + w) + ',' + (y + h) + ' ' + (x + w - r) + ',' + (y + h) + 'H' + x + 'Z';
  }

  // ---- tooltip -------------------------------------------------------------
  function showTip(evt, title, rows) {
    tooltip.textContent = '';
    var head = document.createElement('div');
    head.className = 't-title';
    head.textContent = title;
    tooltip.appendChild(head);
    rows.forEach(function (r) {
      var row = document.createElement('div');
      row.className = 't-row';
      var name = document.createElement('span');
      if (r.color) {
        var key = document.createElement('span');
        key.className = 't-key';
        key.style.background = r.color;
        name.appendChild(key);
      }
      name.appendChild(document.createTextNode(r.label));
      var value = document.createElement('b');
      value.textContent = r.value;
      row.appendChild(value);
      row.appendChild(name);
      tooltip.appendChild(row);
    });
    tooltip.hidden = false;
    var x, y;
    if (evt.clientX !== undefined && evt.type !== 'focus') { x = evt.clientX; y = evt.clientY; }
    else { var b = evt.target.getBoundingClientRect(); x = b.left + b.width / 2; y = b.top; }
    var tw = tooltip.offsetWidth, th = tooltip.offsetHeight;
    tooltip.style.left = Math.min(window.innerWidth - tw - 8, Math.max(8, x + 14)) + 'px';
    tooltip.style.top = Math.max(8, (y - th - 12 < 8 ? y + 18 : y - th - 12)) + 'px';
  }
  function hideTip() { tooltip.hidden = true; }
  function hover(target, marks, title, rows) {
    target.setAttribute('tabindex', '0');
    function on(evt) {
      marks.forEach(function (m) { m.classList.add('active'); });
      showTip(evt, title, rows);
    }
    function off() { marks.forEach(function (m) { m.classList.remove('active'); }); hideTip(); }
    target.addEventListener('pointermove', on);
    target.addEventListener('focus', on);
    target.addEventListener('pointerleave', off);
    target.addEventListener('blur', off);
  }

  // ---- vertical columns ----------------------------------------------------
  function columns(id, items, opts) {
    var container = document.getElementById(id);
    if (!container || !items.length) return;
    var W = width(container), H = 220, top = 22, bottom = 26, left = 34, right = 8;
    var s = svg(container, W, H);
    var max = niceMax(Math.max.apply(null, items.map(function (d) { return d.value; })));
    if (opts.max) max = opts.max;
    var plotH = H - top - bottom, plotW = W - left - right;
    [0, 0.5, 1].forEach(function (f) {
      var y = top + plotH * (1 - f);
      el('line', {x1: left, x2: W - right, y1: y, y2: y, 'class': f === 0 ? 'axis' : 'grid'}, s);
      text(s, left - 6, y + 4, String(Math.round(max * f)), '', 'end');
    });
    var band = plotW / items.length, bw = Math.min(24, band * 0.6);
    items.forEach(function (d, i) {
      var x = left + band * i + (band - bw) / 2, h = max ? plotH * d.value / max : 0, y = top + plotH - h;
      var hit = el('rect', {x: left + band * i, y: top, width: band, height: plotH, 'class': 'hit'}, s);
      var mark = el('path', {d: columnPath(x, y, bw, Math.max(h, 0)), fill: opts.color(d), 'class': 'mark'}, s);
      text(s, x + bw / 2, H - 8, d.label, 'label', 'middle');
      if (d.value && (!opts.labelIf || opts.labelIf(d))) text(s, x + bw / 2, y - 6, opts.format(d.value), 'value', 'middle');
      hover(hit, [mark], opts.title(d), opts.rows(d));
    });
  }

  // ---- horizontal bars -----------------------------------------------------
  function bars(id, items, opts) {
    var container = document.getElementById(id);
    if (!container || !items.length) return;
    var W = width(container), row = 30, bh = 16, top = 4;
    var H = top + items.length * row + 22;
    var s = svg(container, W, H);
    var labelW = Math.min(W * 0.4, 12 + Math.max.apply(null, items.map(function (d) { return measure(s, d.label); })));
    var left = labelW, right = 44, plotW = W - left - right, max = opts.max;
    [0, 0.25, 0.5, 0.75, 1].forEach(function (f) {
      var x = left + plotW * f;
      el('line', {x1: x, x2: x, y1: top, y2: H - 20, 'class': f === 0 ? 'axis' : 'grid'}, s);
      text(s, x, H - 6, String(Math.round(max * f)), '', 'middle');
    });
    items.forEach(function (d, i) {
      var y = top + row * i + (row - bh) / 2, w = plotW * Math.min(d.value, max) / max;
      var hit = el('rect', {x: 0, y: top + row * i, width: W, height: row, 'class': 'hit'}, s);
      var mark = el('path', {d: barPath(left, y, Math.max(w, 1), bh, true), fill: css('--series-1'), 'class': 'mark'}, s);
      text(s, left - 8, y + bh - 3, d.label, 'label', 'end');
      text(s, left + w + 6, y + bh - 3, String(d.value), 'value');
      hover(hit, [mark], d.label, [{label: 'mean average', value: String(d.value)},
                                   {label: 'students', value: String(d.students)}]);
    });
  }

  // ---- subjects: grade mix (100% stacked) + average -------------------------
  function subjects(id, items) {
    var container = document.getElementById(id);
    if (!container || !items.length) return;
    var legend = document.getElementById('legend-mix');
    var used = GRADES.filter(function (g) { return items.some(function (s) { return s.grades[g]; }); });
    legend.textContent = '';
    used.forEach(function (g) {
      var span = document.createElement('span'), key = document.createElement('i');
      key.style.background = gradeColor(g);
      span.appendChild(key);
      span.appendChild(document.createTextNode(GRADE_NAMES[g]));
      legend.appendChild(span);
    });
    var W = width(container), row = 30, bh = 16, top = 22;
    var H = top + items.length * row + 6;
    var s = svg(container, W, H);
    var labelW = Math.min(W * 0.32, 12 + Math.max.apply(null, items.map(function (d) { return measure(s, d.name); })));
    var right = 64, left = labelW, plotW = W - left - right;
    text(s, left, 12, 'Grade mix (share of students)', '');
    text(s, W - 4, 12, 'Average', '', 'end');
    items.forEach(function (d, i) {
      var y = top + row * i + (row - bh) / 2, x = left, marks = [];
      var hit = el('rect', {x: 0, y: top + row * i, width: W, height: row, 'class': 'hit'}, s);
      var segments = used.filter(function (g) { return d.grades[g]; });
      segments.forEach(function (g, k) {
        var w = plotW * d.grades[g] / d.students, last = k === segments.length - 1;
        var drawW = Math.max(last ? w : w - 2, 0.5);   // 2px surface gap between segments
        marks.push(el('path', {d: barPath(x, y, drawW, bh, last), fill: gradeColor(g), 'class': 'mark'}, s));
        x += w;
      });
      text(s, left - 8, y + bh - 3, d.name, 'label', 'end');
      text(s, W - 4, y + bh - 3, d.average.toFixed(1), 'value', 'end');
      var rows = [{label: 'average total', value: d.average.toFixed(1)},
                  {label: 'passed (E or better)', value: d.pass_rate + '%'},
                  {label: 'students', value: String(d.students)}];
      segments.forEach(function (g) {
        rows.push({label: GRADE_NAMES[g], value: d.grades[g] + ' (' + Math.round(d.grades[g] * 100 / d.students) + '%)',
                   color: gradeColor(g)});
      });
      hover(hit, marks, d.name, rows);
    });
  }

  function draw() {
    var totalResults = data.grades.reduce(function (a, g) { return a + g.count; }, 0);
    columns('chart-grades', data.grades.filter(function (g) { return g.grade !== 'ABS' || g.count; })
      .map(function (g) { return {label: g.grade, value: g.count}; }), {
      color: function (d) { return gradeColor(d.label); },
      format: String,
      title: function (d) { return 'Grade ' + GRADE_NAMES[d.label]; },
      rows: function (d) { return [{label: 'results', value: String(d.value)},
                                   {label: 'of all results', value: Math.round(d.value * 100 / totalResults) + '%'}]; }
    });
    columns('chart-histogram', data.histogram.map(function (b) { return {label: String(b.low), name: b.label, value: b.count}; }), {
      color: function () { return css('--series-1'); },
      format: String,
      title: function (d) { return 'Average ' + d.name; },
      rows: function (d) { return [{label: 'students', value: String(d.value)}]; }
    });
    columns('chart-trend', data.trend.map(function (t) { return {label: t.label, value: t.value, students: t.students}; }), {
      max: 100,
      color: function () { return css('--series-1'); },
      format: function (v) { return v.toFixed(1); },
      title: function (d) { return d.label; },
      rows: function (d) { return [{label: 'mean average', value: d.value.toFixed(1)}, {label: 'students', value: String(d.students)}]; }
    });
    bars('chart-classes', data.classes, {max: 100});
    bars('chart-gender', data.gender, {max: 100});
    subjects('chart-subjects', data.subjects);
  }

  // Share column in the grades table.
  var total = data.grades.reduce(function (a, g) { return a + g.count; }, 0);
  document.querySelectorAll('[data-share]').forEach(function (cell) {
    cell.textContent = total ? Math.round(Number(cell.getAttribute('data-share')) * 100 / total) + '%' : '';
  });

  draw();
  var timer;
  window.addEventListener('resize', function () { clearTimeout(timer); timer = setTimeout(draw, 150); });
  window.addEventListener('scroll', hideTip, {passive: true});
})();
