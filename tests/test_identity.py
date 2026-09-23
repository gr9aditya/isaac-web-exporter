"""Identity mapping must distinguish repeated leaf names after conversion."""

import unittest
import json
import struct
import tempfile
from pathlib import Path

from isaac_web_exporter.identity import enrich_glb, node_source_paths, read_glb


class IdentityMappingTests(unittest.TestCase):
    def test_duplicate_leaf_names_with_separate_ancestors(self):
        gltf = {
            "scenes": [{"nodes": [0]}],
            "nodes": [
                {"name": "World", "children": [1]},
                {"name": "World", "children": [2, 4]},
                {"name": "RobotA", "children": [3]},
                {"name": "Arm", "mesh": 0},
                {"name": "RobotB", "children": [5]},
                {"name": "Arm", "mesh": 1},
            ],
        }
        source = {
            "/World", "/World/RobotA", "/World/RobotA/Arm",
            "/World/RobotB", "/World/RobotB/Arm",
        }
        result = node_source_paths(gltf, source)
        self.assertEqual(result[3], "/World/RobotA/Arm")
        self.assertEqual(result[5], "/World/RobotB/Arm")
        self.assertNotEqual(result[3], result[5])

    def test_generated_child_nodes_map_to_nearest_source_object(self):
        gltf = {"scenes": [{"nodes": [0]}], "nodes": [
            {"name": "World", "children": [1]},
            {"name": "Product", "children": [2, 3]},
            {"name": "ConverterMesh_0", "mesh": 0},
            {"name": "ConverterMesh_1", "mesh": 1},
        ]}
        result = node_source_paths(gltf, {"/World", "/World/Product"})
        self.assertEqual([result[index] for index in (1, 2, 3)],
                         ["/World/Product"] * 3)

    def test_catalog_contains_one_to_many_indices_and_parent(self):
        gltf = {"asset": {"version": "2.0"}, "scenes": [{"nodes": [0]}], "nodes": [
            {"name": "World", "children": [1]},
            {"name": "Product", "children": [2, 3]},
            {"name": "ConverterMesh_0", "mesh": 0},
            {"name": "ConverterMesh_1", "mesh": 1},
        ]}
        encoded = json.dumps(gltf).encode()
        encoded += b" " * (-len(encoded) % 4)
        data = b"glTF" + struct.pack("<II", 2, 20 + len(encoded))
        data += struct.pack("<I4s", len(encoded), b"JSON") + encoded
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "scene.glb"
            path.write_bytes(data)
            catalog = enrich_glb(path, {"/World", "/World/Product"})
            self.assertEqual(len(catalog), 1)
            self.assertEqual(catalog[0]["parentId"], "/World")
            self.assertEqual(catalog[0]["nodeIndices"], [1, 2, 3])
            embedded, _ = read_glb(path)
            for index in (1, 2, 3):
                self.assertEqual(embedded["nodes"][index]["extras"]["isaacObjectId"],
                                 "/World/Product")


if __name__ == "__main__":
    unittest.main()
