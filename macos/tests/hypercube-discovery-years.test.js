import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const app = readFileSync(new URL('../public/app.js', import.meta.url), 'utf8');
const helper = app.match(/function hypercubeDiscoveryYears\(options\)\{[\s\S]*?\n\}/)?.[0];
assert.ok(helper);
const years = new Function(`${helper}; return hypercubeDiscoveryYears;`)();

test('base-year-only outputs do not hide future years from discovery', () => {
  assert.deepEqual(years({variables:[{years:['2024']},{years:['2024','2045']}]}), ['2024','2045']);
});
test('catalog years are deduplicated, normalized and sorted', () => {
  assert.deepEqual(years({years:[2045,2024],variables:[{years:['2045','2050']},{years:[]}]}), ['2024','2045','2050']);
  assert.deepEqual(years({}), []);
});
