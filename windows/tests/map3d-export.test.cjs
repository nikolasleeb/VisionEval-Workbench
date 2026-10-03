const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function fixture({ black = false, recoverWithReadPixels = false } = {}) {
  const source = {
    width: 20,
    height: 20,
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 20, height: 20 }),
    getContext: () => recoverWithReadPixels ? {
      RGBA: 6408, UNSIGNED_BYTE: 5121, NO_ERROR: 0,
      readPixels: (_x, _y, _w, _h, _format, _type, pixels) => pixels.fill(238),
      getError: () => 0,
    } : null,
  };
  const context = {
    color: black ? 0 : 238,
    clearRect() {},
    drawImage() { this.color = black ? 0 : 238; },
    getImageData() { return { data: [this.color, this.color, this.color, 255] }; },
    createImageData(width, height) { return { data: new Uint8ClampedArray(width * height * 4) }; },
    putImageData(image) { this.color = image.data[0]; },
    save() {}, restore() {}, strokeText() {}, fillText() {},
  };
  const output = {
    width: 0, height: 0,
    getContext: () => context,
    toDataURL: (mime) => `data:${mime};base64,captured`,
  };
  const window = {};
  const document = { createElement: () => output };
  const script = fs.readFileSync(path.join(__dirname, '..', 'public', 'map3d-export.js'), 'utf8');
  vm.runInNewContext(script, { window, document, setTimeout, clearTimeout, Uint8Array, Uint8ClampedArray });
  const map = {
    getCanvas: () => source,
    isStyleLoaded: () => true,
    once(_event, callback) { this.callback = callback; },
    triggerRepaint() { this.callback(); },
  };
  return { capture: window.WorkbenchMap3dExport.capture, map, context };
}

test('3D PNG and PDF capture the current rendered frame', async () => {
  const { capture, map } = fixture();
  const png = await capture(map, [], 'png');
  const pdf = await capture(map, [], 'pdf');
  assert.equal(png.content, 'data:image/png;base64,captured');
  assert.equal(pdf.content, 'data:image/jpeg;base64,captured');
  assert.equal(png.width, 20);
  assert.equal(png.height, 20);
});

test('3D SVG contains the captured view rather than the 2D map', async () => {
  const { capture, map } = fixture();
  const svg = await capture(map, [], 'svg');
  assert.match(svg.svgText, /<image href="data:image\/png;base64,captured"/);
});

test('black WebGL capture retries the pixel buffer and never exports an empty frame', async () => {
  const recovered = fixture({ black: true, recoverWithReadPixels: true });
  assert.equal((await recovered.capture(recovered.map, [], 'png')).content, 'data:image/png;base64,captured');
  const failed = fixture({ black: true });
  await assert.rejects(failed.capture(failed.map, [], 'png'), /black image/);
});

test('3D labels are included in the exported current view', async () => {
  const { capture, map, context } = fixture();
  let drawn = 0;
  context.fillText = () => { drawn += 1; };
  const marker = { getElement: () => ({ isConnected: true, textContent: 'Zone A\n12%', getBoundingClientRect: () => ({ left: 5, right: 15, top: 5, bottom: 15 }) }) };
  await capture(map, [marker], 'png');
  assert.equal(drawn, 2);
});
