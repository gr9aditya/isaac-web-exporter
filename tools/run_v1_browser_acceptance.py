"""Run final-package browser acceptance sequentially against local HTTP on 8003."""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8003/"
urllib.request.urlopen(BASE + "v1-release-guided/package/", timeout=10).close()

cases = [
    ("guided-editor", "tests/v1_guided_browser.mjs", {"ACCEPT_URL": BASE + "v1-release-guided/package/"}),
    ("guided-state", "tests/v1_guided_state_browser.mjs", {"ACCEPT_URL": BASE + "v1-release-guided/package/"}),
    ("transport", "tests/v1_transport_browser.mjs", {"ACCEPT_URL": BASE + "v1-release-box/package/"}),
    ("navigation", "tests/v1_navigation_inspection_browser.mjs", {"GUIDED_URL": BASE + "v1-release-guided/package/", "BOX_URL": BASE + "v1-release-box/package/"}),
    ("modes-identity", "tests/v1_modes_identity.mjs", {"STATIC_PACKAGE": "v1-release-static/package/", "TWIN_PACKAGE": "v1-release-twins/package/"}),
    ("loading-errors", "tests/v1_load_errors_browser.mjs", {"ACCEPT_URL": BASE + "v1-release-guided/package/"}),
    ("offset-centimeter", "tests/v1_centimeter_browser.mjs", {"ACCEPT_URL": BASE + "v1-release-offset-saved/package/"}),
    ("workflow", "tests/v1_workflow_browser.mjs", {"ACCEPT_URL": BASE + "v1-release-guided/package/"}),
]

results = {}
for name, script, overrides in cases:
    env = os.environ.copy()
    env.update(overrides)
    run = subprocess.run(["node", script], cwd=ROOT, env=env, text=True,
                         capture_output=True, timeout=90)
    try:
        parsed = json.loads(run.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        parsed = {"stdout": run.stdout[-1000:]}
    results[name] = {"exitCode": run.returncode, "result": parsed,
                     "stderr": run.stderr[-1000:]}
    print(f"{name}: {'PASS' if run.returncode == 0 else 'FAIL'}", flush=True)

summary = {"status": "PASS" if all(item["exitCode"] == 0 for item in results.values())
           else "FAIL", "cases": results}
target = ROOT / "runs/v1/release-browser-suite.json"
target.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(target)
sys.exit(0 if summary["status"] == "PASS" else 1)
