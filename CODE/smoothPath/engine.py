# engine.py
# Core motion-planning engine for G-code smoothing.

import math
from decimal import Decimal

import numpy as np

X_MIN = 0.0
X_MAX = 265.0
Y_MIN = 0.0
Y_MAX = 225.0


# ------------------------------------------------------------
# 1. Parse G1 lines into numeric points
# ------------------------------------------------------------

def parse_g1_lines(path_block):
    """
    Converts G1 lines into (X, Y, Z) tuples.
    Returns a list of (x, y, z).
    """
    points = []

    for line in path_block:
        if not line.startswith("G1"):
            continue

        x = extract_value(line, "X")
        y = extract_value(line, "Y")
        z = extract_value(line, "Z")

        if x is not None and y is not None:
            points.append((x, y, z if z is not None else 0.0))

    return points


def extract_value_text(line, letter):
    """Extracts the original numeric text after a letter, e.g. X123.45."""
    try:
        idx = line.index(letter)
        rest = line[idx+1:]
        num = ""
        for ch in rest:
            if ch in "0123456789.-":
                num += ch
            else:
                break
        float(num)
        return num
    except ValueError:
        return None


def extract_value(line, letter):
    """Extracts numeric value after a letter, e.g. X123.45."""
    value = extract_value_text(line, letter)
    return float(value) if value is not None else None


# ------------------------------------------------------------
# 2. Catmull–Rom spline interpolation
# ------------------------------------------------------------

def catmull_rom_spline(points, samples_per_segment=200):
    """
    Generates a dense Catmull–Rom curve within the controller's XY limits.
    Out-of-range input points are clamped; segments that would overshoot are
    blended toward their straight-line paths.
    Input: list of (x, y)
    Output: list of (x, y)
    """
    points = [(max(X_MIN, min(X_MAX, x)), max(Y_MIN, min(Y_MAX, y)))
              for x, y in points]
    if len(points) < 4:
        return points

    curve = []

    def interpolate(p0, p1, p2, p3, t):
        t2 = t * t
        t3 = t2 * t
        return (
            0.5 * (2*p1 +
                   (-p0 + p2)*t +
                   (2*p0 - 5*p1 + 4*p2 - p3)*t2 +
                   (-p0 + 3*p1 - 3*p2 + p3)*t3)
        )

    for i in range(1, len(points)-2):
        p0, p1, p2, p3 = points[i-1], points[i], points[i+1], points[i+2]
        segment = []
        # Find the largest spline blend that keeps every sample in bounds.
        smoothing = 1.0
        for t in np.linspace(0, 1, samples_per_segment):
            x = interpolate(p0[0], p1[0], p2[0], p3[0], t)
            y = interpolate(p0[1], p1[1], p2[1], p3[1], t)
            linear_x = max(X_MIN, min(X_MAX, p1[0] + (p2[0] - p1[0]) * t))
            linear_y = max(Y_MIN, min(Y_MAX, p1[1] + (p2[1] - p1[1]) * t))
            for value, linear, lower, upper in (
                (x, linear_x, X_MIN, X_MAX), (y, linear_y, Y_MIN, Y_MAX)
            ):
                if value < lower:
                    smoothing = min(smoothing, (linear - lower) / (linear - value))
                elif value > upper:
                    smoothing = min(smoothing, (upper - linear) / (value - linear))
            segment.append((x, y, linear_x, linear_y))

        for x, y, linear_x, linear_y in segment:
            if smoothing == 1.0:
                bounded_x, bounded_y = x, y
            else:
                bounded_x = linear_x + smoothing * (x - linear_x)
                bounded_y = linear_y + smoothing * (y - linear_y)
            curve.append((max(X_MIN, min(X_MAX, bounded_x)),
                          max(Y_MIN, min(Y_MAX, bounded_y))))

    return curve


# ------------------------------------------------------------
# 3. Resample curve at fixed spacing
# ------------------------------------------------------------

def resample_fixed_spacing(curve, spacing):
    """
    Resamples a dense curve at fixed spacing.
    Returns a list of (x, y), including both endpoints.
    """
    if not math.isfinite(spacing) or spacing <= 0:
        raise ValueError("Resample spacing must be a positive finite number.")
    if len(curve) < 2:
        return curve

    distances = [0.0]
    for i in range(1, len(curve)):
        x0, y0 = curve[i-1]
        x1, y1 = curve[i]
        d = math.hypot(x1 - x0, y1 - y0)
        distances.append(distances[-1] + d)

    total_length = distances[-1]
    if total_length == 0:
        raise ValueError("The path has no length within the controller's XY limits.")

    resampled = [curve[0]]
    idx = 0

    for sample in range(1, math.ceil(total_length / spacing)):
        target = sample * spacing
        if target >= total_length:
            break
        while idx < len(distances)-1 and distances[idx] < target:
            idx += 1

        x0, y0 = curve[idx-1]
        x1, y1 = curve[idx]
        d0 = distances[idx-1]
        d1 = distances[idx]
        t = (target - d0) / (d1 - d0)
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        resampled.append((x, y))

    resampled.append(curve[-1])
    return resampled


# ------------------------------------------------------------
# 4. Curvature calculation
# ------------------------------------------------------------

def compute_curvature(points):
    """
    Computes curvature at each point.
    Returns list of curvature values.
    """
    if len(points) == 2:
        return [0.0, 0.0]

    curvature = []

    for i in range(1, len(points)-1):
        x0, y0 = points[i-1]
        x1, y1 = points[i]
        x2, y2 = points[i+1]

        a = math.hypot(x1 - x0, y1 - y0)
        b = math.hypot(x2 - x1, y2 - y1)
        c = math.hypot(x2 - x0, y2 - y0)

        if a*b*c == 0:
            curvature.append(0)
            continue

        area = abs((x1 - x0)*(y2 - y0) - (y1 - y0)*(x2 - x0)) / 2
        k = (4 * area) / (a * b * c)
        curvature.append(k)

    curvature.insert(0, curvature[0])
    curvature.append(curvature[-1])
    return curvature


# ------------------------------------------------------------
# 5. Feedrate mapping
# ------------------------------------------------------------

def map_feedrate(curvature, f_min, f_max):
    """
    Maps curvature to feedrate.
    """
    max_k = max(curvature) if max(curvature) > 0 else 1
    feedrates = []

    for k in curvature:
        norm = min(k / max_k, 1.0)
        F = f_min + (f_max - f_min) * (1 - norm)
        feedrates.append(F)

    return feedrates


# ------------------------------------------------------------
# 6. Bearing calculation (forward/reverse)
# ------------------------------------------------------------

def compute_bearings(points, direction):
    """
    Computes CNC bearing angles.
    direction = "forward" or "reverse"
    """
    bearings = []

    for i in range(1, len(points)):
        x0, y0 = points[i-1]
        x1, y1 = points[i]

        math_angle = math.degrees(math.atan2(y1 - y0, x1 - x0))

        if direction == "forward":
            cnc_angle = (math_angle + 90) % 360
        else:
            cnc_angle = (math_angle + 270) % 360

        bearings.append(cnc_angle)

    bearings.insert(0, bearings[0])
    return bearings


# ------------------------------------------------------------
# 7. Build smoothed G1 lines
# ------------------------------------------------------------

def build_g1_lines(resampled_xy, bearings, feedrates, initial_z, endpoint_coordinates):
    """
    Builds final G1 lines with X, Y, Z, F.
    initial_z overrides the first bearing.
    """
    lines = []

    # Override first bearing with original Z
    bearings[0] = initial_z

    for index, ((x, y), z, F) in enumerate(zip(resampled_xy, bearings, feedrates)):
        if index == 0:
            x_text, y_text = endpoint_coordinates[0]
        elif index == len(resampled_xy) - 1:
            x_text, y_text = endpoint_coordinates[1]
        else:
            x_text, y_text = f"{x:.3f}", f"{y:.3f}"
        line = f"G1 X{x_text} Y{y_text} Z{z:.3f} F{F:.1f}"
        lines.append(line)

    return lines


# ------------------------------------------------------------
# 8. Main smoothing pipeline
# ------------------------------------------------------------

def smooth_path(path_block, spacing, f_min, f_max, direction):
    """
    Smooth a path while preserving its exact input XY endpoints.
    Endpoints outside the controller limits are rejected.
    Returns list of smoothed G1 lines.
    """

    # Parse input G1 lines
    path_lines = [line for line in path_block if line.startswith("G1")]
    if len(path_lines) < 2:
        raise ValueError("At least two G1 points with X and Y coordinates are required.")

    endpoint_coordinates = []
    for line in (path_lines[0], path_lines[-1]):
        x_text = extract_value_text(line, "X")
        y_text = extract_value_text(line, "Y")
        if x_text is None or y_text is None:
            raise ValueError("The path's start and end must have X and Y coordinates.")
        if not (Decimal(str(X_MIN)) <= Decimal(x_text) <= Decimal(str(X_MAX))
                and Decimal(str(Y_MIN)) <= Decimal(y_text) <= Decimal(str(Y_MAX))):
            raise ValueError("The path's start and end must be within the controller's XY limits.")
        endpoint_coordinates.append((x_text, y_text))

    raw_points = parse_g1_lines(path_lines)
    # Extract XY only for spline
    xy_points = [(p[0], p[1]) for p in raw_points]

    # Initial Z from first G1
    initial_z = raw_points[0][2]

    # Duplicate endpoints so the spline covers the first and last segments.
    dense_curve = catmull_rom_spline([xy_points[0]] + xy_points + [xy_points[-1]])
    dense_curve[0] = xy_points[0]
    dense_curve[-1] = xy_points[-1]

    # Resample
    resampled_xy = resample_fixed_spacing(dense_curve, spacing)
    # Curvature
    curvature = compute_curvature(resampled_xy)

    # Feedrate
    feedrates = map_feedrate(curvature, f_min, f_max)

    # Bearings
    bearings = compute_bearings(resampled_xy, direction)

    # Build final G1 lines
    smoothed_lines = build_g1_lines(resampled_xy, bearings, feedrates, initial_z, endpoint_coordinates)

    return smoothed_lines


