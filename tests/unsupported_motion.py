"""Owned negative fixture: animated visibility is outside v1 transform scope."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from pxr import UsdGeom
from static_gallery import build as build_static


def build(stage, app, config):
    build_static(stage, app, config)
    object_prim = stage.GetPrimAtPath("/World/Left/Part")
    visibility = UsdGeom.Imageable(object_prim).GetVisibilityAttr()
    visibility.Set(UsdGeom.Tokens.inherited, 0)
    visibility.Set(UsdGeom.Tokens.invisible, 30)
    return {}
