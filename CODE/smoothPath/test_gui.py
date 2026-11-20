import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import engine
import gui


class Variable:
    def __init__(self, value=None):
        self.value = value
        self.callbacks = []

    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        for callback in self.callbacks:
            callback("", "", "write")

    def trace_add(self, _mode, callback):
        self.callbacks.append(callback)


class SmoothingExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.input_path = os.path.join(self.temp.name, "path.gco")
        with open(self.input_path, "w") as file:
            file.write("HEADER\nG1 X0 Y0 Z10\nMIDDLE\nG1 X5 Y0\nG1 X10 Y0\n")

        widgets = patch.multiple(
            gui.tk, StringVar=Variable, DoubleVar=Variable, IntVar=Variable,
            Label=MagicMock(), Entry=MagicMock(), Button=MagicMock(),
            Radiobutton=MagicMock()
        )
        widgets.start()
        self.addCleanup(widgets.stop)
        plot_patch = patch.object(gui.plotter, "plot_paths")
        self.plot = plot_patch.start()
        self.addCleanup(plot_patch.stop)
        error_patch = patch.object(gui.messagebox, "showerror")
        self.error = error_patch.start()
        self.addCleanup(error_patch.stop)
        self.app = gui.GCodeSmootherGUI(MagicMock())
        self.app.input_path_var.set(self.input_path)
        self.output_folder = os.path.join(self.temp.name, "output")
        self.app.output_folder_var.set(self.output_folder)

    def test_preview_does_not_write_and_export_writes_preview(self):
        self.app.run_smoothing()

        self.assertFalse(os.path.exists(self.output_folder))
        self.assertEqual(self.plot.call_count, 1)
        self.app.export_gcode_button.config.assert_called_with(state="normal")
        preview_lines = self.app.smoothed_result[3]
        preview_xy = [(engine.extract_value(line, "X"), engine.extract_value(line, "Y"))
                      for line in preview_lines]
        self.assertEqual(self.plot.call_args.args[1], preview_xy)

        self.app.export_gcode()
        output_path = os.path.join(self.output_folder, "path.gco")
        with open(output_path) as file:
            output_lines = file.read().splitlines()
        self.assertEqual(output_lines, ["HEADER", preview_lines[0], "MIDDLE"] + preview_lines[1:])
        self.assertIn(output_path, self.app.status_var.get())

    def test_preview_does_not_overwrite_existing_output(self):
        os.mkdir(self.output_folder)
        output_path = os.path.join(self.output_folder, "path.gco")
        with open(output_path, "w") as file:
            file.write("existing")

        self.app.run_smoothing()

        with open(output_path) as file:
            self.assertEqual(file.read(), "existing")

    def test_settings_change_invalidates_preview_but_output_folder_does_not(self):
        self.app.run_smoothing()
        other_folder = os.path.join(self.temp.name, "other")
        self.app.output_folder_var.set(other_folder)
        self.assertIsNotNone(self.app.smoothed_result)
        self.app.export_gcode()
        self.assertTrue(os.path.isfile(os.path.join(other_folder, "path.gco")))

        for variable, value in (
            (self.app.input_path_var, self.input_path),
            (self.app.direction_var, "reverse"),
            (self.app.fmin_var, 300),
            (self.app.fmax_var, 900),
            (self.app.spacing_var, 1),
        ):
            with self.subTest(variable=variable):
                self.app.run_smoothing()
                variable.set(value)
                self.assertIsNone(self.app.smoothed_result)
                self.app.export_gcode_button.config.assert_called_with(state="disabled")
                self.app.export_gcode()
                self.error.assert_called_with("Error", "Run smoothing before exporting G-code.")

    def test_failed_preview_cannot_export_previous_result(self):
        self.app.run_smoothing()
        self.plot.side_effect = ValueError("plot failed")
        self.app.run_smoothing()
        self.assertIsNone(self.app.smoothed_result)
        self.app.export_gcode_button.config.assert_called_with(state="disabled")
        self.assertEqual(self.app.status_var.get(), "Error")
        self.error.assert_called_with("Error", "plot failed")

    def test_preview_gcode_and_svg_use_bounded_path(self):
        with open(self.input_path, "w") as file:
            file.write("HEADER\nG1 X0.00012345 Y20.00098765 Z0\nMIDDLE\n"
                       "G1 X0 Y0\nG1 X30 Y0\nG1 X30.45678 Y20.000123\n")
        self.app.run_smoothing()
        preview_xy = self.plot.call_args.args[1]
        self.assertTrue(preview_xy)
        self.assertTrue(all(0 <= x <= 265 and 0 <= y <= 220 for x, y in preview_xy))
        self.assertEqual(preview_xy[0], (0.00012345, 20.00098765))
        self.assertEqual(preview_xy[-1], (30.45678, 20.000123))

        self.app.export_gcode()
        with open(os.path.join(self.output_folder, "path.gco")) as file:
            output_lines = file.read().splitlines()
        points = engine.parse_g1_lines(output_lines)
        self.assertEqual([(x, y) for x, y, _ in points], preview_xy)
        self.assertIn("X0.00012345 Y20.00098765", output_lines[1])
        self.assertIn("X30.45678 Y20.000123", output_lines[-1])

        with patch.object(gui.svgexport, "export_svg", return_value="preview.svg") as export_svg:
            self.app.export_svg()
        self.assertEqual(export_svg.call_args.args[2], preview_xy)

    def test_out_of_bounds_endpoint_rejects_preview_and_export(self):
        self.app.run_smoothing()
        with open(self.input_path, "w") as file:
            file.write("G1 X-1 Y0 Z0\nG1 X10 Y10\n")
        self.app.run_smoothing()
        self.assertIsNone(self.app.smoothed_result)
        self.app.export_gcode_button.config.assert_called_with(state="disabled")
        self.assertIn("start and end", self.error.call_args.args[1])
        self.assertFalse(os.path.exists(self.output_folder))


if __name__ == "__main__":
    unittest.main()
