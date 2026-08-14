# svgexport.py
# Exports smoothed G-code paths to SVG format.

import math
import os


# ------------------------------------------------------------
# Utility: feedrate → RGB colour
# ------------------------------------------------------------

def feedrate_to_rgb(F, F_min, F_max):
    """
    Maps feedrate to an RGB colour:
        red → yellow → green
    """
    F_range = F_max - F_min if F_max > F_min else 1
    frac = (F - F_min) / F_range
    r = int(255 * (1 - frac))
    g = int(255 * frac)
    b = 0
    return f"rgb({r},{g},{b})"


# ------------------------------------------------------------
# Export SVG
# ------------------------------------------------------------

def export_svg(output_folder, input_filename, smoothed_points, bearings, feedrates, arrow_step=10):
    """
    Exports an SVG file containing:
      - smoothed path polyline
      - bearing arrows (every N points)
      - feedrate colour coding

    The SVG filename matches the input filename but with .svg extension.
    """

    # Build output path
    base_name = os.path.splitext(input_filename)[0]
    svg_path = os.path.join(output_folder, base_name + ".svg")

    # Extract XY
    xs = [p[0] for p in smoothed_points]
    ys = [p[1] for p in smoothed_points]

    # SVG header
    svg_lines = []
    svg_lines.append('<?xml version="1.0" standalone="no"?>')
    svg_lines.append('<svg xmlns="http://www.w3.org/2000/svg" version="1.1">')

    # ------------------------------------------------------------
    # Polyline for smoothed path
    # ------------------------------------------------------------

    poly_points = " ".join([f"{x},{y}" for x, y in smoothed_points])
    svg_lines.append(f'<polyline points="{poly_points}" '
                     f'style="fill:none;stroke:blue;stroke-width:1.5" />')

    # ------------------------------------------------------------
    # Bearing arrows
    # ------------------------------------------------------------

    F_min = min(feedrates)
    F_max = max(feedrates)

    for i in range(0, len(smoothed_points), arrow_step):
        x, y = smoothed_points[i]
        angle = bearings[i]
        F = feedrates[i]

        # Feedrate colour
        color = feedrate_to_rgb(F, F_min, F_max)

        # Arrow orientation (angle - 90°)
        plot_angle = (angle - 90) % 360
        dx = math.cos(math.radians(plot_angle)) * 1.0
        dy = math.sin(math.radians(plot_angle)) * 1.0

        x2 = x + dx
        y2 = y + dy

        svg_lines.append(
            f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" '
            f'style="stroke:{color};stroke-width:0.8" />'
        )

        # Arrowhead
        hx = x2 + math.cos(math.radians(plot_angle - 150)) * 0.5
        hy = y2 + math.sin(math.radians(plot_angle - 150)) * 0.5

        hx2 = x2 + math.cos(math.radians(plot_angle + 150)) * 0.5
        hy2 = y2 + math.sin(math.radians(plot_angle + 150)) * 0.5

        svg_lines.append(
            f'<polyline points="{x2},{y2} {hx},{hy} {hx2},{hy2}" '
            f'style="fill:{color};stroke:{color};stroke-width:0.5" />'
        )

    # ------------------------------------------------------------
    # Close SVG
    # ------------------------------------------------------------

    svg_lines.append('</svg>')

    # Write file
    with open(svg_path, "w") as f:
        for line in svg_lines:
            f.write(line + "\n")

    return svg_path

