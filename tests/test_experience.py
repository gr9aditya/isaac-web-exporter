"""Reject presentation data that points outside the actual exported clip."""

import unittest

from isaac_web_exporter.experience import validate_experience


class ExperienceValidationTests(unittest.TestCase):
    def test_valid_chapter(self):
        data = {"schemaVersion": "v1.0", "chapters": [
            {"id": "inspect", "clipIndex": 0, "startSeconds": 2.5,
             "title": "Inspect", "caption": "Recorded motion",
             "objectId": "/World/Part",
             "camera": {"position": [1, 2, 3], "target": [0, 0, 0]}},
        ]}
        self.assertIs(validate_experience(data, ["/World/Part"], [5]), data)

    def test_unknown_object_and_invalid_time(self):
        base = {"schemaVersion": "v1.0", "chapters": [
            {"id": "inspect", "startSeconds": 2.5,
             "title": "Inspect", "caption": "Recorded motion",
             "objectId": "/World/Missing"},
        ]}
        with self.assertRaisesRegex(ValueError, "unknown object"):
            validate_experience(base, ["/World/Part"], [5])
        base["chapters"][0]["objectId"] = "/World/Part"
        base["chapters"][0]["startSeconds"] = 6
        with self.assertRaisesRegex(ValueError, "outside"):
            validate_experience(base, ["/World/Part"], [5])


if __name__ == "__main__":
    unittest.main()
