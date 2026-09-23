"""Build guided chapters from the captured real model-run records."""

import argparse
import json
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("summary", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
summary = json.loads(args.summary.read_text(encoding="utf-8"))
records = {record["object_id"]: record for record in summary["records"]
           if record.get("object_id", "").startswith("object-")}
chapters = [{
    "id": "preparation", "clipIndex": 0, "startSeconds": 0,
    "title": "Factory preparation",
    "caption": "Recorded Isaac Sim camera calibration and conveyor setup before the model run.",
    "camera": {"position": [4, 3, 5], "target": [0, 0.5, 0]},
}]
for index, item in enumerate(summary["items"]):
    record = records[item["id"]]
    prediction = record.get("predicted_type") or record.get("status", "unknown")
    destination = record.get("predicted_bin") or "no authorized bin"
    if record.get("pick_success"):
        outcome = "pick and bin correct" if record.get("correct_bin") else "pick succeeded; incorrect bin"
    elif record.get("pick_attempted"):
        outcome = "pick failed"
    else:
        outcome = f"{record.get('status', 'held')}; no pick attempted"
    chapters.append({
        "id": item["id"], "clipIndex": 0,
        "startSeconds": round(item["frame"] / 60, 3),
        "title": f"Item {index + 1}: {item['class'].replace('_', ' ')}",
        "caption": (f"Actual camera/model run: prediction {prediction}; "
                    f"destination {destination}; {outcome}."),
        "objectId": f"/World/RecordedItems/Item{index:03d}",
        "label": f"{prediction} → {destination}",
        "camera": {"position": [4, 3, 5], "target": [0, 0.5, 0]},
    })
args.output.write_text(json.dumps({"schemaVersion": "v1.0", "chapters": chapters},
                                  indent=2), encoding="utf-8")
print(json.dumps({"chapters": len(chapters), "duration": summary["durationSeconds"],
                  "modelItems": len(records)}))
