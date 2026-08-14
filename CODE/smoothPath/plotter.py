# plotter.py
# Plotting utilities for the G-code smoothing GUI application.

import math
import matplotlib.pyplot as plt


# ------------------------------------------------------------
# Plot smoothed path with arrows and feedrate colouring
# ------------------------------------------------------------

def plot_paths(original_points, smoothed_points, bearings, feedrates, arrow_step=10):
    """
    Displays a plot showing:
      - original path (thin grey)
      - smoothed path (thicker coloured line)
      - bearing arrows (every N points)
      - feedrate colour coding (red → yellow → green)

    Parameters:
        original_points : list of (x, y)
        smoothed_points : list of (x, y)
        bearings        : list of CNC bearing angles
        feedrates       : list of feedrates
        arrow_step      : draw an arrow every N points
    """

    # Extract XY for plotting
    orig_x = [p[0] for p in original_points]
    orig_y = [p[1] for p in original_points]

    sm_x = [p[0] for p in smoothed_points]
    sm_y = [p[1] for p in smoothed_points]

    # Feedrate colour mapping
    F_min = min(feedrates)
    F_max = max(feedrates)
    F_range = F_max - F_min if F_max > F_min else 1

    # Create figure
    plt.figure(figsize=(10, 8))

    # Plot original path
    plt.plot(orig_x, orig_y, color="lightgrey", linewidth=1, label="Original Path")

    # Plot smoothed path
    plt.plot(sm_x, sm_y, color="blue", linewidth=2, label="Smoothed Path")

    # Draw bearing arrows
    for i in range(0, len(smoothed_points), arrow_step):
        x, y = smoothed_points[i]
        angle = bearings[i]
        F = feedrates[i]

        # Feedrate colour (red → yellow → green)
        frac = (F - F_min) / F_range
        color = (1 - frac, frac, 0)

        # Arrow orientation (plot uses angle - 90°)
        plot_angle = (angle - 90) % 360
        dx = math.cos(math.radians(plot_angle)) * 0.5
        dy = math.sin(math.radians(plot_angle)) * 0.5

        plt.arrow(
            x, y, dx, dy,
            head_width=1.5,
            head_length=1.5,
            fc=color, ec=color
        )

    # Invert X-axis (your coordinate convention)
    plt.gca().invert_xaxis()

    plt.title("Smoothed Path with Bearings and Feedrate Colouring")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
