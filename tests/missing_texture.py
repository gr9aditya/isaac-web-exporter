"""Negative fixture: a bound material references a nonexistent texture."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from pxr import Sdf, UsdShade
from falling_box import build as build_box


def build(stage, app, config):
    built = build_box(stage, app, config)
    root = "/World/Looks/World_FallingBox"
    texture = UsdShade.Shader.Define(stage, root + "/MissingTexture")
    texture.CreateIdAttr("UsdUVTexture")
    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(
        Sdf.AssetPath("this-file-is-intentionally-missing.png"))
    texture.CreateOutput("rgb", Sdf.ValueTypeNames.Color3f)
    pbr = UsdShade.Shader(stage.GetPrimAtPath(root + "/PBR"))
    pbr.GetInput("diffuseColor").ConnectToSource(texture.ConnectableAPI(), "rgb")
    return built
