import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const root = new URL('../', import.meta.url);
const app = readFileSync(new URL('public/app.js', root), 'utf8');
const markup = readFileSync(new URL('public/index.html', root), 'utf8');

const helper = app.match(/function compatibleRegionSources\(sources, regionId\) \{[\s\S]*?\n\}/)?.[0];
assert.ok(helper, 'Missing region source compatibility helper');
const compatibleRegionSources = new Function(`${helper}; return compatibleRegionSources;`)();

test('regional package keeps its own Virginia inputs and hides an incompatible workspace library', () => {
  const sources = [
    { id: 'package:virginia-mpo-regions', kind: 'package' },
    { id: 'workspace:PlanRVA', kind: 'workspace', supportedRegionIds: ['richmond-mpo'] },
  ];
  assert.deepEqual(compatibleRegionSources(sources, 'charlottesville-albemarle-mpo').map((source) => source.id), [sources[0].id]);
  assert.deepEqual(compatibleRegionSources(sources, 'richmond-mpo').map((source) => source.id), sources.map((source) => source.id));
});

test('input data source is visible outside the collapsed output options', () => {
  assert.ok(markup.indexOf('id="regionSourceLibraryField"') < markup.indexOf('id="regionOutputOptions"'));
  assert.match(markup, /Input data source<select id="regionSourceLibrary"/);
  assert.doesNotMatch(app, /state\.regionBuilderSourceLibraryId \|\| sourceSelect\.value/);
});
