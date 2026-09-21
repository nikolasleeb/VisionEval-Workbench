import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, PngImagePlugin


WIDTH = 1600
HEIGHT = 1000
PADDING = 70
COUNTIES_PATH = Path("/tmp/va_counties.geojson")
MPO_PATH = Path("/tmp/vdot_mpo_study_areas.geojson")
OUTPUT_PATH = Path("site-assets/virginia-official-mpo-study-areas-map.png")

PALETTE = [
    "#1769aa", "#0097a7", "#2e7d32", "#7b1fa2", "#ef6c00",
    "#00897b", "#3949ab", "#c62828", "#6d4c41", "#5e35b1",
    "#0277bd", "#558b2f", "#ad1457", "#f9a825", "#00695c",
]


def iter_polygons(geometry):
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        yield from geometry["coordinates"]


def iter_points(geometry):
    for polygon in iter_polygons(geometry):
        for ring in polygon:
            yield from ring


with COUNTIES_PATH.open() as handle:
    counties = json.load(handle)
with MPO_PATH.open() as handle:
    mpo_areas = json.load(handle)["features"]

state_points = [point for feature in counties["features"] for point in iter_points(feature["geometry"])]
mean_latitude = sum(point[1] for point in state_points) / len(state_points)
x_factor = math.cos(math.radians(mean_latitude))
projected = [(lon * x_factor, lat) for lon, lat in state_points]
min_x = min(point[0] for point in projected)
max_x = max(point[0] for point in projected)
min_y = min(point[1] for point in projected)
max_y = max(point[1] for point in projected)
scale = min((WIDTH - 2 * PADDING) / (max_x - min_x), (HEIGHT - 2 * PADDING) / (max_y - min_y))
draw_width = (max_x - min_x) * scale
draw_height = (max_y - min_y) * scale
offset_x = (WIDTH - draw_width) / 2
offset_y = (HEIGHT - draw_height) / 2


def project(point):
    lon, lat = point[:2]
    x = offset_x + (lon * x_factor - min_x) * scale
    y = HEIGHT - (offset_y + (lat - min_y) * scale)
    return (round(x), round(y))


def draw_geometry(draw, geometry, fill, outline=None, width=1):
    for polygon in iter_polygons(geometry):
        if not polygon:
            continue
        outer = [project(point) for point in polygon[0]]
        draw.polygon(outer, fill=fill)
        if outline:
            draw.line(outer, fill=outline, width=width, joint="curve")
        for hole in polygon[1:]:
            inner = [project(point) for point in hole]
            draw.polygon(inner, fill=0 if isinstance(fill, int) else "#f7fafc")
            if outline:
                draw.line(inner, fill=outline, width=width, joint="curve")


state_mask = Image.new("L", (WIDTH, HEIGHT), 0)
for feature in counties["features"]:
    feature_mask = Image.new("L", (WIDTH, HEIGHT), 0)
    draw_geometry(ImageDraw.Draw(feature_mask), feature["geometry"], 255)
    state_mask = ImageChops.lighter(state_mask, feature_mask)
state_silhouette = state_mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))

canvas = Image.new("RGBA", (WIDTH, HEIGHT), "#f7fafc")
shadow = state_silhouette.filter(ImageFilter.GaussianBlur(14))
shadow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (18, 43, 66, 0))
shadow_layer.putalpha(shadow.point(lambda value: int(value * 0.22)))
canvas.alpha_composite(shadow_layer, (8, 12))

state_layer = Image.new("RGBA", (WIDTH, HEIGHT), (225, 236, 246, 255))
state_layer.putalpha(state_silhouette)
canvas.alpha_composite(state_layer)

county_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
county_draw = ImageDraw.Draw(county_overlay)
for feature in counties["features"]:
    for polygon in iter_polygons(feature["geometry"]):
        for ring in polygon:
            county_draw.line([project(point) for point in ring], fill=(73, 98, 120, 60), width=1)
canvas.alpha_composite(county_overlay)

mpo_masks = []
for feature in mpo_areas:
    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    draw_geometry(ImageDraw.Draw(mask), feature["geometry"], 255)
    mpo_masks.append(ImageChops.multiply(mask, state_silhouette))

for color, mask in zip(PALETTE, mpo_masks):
    rgb = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
    fill_layer = Image.new("RGBA", (WIDTH, HEIGHT), (*rgb, 82))
    fill_layer.putalpha(mask.point(lambda value: int(value * 0.40)))
    canvas.alpha_composite(fill_layer)

for color, mask in zip(PALETTE, mpo_masks):
    rgb = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
    expanded = mask.filter(ImageFilter.MaxFilter(9))
    contracted = mask.filter(ImageFilter.MinFilter(9))
    boundary = ImageChops.subtract(expanded, contracted)
    outline_layer = Image.new("RGBA", (WIDTH, HEIGHT), (*rgb, 235))
    outline_layer.putalpha(boundary.point(lambda value: int(value * 0.92)))
    canvas.alpha_composite(outline_layer)

state_expanded = state_silhouette.filter(ImageFilter.MaxFilter(11))
state_contracted = state_silhouette.filter(ImageFilter.MinFilter(11))
state_boundary = ImageChops.subtract(state_expanded, state_contracted)
state_outline = Image.new("RGBA", (WIDTH, HEIGHT), (14, 52, 91, 255))
state_outline.putalpha(state_boundary)
canvas.alpha_composite(state_outline)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
metadata = PngImagePlugin.PngInfo()
metadata.add_text("Title", "Virginia official MPO study areas")
metadata.add_text("MPO source", "Virginia Department of Transportation MPO Study Area Boundary feature service")
metadata.add_text("Geography", "U.S. Census Bureau TIGERweb county-equivalent geography, January 1 2026 vintage")
metadata.add_text("Note", "Illustrative raster rendering; verify policy decisions against the current VDOT source")
canvas.convert("RGB").save(OUTPUT_PATH, "PNG", optimize=True, pnginfo=metadata)
print(OUTPUT_PATH.resolve())
