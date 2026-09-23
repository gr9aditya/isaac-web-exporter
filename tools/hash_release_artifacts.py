"""Record hashes for the private, local-only v1 candidate."""

import hashlib
import json
import subprocess
from pathlib import Path


root = Path(__file__).resolve().parents[1]
paths = [root / "dist/isaac_web_exporter-1.0.0-py3-none-any.whl"]
paths += [root / f"runs/v1/v1-release-{name}/package.zip" for name in
          ("guided", "compact", "box", "static", "twins", "centimeter", "saved")]
records = []
for path in paths:
    content = path.read_bytes()
    records.append({"path": str(path.relative_to(root)).replace("\\", "/"),
                    "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
result = {
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                              cwd=root, text=True).strip(),
    "isaacImage": json.loads((root / "toolchain.lock.json").read_text(encoding="utf-8"))
                  ["isaac"]["containerImage"],
    "buildCommand": "python tools/build_release.py",
    "artifacts": records,
}
target = root / "runs/v1/release-artifacts.json"
target.write_text(json.dumps(result, indent=2), encoding="utf-8")
print(target)
