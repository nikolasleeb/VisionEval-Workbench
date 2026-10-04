const assert = require('node:assert/strict');
const test = require('node:test');
const { render } = require('../public/hypercube-visual-export.js');

test('Hypercube heatmap export is self-contained SVG without foreignObject', () => {
  const output = render({
    title: 'Fuel Cost & Tax', subtitle: 'Percent change · 10 cases',
    headers: ['Fuel tax ↓ / Fuel cost →', '10%', '25%'],
    rows: [{ cells: ['0%', '2.5%', '-1.2%'] }, { cells: ['50%', 'Missing', '4.1%'], selected: true }],
    mode: 'heatmap',
  });
  assert.equal(output.width, 1600);
  assert.match(output.svgText, /Fuel Cost &amp; Tax/);
  assert.match(output.svgText, /2\.5%/);
  assert.match(output.svgText, /Missing/);
  assert.match(output.svgText, /#dff2e8/);
  assert.doesNotMatch(output.svgText, /foreignObject|<image\b|(?:href|src)=["']https?:\/\//);
});

test('Hypercube table export escapes source labels and expands for many cases', () => {
  const output = render({
    title: '<script>alert(1)</script>', subtitle: 'Cases',
    headers: ['Case', 'Metric'],
    rows: Array.from({ length: 30 }, (_, index) => ({ cells: [`Case ${index + 1}`, String(index)] })),
    mode: 'table',
  });
  assert.ok(output.height > 1000);
  assert.match(output.svgText, /&lt;script&gt;/);
  assert.doesNotMatch(output.svgText, /<script>/);
  assert.match(output.svgText, /Case 30/);
});
