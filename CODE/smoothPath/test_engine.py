import unittest

import engine


class ControllerLimitTests(unittest.TestCase):
    def test_spline_reduces_overshoot_at_each_limit(self):
        cases = (
            [(40, 40), (2, 50), (2, 90), (40, 100)],
            [(225, 40), (263, 50), (263, 90), (225, 100)],
            [(40, 40), (50, 2), (90, 2), (100, 40)],
            [(40, 180), (50, 218), (90, 218), (100, 180)],
        )
        for points in cases:
            with self.subTest(points=points):
                curve = engine.catmull_rom_spline(points, samples_per_segment=101)
                self.assertTrue(all(0 <= x <= 265 and 0 <= y <= 220 for x, y in curve))
                self.assertEqual(curve[0], points[1])
                self.assertEqual(curve[-1], points[2])
                midpoint = curve[50]
                linear_midpoint = tuple((a + b) / 2 for a, b in zip(points[1], points[2]))
                self.assertNotEqual(midpoint, linear_midpoint)

    def test_unrestricted_spline_is_unchanged(self):
        curve = engine.catmull_rom_spline(
            [(10, 10), (20, 30), (40, 30), (50, 10)],
            samples_per_segment=3
        )
        self.assertEqual(curve, [(20, 30), (30, 32.5), (40, 30)])

    def test_input_outside_limits_is_clamped_before_smoothing(self):
        lines = ["G1 X0 Y0 Z0", "G1 X300 Y250", "G1 X130 Y110"]
        result = engine.smooth_path(lines, 1, 200, 1000, "forward")
        points = engine.parse_g1_lines(result)
        self.assertGreater(len(points), 3)
        self.assertEqual(points[0][:2], (0, 0))
        self.assertEqual(points[-1][:2], (130, 110))
        self.assertTrue(all(0 <= x <= 265 and 0 <= y <= 220 for x, y, _ in points))

    def test_zero_length_path_reports_error(self):
        lines = ["G1 X0 Y0 Z0", "G1 X-5 Y-5", "G1 X0 Y0"]
        with self.assertRaisesRegex(ValueError, "no length"):
            engine.smooth_path(lines, 0.5, 200, 1000, "forward")

    def test_smoothed_gcode_stays_within_limits(self):
        cases = (
            ["G1 X0 Y20 Z0", "G1 X0 Y0", "G1 X30 Y0", "G1 X30 Y20"],
            ["G1 X245 Y200 Z0", "G1 X265 Y220", "G1 X235 Y220", "G1 X215 Y200"],
        )
        for lines in cases:
            with self.subTest(lines=lines):
                result = engine.smooth_path(lines, 0.5, 200, 1000, "forward")
                self.assertGreater(len(result), 3)
                for x, y, _ in engine.parse_g1_lines(result):
                    self.assertTrue(0 <= x <= 265 and 0 <= y <= 220, (x, y))


class EndpointTests(unittest.TestCase):
    def test_preserves_precise_endpoints_for_multiple_point_counts(self):
        cases = (
            ["G1 X1.234567890123456789 Y2.34567 Z7", "G1 X3.65432 Y4.76543"],
            ["G1 X0 Y220 Z7", "G1 X100 Y100", "G1 X265 Y0"],
            ["G1 X1.23456 Y2.34567 Z7", "G1 X10 Y10", "G1 X20 Y15",
             "G1 X30.65432 Y25.76543"],
            ["G1 X5.00001 Y8.00001 Z7", "G1 X50 Y50", "G1 X5.00001 Y8.00001"],
        )
        for lines in cases:
            with self.subTest(lines=lines):
                result = engine.smooth_path(lines, 1, 200, 1000, "forward")
                for source, output in ((lines[0], result[0]), (lines[-1], result[-1])):
                    for axis in ("X", "Y"):
                        self.assertEqual(engine.extract_value_text(output, axis),
                                         engine.extract_value_text(source, axis))
                self.assertEqual(engine.extract_value(result[0], "Z"), 7)

    def test_short_path_keeps_both_endpoints(self):
        lines = ["G1 X1.12345 Y2.12345 Z0", "G1 X1.2 Y2.2"]
        result = engine.smooth_path(lines, 10, 200, 1000, "forward")
        self.assertEqual(len(result), 2)
        self.assertEqual(engine.extract_value_text(result[0], "X"), "1.12345")
        self.assertEqual(engine.extract_value_text(result[-1], "X"), "1.2")

    def test_out_of_bounds_endpoints_are_rejected(self):
        cases = (
            ["G1 X-1 Y0 Z0", "G1 X1 Y1"],
            ["G1 X0 Y0 Z0", "G1 X265.00000000000000001 Y1"],
            ["G1 X0 Y220.0001 Z0", "G1 X1 Y1"],
            ["G1 X0 Y0 Z0", "G1 X1 Y-0.1"],
        )
        for lines in cases:
            with self.subTest(lines=lines):
                with self.assertRaisesRegex(ValueError, "start and end.*XY limits"):
                    engine.smooth_path(lines, 1, 200, 1000, "forward")

    def test_resampling_includes_endpoint_even_at_exact_spacing(self):
        self.assertEqual(engine.resample_fixed_spacing([(0, 0), (2, 0)], 1),
                         [(0, 0), (1, 0), (2, 0)])

    def test_missing_endpoint_coordinate_is_not_silently_skipped(self):
        cases = (
            ["G1 X0 Z0", "G1 X1 Y1", "G1 X2 Y2"],
            ["G1 X0 Y0 Z0", "G1 X1 Y1", "G1 X2"],
        )
        for lines in cases:
            with self.subTest(lines=lines):
                with self.assertRaisesRegex(ValueError, "start and end.*X and Y"):
                    engine.smooth_path(lines, 1, 200, 1000, "forward")


if __name__ == "__main__":
    unittest.main()
