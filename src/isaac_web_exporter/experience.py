"""Validate the portable guided-demo presentation contract."""

import math


def validate_experience(data, object_ids, clip_durations):
    if not isinstance(data, dict) or data.get("schemaVersion") != "v1.0":
        raise ValueError("Experience schemaVersion must be v1.0")
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        raise ValueError("Experience chapters must be an array")
    known = set(object_ids)
    seen = set()
    for chapter in chapters:
        if not isinstance(chapter, dict):
            raise ValueError("Each chapter must be an object")
        identifier = chapter.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError("Chapter IDs must be unique nonempty strings")
        seen.add(identifier)
        index = chapter.get("clipIndex", 0)
        if type(index) is not int or index < 0 or index >= max(1, len(clip_durations)):
            raise ValueError(f"Chapter {identifier} has an invalid clip index")
        duration = clip_durations[index] if clip_durations else 0
        time = chapter.get("startSeconds")
        if (not isinstance(time, (float, int)) or not math.isfinite(time)
                or time < 0 or time > duration):
            raise ValueError(f"Chapter {identifier} is outside the selected clip")
        if (not isinstance(chapter.get("title"), str) or not chapter["title"].strip()
                or not isinstance(chapter.get("caption"), str)):
            raise ValueError(f"Chapter {identifier} needs title and caption text")
        if chapter.get("objectId") and chapter["objectId"] not in known:
            raise ValueError(f"Chapter {identifier} refers to unknown object {chapter['objectId']}")
        if chapter.get("label") is not None and not isinstance(chapter["label"], str):
            raise ValueError(f"Chapter {identifier} label must be text")
        if chapter.get("camera") is not None:
            if not isinstance(chapter["camera"], dict):
                raise ValueError(f"Chapter {identifier} camera must be an object")
            for key in ("position", "target"):
                values = chapter["camera"].get(key)
                if (not isinstance(values, list) or len(values) != 3 or
                        any(not isinstance(value, (float, int)) or not math.isfinite(value)
                            for value in values)):
                    raise ValueError(f"Chapter {identifier} camera.{key} must be three finite numbers")
            transition = chapter.get("transitionSeconds", 0)
            if (not isinstance(transition, (int, float)) or not math.isfinite(transition)
                    or not 0 <= transition <= 10):
                raise ValueError(f"Chapter {identifier} camera transition must be 0–10 seconds")
    return data
