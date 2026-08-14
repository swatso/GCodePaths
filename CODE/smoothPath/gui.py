# gui.py
# Tkinter GUI for the G-code smoothing application.

import os
import tkinter as tk
from tkinter import filedialog, messagebox

import fileio
import engine
import plotter
import svgexport


# ------------------------------------------------------------
# GUI Defaults (easy to adjust)
# ------------------------------------------------------------

DEFAULT_F_MIN = 200
DEFAULT_F_MAX = 1000
DEFAULT_SPACING = 0.5
DEFAULT_ARROW_STEP = 10

DEFAULT_INPUT_PATH = fileio.DEFAULT_INPUT_PATH
DEFAULT_OUTPUT_FOLDER = fileio.DEFAULT_OUTPUT_FOLDER


# ------------------------------------------------------------
# Main GUI Application
# ------------------------------------------------------------

class GCodeSmootherGUI:

    def __init__(self, root):
        self.root = root
        root.title("G-Code Smoother v2")

        # ------------------------------------------------------------
        # Input file selection
        # ------------------------------------------------------------

        tk.Label(root, text="Input G-code File:").grid(row=0, column=0, sticky="w")
        self.input_path_var = tk.StringVar(value=DEFAULT_INPUT_PATH)
        tk.Entry(root, textvariable=self.input_path_var, width=60).grid(row=0, column=1)
        tk.Button(root, text="Browse", command=self.browse_input).grid(row=0, column=2)

        # ------------------------------------------------------------
        # Output folder selection
        # ------------------------------------------------------------

        tk.Label(root, text="Output Folder:").grid(row=1, column=0, sticky="w")
        self.output_folder_var = tk.StringVar(value=DEFAULT_OUTPUT_FOLDER)
        tk.Entry(root, textvariable=self.output_folder_var, width=60).grid(row=1, column=1)
        tk.Button(root, text="Browse", command=self.browse_output).grid(row=1, column=2)

        # ------------------------------------------------------------
        # Direction of travel
        # ------------------------------------------------------------

        tk.Label(root, text="Direction of Travel:").grid(row=2, column=0, sticky="w")
        self.direction_var = tk.StringVar(value="forward")
        tk.Radiobutton(root, text="Forward", variable=self.direction_var, value="forward").grid(row=2, column=1, sticky="w")
        tk.Radiobutton(root, text="Reverse", variable=self.direction_var, value="reverse").grid(row=2, column=1, sticky="e")

        # ------------------------------------------------------------
        # Feedrate settings
        # ------------------------------------------------------------

        tk.Label(root, text="F_min:").grid(row=3, column=0, sticky="w")
        self.fmin_var = tk.DoubleVar(value=DEFAULT_F_MIN)
        tk.Entry(root, textvariable=self.fmin_var, width=10).grid(row=3, column=1, sticky="w")

        tk.Label(root, text="F_max:").grid(row=4, column=0, sticky="w")
        self.fmax_var = tk.DoubleVar(value=DEFAULT_F_MAX)
        tk.Entry(root, textvariable=self.fmax_var, width=10).grid(row=4, column=1, sticky="w")

        # ------------------------------------------------------------
        # Resample spacing
        # ------------------------------------------------------------

        tk.Label(root, text="Resample Spacing (mm):").grid(row=5, column=0, sticky="w")
        self.spacing_var = tk.DoubleVar(value=DEFAULT_SPACING)
        tk.Entry(root, textvariable=self.spacing_var, width=10).grid(row=5, column=1, sticky="w")

        # ------------------------------------------------------------
        # Arrow density
        # ------------------------------------------------------------

        tk.Label(root, text="Arrow Step:").grid(row=6, column=0, sticky="w")
        self.arrow_step_var = tk.IntVar(value=DEFAULT_ARROW_STEP)
        tk.Entry(root, textvariable=self.arrow_step_var, width=10).grid(row=6, column=1, sticky="w")

        # ------------------------------------------------------------
        # Action buttons
        # ------------------------------------------------------------

        tk.Button(root, text="Run Smoothing", command=self.run_smoothing, width=20).grid(row=7, column=0, pady=10)
        tk.Button(root, text="Export SVG", command=self.export_svg, width=20).grid(row=7, column=1, pady=10)

        # ------------------------------------------------------------
        # Status bar
        # ------------------------------------------------------------

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(root, textvariable=self.status_var, anchor="w").grid(row=8, column=0, columnspan=3, sticky="we")

    # ------------------------------------------------------------
    # File browser handlers
    # ------------------------------------------------------------

    def browse_input(self):
        # Use the folder of the currently selected path
        current_path = self.input_path_var.get()
        initial_dir = os.path.dirname(current_path)

        path = filedialog.askopenfilename(
            title="Select G-code File",
            initialdir=initial_dir,   # <--- THIS IS THE IMPORTANT BIT
            filetypes=[("G-code Files", "*.gco *.gcode *.txt"), ("All Files", "*.*")]
        )
        if path:
            self.input_path_var.set(path)

    def browse_output(self):
        # Use the folder currently shown in the GUI
        current_folder = self.output_folder_var.get()

        # If the folder doesn't exist yet, fall back to default
        if os.path.isdir(current_folder):
            initial_dir = current_folder
        else:
            initial_dir = DEFAULT_OUTPUT_FOLDER

        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=initial_dir    # <--- IMPORTANT
        )

        if folder:
            self.output_folder_var.set(folder)


    # ------------------------------------------------------------
    # Run smoothing
    # ------------------------------------------------------------

    def run_smoothing(self):
        try:
            input_path = self.input_path_var.get()
            output_folder = self.output_folder_var.get()

            if not os.path.isfile(input_path):
                messagebox.showerror("Error", "Input file does not exist.")
                return

            # Read G-code blocks
            header, mid, path_block = fileio.read_gcode_file(input_path)

            # Smooth path
            smoothed_lines = engine.smooth_path(
                path_block,
                spacing=self.spacing_var.get(),
                f_min=self.fmin_var.get(),
                f_max=self.fmax_var.get(),
                direction=self.direction_var.get()
            )

            # Write output
            input_filename = fileio.get_filename(input_path)
            output_path = fileio.write_gcode_file(
                output_folder,
                input_filename,
                header,
                mid,
                smoothed_lines
            )

            # Prepare data for plotting
            raw_points = engine.parse_g1_lines(path_block)
            original_xy = [(p[0], p[1]) for p in raw_points]

            smoothed_xy = [(engine.extract_value(line, "X"),
                            engine.extract_value(line, "Y"))
                           for line in smoothed_lines]

            bearings = [engine.extract_value(line, "Z") for line in smoothed_lines]
            feedrates = [engine.extract_value(line, "F") for line in smoothed_lines]

            # Plot
            plotter.plot_paths(
                original_xy,
                smoothed_xy,
                bearings,
                feedrates,
                arrow_step=self.arrow_step_var.get()
            )

            self.status_var.set(f"Smoothing complete: {output_path}")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error")

    # ------------------------------------------------------------
    # Export SVG
    # ------------------------------------------------------------

    def export_svg(self):
        try:
            input_path = self.input_path_var.get()
            output_folder = self.output_folder_var.get()

            if not os.path.isfile(input_path):
                messagebox.showerror("Error", "Input file does not exist.")
                return

            # Read G-code blocks
            header, mid, path_block = fileio.read_gcode_file(input_path)

            # Smooth path (same as smoothing button)
            smoothed_lines = engine.smooth_path(
                path_block,
                spacing=self.spacing_var.get(),
                f_min=self.fmin_var.get(),
                f_max=self.fmax_var.get(),
                direction=self.direction_var.get()
            )

            # Prepare data for SVG
            smoothed_xy = [(engine.extract_value(line, "X"),
                            engine.extract_value(line, "Y"))
                           for line in smoothed_lines]

            bearings = [engine.extract_value(line, "Z") for line in smoothed_lines]
            feedrates = [engine.extract_value(line, "F") for line in smoothed_lines]

            input_filename = fileio.get_filename(input_path)

            svg_path = svgexport.export_svg(
                output_folder,
                input_filename,
                smoothed_xy,
                bearings,
                feedrates,
                arrow_step=self.arrow_step_var.get()
            )

            self.status_var.set(f"SVG exported: {svg_path}")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error")


# ------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = GCodeSmootherGUI(root)
    root.mainloop()

