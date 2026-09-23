"""Build and bundle the offline browser runtime into the Python distribution."""

from pathlib import Path
import shutil
import subprocess


root = Path(__file__).resolve().parents[1]
player = root / "web" / "player"
target = root / "src" / "isaac_web_exporter" / "player_dist"

npm = shutil.which("npm.cmd") or shutil.which("npm")
if not npm:
    raise RuntimeError("Node.js/npm is needed by the package builder")
subprocess.run([npm, "ci"], cwd=player, check=True)
subprocess.run([npm, "run", "build"], cwd=player, check=True)
dist = player / "dist"
if not (dist / "index.html").is_file():
    raise RuntimeError("Player build did not create index.html")
if not (dist / "THIRD_PARTY_LICENSES" / "three-MIT.txt").is_file():
    raise RuntimeError("Three.js license is missing from the player build")
if target.exists():
    shutil.rmtree(target)
shutil.copytree(dist, target)
print(f"Bundled player: {target}")
