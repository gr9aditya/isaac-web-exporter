"""Create the v1 acceptance ledger from the authoritative plan checklist."""

from pathlib import Path
import re


root = Path(__file__).resolve().parents[1]
plan = (root / "V1_IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
items = re.findall(r"^- \[ \] \*\*([A-J]\d{2})\*\* (.+)$", plan, re.M)
if len(items) != 66 or len({item[0] for item in items}) != 66:
    raise SystemExit(f"Expected 66 unique checklist items, got {len(items)}")
destination = root / "V1_ACCEPTANCE.md"
if destination.exists():
    raise SystemExit(f"Refusing to overwrite {destination}")

lines = [
    "# V1 acceptance ledger",
    "",
    "Status: **V1 INCOMPLETE**. Checkboxes in V1_IMPLEMENTATION_PLAN.md are the",
    "authoritative completion list. This ledger records evidence for each item.",
    "Never mark a code-only change as a verified runtime pass.",
    "",
    "| ID | Status | Acceptance result | Command/test/manual steps | Evidence path | Tested revision/build | Limitation |",
    "|---|---|---|---|---|---|---|",
]
for identifier, requirement in items:
    result = "Pending: " + requirement.replace("|", "\\|")
    if identifier == "A01":
        lines.append(
            "| A01 | PASS | Inspected the empty Git history, ignored output, and "
            "59 source/plan files; created the first local baseline commit. | "
            "`git status --short`; `git add -n .`; `git commit` | "
            "`git show --stat 64d6a83` | `64d6a83` | Local commit only; "
            "agent identity was set per command. |"
        )
    elif identifier == "A02":
        lines.append(
            "| A02 | IN_PROGRESS | Isaac image digest and remote read-only source "
            "were reachable; Intel UHD integrated graphics present. Firefox "
            "is not yet installed. | SSH environment probe; PowerShell "
            "`Get-CimInstance Win32_VideoController` | "
            "`toolchain.lock.json`; runtime probe pending | `64d6a83` | "
            "Finish Isaac/Firefox access and mount checks. |"
        )
    else:
        lines.append(f"| {identifier} | TODO | {result} | — | — | — | — |")
lines += [
    "",
    "## Session notes",
    "",
    "- Baseline commit: `64d6a83` (source and planning documents only).",
    "- Remote `brev-9h86y3ebd` responded; pinned Isaac 6.1 image digest was present.",
    "- `/home/ubuntu/cheese-factory-challenge` returned a clean Git status in the",
    "  read-only probe. No factory source was changed.",
    "- Windows reference machine reports Intel(R) UHD Graphics driver",
    "  `32.0.101.7082`. Firefox availability remains to be resolved.",
]
destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(destination, len(items))
