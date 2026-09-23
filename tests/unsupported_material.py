"""Owned negative fixture with a bound unsupported shader type."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from pxr import UsdShade
from falling_box import build as build_box


def build(stage, app, config):
    result = build_box(stage, app, config)
    shader = UsdShade.Shader(stage.GetPrimAtPath(
        "/World/Looks/World_FallingBox/PBR"))
    shader.CreateIdAttr("UnsupportedShader")
    return result
