(function (root) {
  "use strict";

  function escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
  }

  function lines(value, width, fontSize = 17, limit = 2) {
    const max = Math.max(8, Math.floor((width - 24) / (fontSize * .55)));
    const words = String(value ?? "").trim().split(/\s+/);
    const result = [];
    let current = "";
    for (const word of words) {
      if (current && `${current} ${word}`.length > max) {
        result.push(current);
        current = word;
      } else current = current ? `${current} ${word}` : word;
    }
    if (current) result.push(current);
    if (!result.length) result.push("");
    if (result.length > limit) {
      result.length = limit;
      result[limit - 1] = `${result[limit - 1].slice(0, Math.max(0, max - 1))}…`;
    }
    return result;
  }

  function text(value, x, y, width, options = {}) {
    const fontSize = options.fontSize || 17;
    const displayed = lines(value, width, fontSize, options.limit || 2);
    const anchor = options.anchor || "start";
    const fill = options.fill || "#172331";
    const weight = options.weight || 400;
    return `<text x="${x}" y="${y}" fill="${fill}" font-family="Arial,sans-serif" font-size="${fontSize}" font-weight="${weight}" text-anchor="${anchor}">${displayed.map((line, index) => `<tspan x="${x}" dy="${index ? fontSize + 3 : 0}">${escape(line)}</tspan>`).join("")}</text>`;
  }

  function numeric(value) {
    const parsed = Number(String(value ?? "").replace(/,/g, "").replace(/%$/, ""));
    return Number.isFinite(parsed) ? parsed : null;
  }

  function render({ title, subtitle, headers, rows, mode = "table" }) {
    const width = 1600;
    const left = 45;
    const top = 133;
    const tableWidth = width - left * 2;
    const rowHeight = 58;
    const height = Math.max(1000, top + (rows.length + 1) * rowHeight + 55);
    const columns = Math.max(1, headers.length, ...rows.map((row) => row.cells.length));
    const firstWidth = columns === 1 ? tableWidth : Math.min(mode === "heatmap" ? 350 : 290, tableWidth * .35);
    const otherWidth = columns === 1 ? 0 : (tableWidth - firstWidth) / (columns - 1);
    const xAt = (column) => left + (column === 0 ? 0 : firstWidth + (column - 1) * otherWidth);
    const widthAt = (column) => column === 0 ? firstWidth : otherWidth;
    const allValues = mode === "heatmap" ? rows.flatMap((row) => row.cells.slice(1).map((cell) => numeric(cell))).filter((value) => value !== null) : [];
    const maxAbs = Math.max(1, ...allValues.map(Math.abs));
    const parts = [`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`, `<rect width="${width}" height="${height}" fill="#fff"/>`, text(title, left, 55, tableWidth, { fontSize: 30, weight: 700, limit: 1 }), text(subtitle, left, 88, tableWidth, { fontSize: 17, fill: "#53657a", limit: 1 })];
    for (let rowIndex = -1; rowIndex < rows.length; rowIndex += 1) {
      const row = rowIndex < 0 ? { cells: headers } : rows[rowIndex];
      const y = top + (rowIndex + 1) * rowHeight;
      for (let column = 0; column < columns; column += 1) {
        const x = xAt(column);
        const cellWidth = widthAt(column);
        const value = row.cells[column] ?? "";
        let fill = rowIndex < 0 ? "#eaf1f8" : rowIndex % 2 ? "#f6f9fc" : "#fff";
        if (rowIndex >= 0 && mode === "heatmap" && column > 0) {
          const amount = numeric(value);
          if (amount !== null) {
            const intensity = Math.round(13 + Math.min(1, Math.abs(amount) / maxAbs) * 53);
            fill = amount < 0 ? `rgb(255,${255 - intensity},${255 - intensity})` : `rgb(${255 - intensity},${255 - Math.round(intensity * .55)},255)`;
          }
        }
        if (rowIndex >= 0 && row.selected) fill = "#dff2e8";
        parts.push(`<rect x="${x}" y="${y}" width="${cellWidth}" height="${rowHeight}" fill="${fill}" stroke="#cad8e6"/>`);
        parts.push(text(value, x + 12, y + 23, cellWidth, { fontSize: rowIndex < 0 ? 16 : 17, weight: rowIndex < 0 || column === 0 ? 700 : 400 }));
      }
    }
    parts.push("</svg>");
    return { svgText: parts.join(""), width, height };
  }

  const api = { render };
  root.WorkbenchHypercubeVisualExport = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
