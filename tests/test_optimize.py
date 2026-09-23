"""The compact preset may remove keys only within its fixed error limits."""

import math
import unittest

from isaac_web_exporter.optimize import _error, _interpolate, _simplify


class OptimizeTests(unittest.TestCase):
    def test_linear_translation_collapses_to_endpoints(self):
        times = [index / 30 for index in range(31)]
        values = [(time, 2 * time, -time) for time in times]
        selected, error = _simplify(times, values, "translation")
        self.assertEqual(selected, [0, 30])
        self.assertLess(error, 0.0002)

    def test_curved_rotation_preserves_required_keys(self):
        times = [index / 30 for index in range(31)]
        angles = [0.7 * math.sin(time * math.pi) for time in times]
        values = [(0, 0, math.sin(angle / 2), math.cos(angle / 2))
                  for angle in angles]
        selected, _ = _simplify(times, values, "rotation")
        self.assertGreater(len(selected), 2)
        for begin, end in zip(selected, selected[1:]):
            for index in range(begin + 1, end):
                fraction = (times[index] - times[begin]) / (times[end] - times[begin])
                estimate = _interpolate(values[begin], values[end], fraction, "rotation")
                self.assertLessEqual(_error(values[index], estimate, "rotation"), 0.005)


if __name__ == "__main__":
    unittest.main()
