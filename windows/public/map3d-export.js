(function (global) {
  "use strict";

  function isBlackFrame(context, width, height) {
    const points = [0.1, 0.25, 0.5, 0.75, 0.9];
    for (const y of points) {
      for (const x of points) {
        const pixel = context.getImageData(Math.min(width - 1, Math.floor(x * width)), Math.min(height - 1, Math.floor(y * height)), 1, 1).data;
        if (pixel[0] > 12 || pixel[1] > 12 || pixel[2] > 12) return false;
      }
    }
    return true;
  }

  function readWebglPixels(map, context, width, height) {
    const canvas = map.getCanvas();
    const gl = map.painter?.context?.gl || canvas.getContext("webgl2") || canvas.getContext("webgl");
    if (!gl) return false;
    const pixels = new Uint8Array(width * height * 4);
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    if (gl.getError() !== gl.NO_ERROR) return false;
    const image = context.createImageData(width, height);
    const rowSize = width * 4;
    for (let row = 0; row < height; row += 1) {
      image.data.set(pixels.subarray((height - row - 1) * rowSize, (height - row) * rowSize), row * rowSize);
    }
    context.putImageData(image, 0, 0);
    return true;
  }

  function drawLabels(context, canvas, markers) {
    const canvasRect = canvas.getBoundingClientRect();
    if (!canvasRect.width || !canvasRect.height) return;
    const scaleX = canvas.width / canvasRect.width;
    const scaleY = canvas.height / canvasRect.height;
    context.save();
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font = `${Math.max(11, Math.round(11 * scaleY))}px ui-monospace, Consolas, monospace`;
    context.lineJoin = "round";
    context.lineWidth = Math.max(3, 3 * scaleY);
    for (const marker of markers) {
      const element = marker.getElement?.();
      if (!element || !element.isConnected || !element.textContent) continue;
      const rect = element.getBoundingClientRect();
      const x = ((rect.left + rect.right) / 2 - canvasRect.left) * scaleX;
      const y = ((rect.top + rect.bottom) / 2 - canvasRect.top) * scaleY;
      if (x < 0 || x > canvas.width || y < 0 || y > canvas.height) continue;
      const lines = element.textContent.split("\n");
      const lineHeight = 13 * scaleY;
      lines.forEach((line, index) => {
        const lineY = y + (index - (lines.length - 1) / 2) * lineHeight;
        context.strokeStyle = "#ffffff";
        context.strokeText(line, x, lineY);
        context.fillStyle = "#172231";
        context.fillText(line, x, lineY);
      });
    }
    context.restore();
  }

  async function capture(map, markers = [], format = "png") {
    const source = map?.getCanvas?.();
    if (!source?.width || !source?.height) throw new Error("The 3D map is not ready to export.");
    if (map.isStyleLoaded && !map.isStyleLoaded()) throw new Error("Wait for the 3D map to finish loading before exporting.");
    const output = document.createElement("canvas");
    output.width = source.width;
    output.height = source.height;
    const context = output.getContext("2d", { willReadFrequently: true });
    if (!context) throw new Error("Could not prepare the 3D map image.");

    for (let attempt = 0; attempt < 2; attempt += 1) {
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error("The 3D map did not finish rendering for export.")), 5000);
        map.once("render", () => { clearTimeout(timeout); resolve(); });
        map.triggerRepaint();
      });
      context.clearRect(0, 0, output.width, output.height);
      context.drawImage(source, 0, 0, output.width, output.height);
      if (!isBlackFrame(context, output.width, output.height)) break;
      try { readWebglPixels(map, context, output.width, output.height); } catch (_) { /* A second repaint may still succeed. */ }
      if (!isBlackFrame(context, output.width, output.height)) break;
      if (attempt === 1) throw new Error("The 3D renderer returned a black image. No export was saved; try moving the map and exporting again.");
    }

    drawLabels(context, source, markers);
    const width = output.width, height = output.height;
    if (format === "svg") {
      const content = output.toDataURL("image/png");
      return { width, height, svgText: `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><image href="${content}" width="${width}" height="${height}"/></svg>` };
    }
    return { width, height, content: output.toDataURL(format === "pdf" ? "image/jpeg" : "image/png", .94) };
  }

  global.WorkbenchMap3dExport = { capture };
})(window);
