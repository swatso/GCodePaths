# fileio.py
# Handles reading/writing G-code files and splitting into header/mid/path blocks.

import os

# ------------------------------------------------------------
# Default paths (GUI can override these)
# ------------------------------------------------------------

# User's Documents folder
DOCUMENTS = os.path.join(os.path.expanduser("~"), "Documents")

DEFAULT_INPUT_PATH = r"C:\PathCaptures\PATH_0.GCO"
DEFAULT_OUTPUT_FOLDER = os.path.join(DOCUMENTS, "GitRepos", "GCodePaths", "BuildingSite")


# ------------------------------------------------------------
# Read and classify G-code lines
# ------------------------------------------------------------

def read_gcode_file(filepath):
    """
    Reads the entire G-code file and splits it into:
      - header_block: lines before the first G1
      - mid_block: lines after the first G1 but before the second G1
      - path_block: all remaining G1 lines (the path to be smoothed)

    Returns:
        header_block, mid_block, path_block
    """

    with open(filepath, "r") as f:
        lines = [line.rstrip("\n") for line in f]

    header_block = []
    mid_block = []
    path_block = []

    g1_count = 0

    for line in lines:
        if line.startswith("G1"):
            g1_count += 1

            if g1_count == 1:
                # First G1 belongs to path_block (but smoothing engine will treat it specially)
                path_block.append(line)

            elif g1_count == 2:
                # Second G1 marks the start of the main path
                path_block.append(line)

            else:
                # Remaining G1 lines belong to the path
                path_block.append(line)

        else:
            # Non-G1 lines
            if g1_count == 0:
                # Before first G1
                header_block.append(line)
            elif g1_count == 1:
                # After first G1 but before second G1
                mid_block.append(line)
            else:
                # After second G1 — currently not expected, but we preserve them
                # If needed later, we can add a tail_block
                mid_block.append(line)

    return header_block, mid_block, path_block


# ------------------------------------------------------------
# Write output G-code
# ------------------------------------------------------------

def write_gcode_file(output_folder, input_filename, header_block, mid_block, smoothed_g1_lines):
    """
    Writes the final G-code file with the structure:

        header_block
        <first smoothed G1>
        mid_block
        <remaining smoothed G1 lines>

    The output filename matches the input filename.
    """

    os.makedirs(output_folder, exist_ok=True)

    output_path = os.path.join(output_folder, input_filename)

    with open(output_path, "w") as f:

        # Write header block
        for line in header_block:
            f.write(line + "\n")

        # Write first smoothed G1
        if smoothed_g1_lines:
            f.write(smoothed_g1_lines[0] + "\n")

        # Write mid block
        for line in mid_block:
            f.write(line + "\n")

        # Write remaining smoothed G1 lines
        for line in smoothed_g1_lines[1:]:
            f.write(line + "\n")

    return output_path


# ------------------------------------------------------------
# Utility: extract filename from path
# ------------------------------------------------------------

def get_filename(filepath):
    """Returns the filename portion of a full path."""
    return os.path.basename(filepath)
