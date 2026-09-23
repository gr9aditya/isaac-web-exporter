"""Self-authored mesh geometry shared by independent Isaac test projects."""

from pxr import Gf, Sdf, UsdGeom, UsdShade


def box(stage, path, size, color, center):
    x, y, z = [value / 2 for value in size]
    points = [
        Gf.Vec3f(-x, -y, -z), Gf.Vec3f(x, -y, -z),
        Gf.Vec3f(x, y, -z), Gf.Vec3f(-x, y, -z),
        Gf.Vec3f(-x, -y, z), Gf.Vec3f(x, -y, z),
        Gf.Vec3f(x, y, z), Gf.Vec3f(-x, y, z),
    ]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(points)
    # Hydra/RTX uses USD extents for culling; without them the browser GLB may
    # look correct while Isaac's own viewport renders the authored mesh black.
    mesh.CreateExtentAttr([Gf.Vec3f(-x, -y, -z), Gf.Vec3f(x, y, z)])
    mesh.CreateFaceVertexCountsAttr([4] * 6)
    mesh.CreateFaceVertexIndicesAttr([
        0, 3, 2, 1, 4, 5, 6, 7, 0, 1, 5, 4,
        1, 2, 6, 5, 2, 3, 7, 6, 3, 0, 4, 7,
    ])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.AddTranslateOp().Set(Gf.Vec3d(*center))
    material_path = "/World/Looks/" + path.strip("/").replace("/", "_")
    material = UsdShade.Material.Define(stage, material_path)
    shader = UsdShade.Shader.Define(stage, material_path + "/PBR")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.55)
    shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    return mesh
