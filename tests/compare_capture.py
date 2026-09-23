"""Compare Isaac capture endpoints with independently loaded browser poses."""

import argparse
import json
import math
from pathlib import Path


def compare(report_path, browser_path, prim_path):
    report = json.loads(Path(report_path).read_text())
    browser = json.loads(Path(browser_path).read_text())
    capture = report["capture"][prim_path]
    differences = {}
    for label, source_key in (("first", "first_position"), ("last", "last_position")):
        actual = browser[label]["local"]
        expected = capture[source_key]
        differences[label] = math.dist(actual, expected)
        if differences[label] > 1e-4:
            raise AssertionError(f"{prim_path} {label} pose differs by {differences[label]} m")
    return differences


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("browser", type=Path)
    parser.add_argument("prim_path")
    args = parser.parse_args()
    print(json.dumps(compare(args.report, args.browser, args.prim_path), indent=2))
