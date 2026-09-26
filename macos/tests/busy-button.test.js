import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const root = new URL('../', import.meta.url);

function busyHelper(relativePath) {
  const source = readFileSync(new URL(relativePath, root), 'utf8');
  const functionSource = source.match(/function setBusy\(button, busy, label = "Working…"\) \{[\s\S]*?\n\}/)?.[0];
  assert.ok(functionSource, `Missing setBusy in ${relativePath}`);
  const setButtonAvailability = (button, enabled, reason = '') => {
    button.disabled = !enabled;
    if (enabled) delete button.dataset.disabledReason;
    else button.dataset.disabledReason = reason;
  };
  return new Function('setButtonAvailability', 'disabledReasonFor', `${functionSource}; return setBusy;`)(
    setButtonAvailability,
    () => '',
  );
}

for (const path of ['public/app.js']) {
  test(`${path} preserves the original button state across busy phases`, () => {
    const setBusy = busyHelper(path);
    const button = { textContent: 'Install asset package', disabled: false, dataset: {} };
    setBusy(button, true, 'Validating…');
    setBusy(button, true, 'Installing…');
    assert.equal(button.textContent, 'Installing…');
    assert.equal(button.disabled, true);
    setBusy(button, false);
    assert.equal(button.textContent, 'Install asset package');
    assert.equal(button.disabled, false);
    assert.equal(button.dataset.busy, undefined);
    setBusy(button, false);
    assert.equal(button.textContent, 'Install asset package');
  });

  test(`${path} restores an originally disabled button`, () => {
    const setBusy = busyHelper(path);
    const button = { textContent: 'Install asset package', disabled: true, dataset: { disabledReason: 'Not available yet' } };
    setBusy(button, true, 'Validating…');
    setBusy(button, true, 'Installing…');
    setBusy(button, false);
    assert.equal(button.textContent, 'Install asset package');
    assert.equal(button.disabled, true);
    assert.equal(button.dataset.disabledReason, 'Not available yet');
  });
}

test('Hypercube axis controls align at the top despite numeric-column guidance', () => {
  const styles = readFileSync(new URL('public/styles.css', root), 'utf8');
  assert.match(styles, /\.hypercube-axis-row\s*\{[^}]*align-items:\s*start;/);
  assert.match(styles, /\.hypercube-axis-row \.danger\s*\{[^}]*margin-top:\s*25px;/);
});
