(function initializePolygonLabels(global) {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  let clipSequence = 0;

  function polygons(geometry) {
    if (!geometry) return [];
    if (geometry.type === "Polygon") return [geometry.coordinates || []];
    if (geometry.type === "MultiPolygon") return geometry.coordinates || [];
    return [];
  }

  function pointInRing(point, ring, project) {
    let inside = false;
    for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index++) {
      const [xi, yi] = project(ring[index]), [xj, yj] = project(ring[previous]);
      if ((yi > point[1]) !== (yj > point[1]) && point[0] < (xj - xi) * (point[1] - yi) / ((yj - yi) || Number.EPSILON) + xi) inside = !inside;
    }
    return inside;
  }

  function contains(point, feature, project) {
    return polygons(feature?.geometry).some((rings) => rings.length && pointInRing(point, rings[0], project) && !rings.slice(1).some((ring) => pointInRing(point, ring, project)));
  }

  function segmentDistance(point, start, end) {
    let x = start[0], y = start[1], dx = end[0] - x, dy = end[1] - y;
    if (dx || dy) {
      const ratio = Math.max(0, Math.min(1, ((point[0] - x) * dx + (point[1] - y) * dy) / (dx * dx + dy * dy)));
      x += dx * ratio; y += dy * ratio;
    }
    dx = point[0] - x; dy = point[1] - y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function signedDistance(point, feature, project) {
    let distance = Infinity;
    polygons(feature?.geometry).flat().forEach((ring) => {
      const vertices = ring.map(project);
      for (let index = 0, previous = vertices.length - 1; index < vertices.length; previous = index++) distance = Math.min(distance, segmentDistance(point, vertices[previous], vertices[index]));
    });
    return (contains(point, feature, project) ? 1 : -1) * distance;
  }

  function interiorPoint(feature, project) {
    const points = polygons(feature?.geometry).flat(2).map(project);
    if (!points.length) return {x: 0, y: 0, radius: 0};
    const xs = points.map((point) => point[0]), ys = points.map((point) => point[1]);
    const bounds = {minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys)};
    let best = {x: (bounds.minX + bounds.maxX) / 2, y: (bounds.minY + bounds.maxY) / 2, radius: -Infinity};
    const span = Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY);
    let step = Math.max(span / 7, 0.001);
    for (let pass = 0; pass < 6; pass += 1) {
      const minX = pass ? best.x - step * 2 : bounds.minX, maxX = pass ? best.x + step * 2 : bounds.maxX;
      const minY = pass ? best.y - step * 2 : bounds.minY, maxY = pass ? best.y + step * 2 : bounds.maxY;
      for (let x = minX; x <= maxX; x += step) for (let y = minY; y <= maxY; y += step) {
        const radius = signedDistance([x, y], feature, project);
        if (radius > best.radius) best = {x, y, radius};
      }
      step /= 2;
    }
    return best.radius > 0 ? best : {...best, radius: 0};
  }

  function overlaps(left, right) {
    return left.left < right.right && left.right > right.left && left.top < right.bottom && left.bottom > right.top;
  }

  function padded(rect, padding = 3) {
    return {left: rect.left - padding, right: rect.right + padding, top: rect.top - padding, bottom: rect.bottom + padding};
  }

  function shortenLocality(value) {
    return String(value || "").replace(/\s+(County|City|city)$/i, "").replace(/^City of\s+/i, "").trim();
  }

  function layout({group, entries, view, viewport, project, pathFor, className = "region-map-label", minFontPx = 8, maxFontPx = 12, maxLabels = 250}) {
    if (!group || !view || !viewport?.width || !viewport?.height) return [];
    group.replaceChildren();
    const scale = Math.max(0.0001, Math.min(viewport.width / view.width, viewport.height / view.height));
    const occupied = [], accepted = [];
    const prepared = entries.map((entry) => ({...entry, label: entry.label || interiorPoint(entry.feature, project)}))
      .filter((entry) => entry.label.radius > 0)
      .sort((left, right) => (Number(right.priority) || 0) - (Number(left.priority) || 0) || right.label.radius - left.label.radius);

    for (const entry of prepared) {
      if (accepted.length >= maxLabels) break;
      const {x, y, radius} = entry.label;
      if (x < view.x || x > view.x + view.width || y < view.y || y > view.y + view.height) continue;
      const radiusPx = radius * scale;
      if (radiusPx < minFontPx * 0.75) continue;
      const fontPx = Math.max(minFontPx, Math.min(maxFontPx, radiusPx * 0.24));
      for (const lines of entry.candidates || []) {
        if (!lines?.length) continue;
        const clipId = `polygon-label-clip-${++clipSequence}`;
        const clip = document.createElementNS(SVG_NS, "clipPath"), path = document.createElementNS(SVG_NS, "path");
        clip.id = clipId; path.setAttribute("d", pathFor(entry.feature)); clip.append(path);
        const text = document.createElementNS(SVG_NS, "text");
        text.setAttribute("class", `${className}${entry.className ? ` ${entry.className}` : ""}`);
        text.setAttribute("x", x.toFixed(2)); text.setAttribute("y", y.toFixed(2)); text.setAttribute("text-anchor", "middle");
        text.setAttribute("clip-path", `url(#${clipId})`); text.style.fontSize = `${fontPx / scale}px`; text.style.strokeWidth = `${3 / scale}px`;
        const firstDy = -((lines.length - 1) * 0.54);
        lines.forEach((line, index) => {
          const span = document.createElementNS(SVG_NS, "tspan");
          span.setAttribute("x", x.toFixed(2)); span.setAttribute("dy", `${index ? 1.08 : firstDy}em`); span.textContent = String(line); text.append(span);
        });
        group.append(clip, text);
        const measured = text.getBoundingClientRect(), box = padded(measured);
        const fits = measured.width > 0 && measured.height > 0 && measured.width <= radiusPx * 1.85 && measured.height <= radiusPx * 1.85;
        if (fits && !occupied.some((item) => overlaps(item, box))) {
          occupied.push(box); accepted.push({entry, text, clip, box}); break;
        }
        text.remove(); clip.remove();
      }
    }
    return accepted;
  }

  global.WorkbenchPolygonLabels = Object.freeze({interiorPoint, layout, shortenLocality});
})(window);
