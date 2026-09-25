import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const source = readFileSync(new URL('../public/app.js', import.meta.url), 'utf8');
const visualSource = source.match(/function hypercubeVisualSvg\(\)\{[\s\S]*?\n\}\n(?=async function exportHypercubeVisual)/)?.[0];
assert.ok(visualSource, 'Missing Hypercube visual export renderer');

function render(view) {
  const nodes = {
    hypercubeAnalysisView: view,
    hypercubeAnalysisTitle: { textContent: 'Household / AveVehCostPM' },
    hypercubeAnalysisSubtitle: { textContent: 'Percent change · 25 cases' },
  };
  const escapeHtml = (value) => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  const state = { hypercubeAnalysis: { matrix: { cells: [{ variationId: 'case-1', value: -12 }] } } };
  const fn = new Function('$', 'escapeHtml', 'state', `${visualSource}; return hypercubeVisualSvg;`)(
    (id) => nodes[id], escapeHtml, state,
  );
  return fn();
}

test('Hypercube table export is self-contained SVG without HTML foreignObject', () => {
  const header = { cells: [{ textContent: 'FuelCost', querySelector: () => null }, { textContent: 'FuelTax', querySelector: () => null }] };
  const data = { cells: [
    { textContent: '10', querySelector: () => null },
    { textContent: '-12%', querySelector: () => ({ dataset: { hypercubeCell: 'case-1' } }) },
  ] };
  const output = render({ querySelector: () => null, querySelectorAll: () => [header, data] });
  assert.equal(output.width, 1600);
  assert.equal(output.height, 1000);
  assert.match(output.svgText, /FuelTax/);
  assert.match(output.svgText, /-12%/);
  assert.match(output.svgText, /#fde8e9/);
  assert.doesNotMatch(output.svgText, /foreignObject|<table|<button/);
});

test('Hypercube curve export embeds vector paths without HTML', () => {
  const output = render({ querySelector: () => ({ innerHTML: '<polyline points="1,2 3,4"/>' }) });
  assert.match(output.svgText, /<polyline points="1,2 3,4"\/>/);
  assert.doesNotMatch(output.svgText, /foreignObject|<div/);
});
