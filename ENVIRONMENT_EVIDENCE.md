# Read-only environment evidence — 2026-09-22

This is a planning record, not a successful export or compatibility test. The workstation was inspected over the SSH connection supplied in `NEW_CODEX_PROJECT_PROMPT.md`. No simulator instance was started, recorder invoked, converter run, software installed, container changed, or source project modified. Only these planning documents were created in the separate Windows workspace.

## Workstation and isolation

| Observation | Evidence |
|---|---|
| Host | `hostname`: `brev-9h86y3ebd` |
| GPU | `nvidia-smi`: NVIDIA RTX PRO 6000 Blackwell Server Edition; 97887 MiB; driver 595.91.07 |
| Running Isaac container | `docker ps`: `isim-isaac-sim-1`, image `nvcr.io/nvidia/isaac-sim:6.1.0` |
| Immutable image reference | `docker image inspect`: `nvcr.io/nvidia/isaac-sim@sha256:af1d2b4e75d553bfa27beb5a401198654aa8d607f3b7a6749196e9ce253def20` |
| Existing project mount | Selected `docker inspect` mount fields show `/home/ubuntu/cheese-factory-challenge` mounted at `/workspace`, writable. Do not reuse this container as the exporter development sandbox. |
| Proposed independent Linux workspace | `/home/ubuntu/isaac-web-exporter` did not exist at inspection time. It was not created. |
| Independent local workspace | `C:/Users/adity/Documents/ChatGPT/isaac-web-exporter 2` initially contained only `.git`; `git status` reported no commits on `master`; `git remote -v` returned no remotes. |

## Installed versions and APIs

Paths below are **inside the running container**, unless identified as host paths. They can be re-read using `docker exec` without starting Kit.

| Component | Exact evidence |
|---|---|
| Isaac build | `/isaac-sim/VERSION`: `6.1.0-rc.26+release.49347.2d230af4.gl`. Image tag and app configuration say 6.1.0; preserve the detailed build string rather than silently replacing it with a generic GA label. |
| Kit | `/isaac-sim/kit/kernel/config/kit-core.json`, `app.tokens.kit_version`: `110.3.0+feature.371399.00c488ae.gl` |
| OpenUSD | Same configuration, `app.tokens.usd_version`: `25.11`. Independently, `extscache/omni.usd.libs-1.0.3+00c488ae.lx64.r.cp312/bin/libusd_usd.so` contains namespace `pxrInternal_v0_25_11__`. |
| Python | `/isaac-sim/kit/python/bin/python3 -B`: 3.12.13 |
| Host Isaac source checkout | Read-only `git` inspection of `/home/ubuntu/IsaacSim`: tag `v6.1.0`, commit `7c206f75bdadd9e05fc457f19863ca4c3f0cb693`, origin `https://github.com/isaac-sim/IsaacSim.git` |
| Stage Recorder | `extscache/omni.kit.stagerecorder.core-110.0.14+110.0.0.lx64.r.cp312.u7f4/config/extension.toml`: core 110.0.14, title marks BETA. Bundle and UI: 110.0.2. These are cached files; their presence does not prove enabled/runtime behavior. |
| Recorder commands | Same core directory, `omni/kit/stagerecorder/core/scripts/commands.py`: `StartRecording` at line 20; constructor lines 23–40; `StopRecording` at line 162. Parameters include recursive target paths, live/frame-range controls, FILE/NEW_LAYER, output folder/name, FPS, optional numeric `user_tokens`, and `use_timeline_ticks=False`. Lines 57–63 document FPS and timeline-tick semantics. Lines 118–124 configure animation-only output. |
| Recorder licensing | The installed command source's opening notice reserves NVIDIA proprietary rights. Do not treat this cached extension as Apache-licensed merely because the Isaac repository is Apache-licensed. |
| Fabric clue | Core recorder extension test arguments include `/app/useFabricSceneDelegate=1`; the app configuration also uses the Fabric scene delegate. This alone does not prove capture of physics state that bypasses USD writes. |
| OmniPVD | Cached `omni.physx.pvd-110.3.2+110.3.0.lx64.r.cp312.u7f4`; not exercised. |
| Asset Converter | Cached `omni.kit.asset_converter-6.0.5+110.1.1.lx64.r.cp312.u7f4`. Its `omni/kit/asset_converter/impl/context.py` defines `ignore_animations=False` (line 8), `embed_textures=True` (line 19), `bake_mdl_material=False` (line 31), and `export_mdl_gltf_extension=False` (line 33). Conversion was not run. |
| USD–MDL converter | Cached `omni.mdl.usd_converter-1.0.40+00c488ae`. This is not the MDL Distill and Bake extension. |
| MDL Distill and Bake | No `distill` extension directory found under `/isaac-sim/extscache`, `exts`, `extsUser`, `extsInternal`, `kit/exts`, or `kit/extscore`. Registry availability and compatibility were not tested. |

A direct `from pxr import Usd` using `python.sh`, without initializing Kit, returned `ModuleNotFoundError`. No package was installed to work around this. The stock scripts explicitly require Omniverse imports after `SimulationApp` initialization. Version evidence above therefore comes from configuration and binary inspection, not an executed `Usd.GetVersion()` call.

## Stock fixtures and assets

- `/isaac-sim/standalone_examples/api/isaacsim.core.experimental.api/add_cubes.py` is present. It uses PreviewSurface materials, Cube objects, rigid bodies and a ground plane; it is suitable as a first fixture after handling analytic geometry in an export copy.
- `/isaac-sim/standalone_examples/api/isaacsim.core.experimental.api/control_frankas.py` is present. It loads the Franka asset, chooses gripper/mesh variants and controls articulations. This is a candidate second technical fixture, subject to the model's asset rights for redistribution.
- Only one USD file was found under the inspected `standalone_examples` tree; none under `/isaac-sim/data`. This does not imply the machine has no cached assets elsewhere.
- `/isaac-sim/exts/isaacsim.storage.native/config/extension.toml` sets the default asset root to `https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.1`.
- A HEAD request from the workstation to that root plus `/Isaac/Robots_Multiphysics/FrankaRobotics/FrankaPanda/franka/franka.usda` returned HTTP 200. This establishes root-file reachability, not complete dependency availability, a successful scene load, or redistribution rights.

## Upstream inspection record

- GitHub API resolved USD Web View `main` to `b050c3731d1854a5980b6b4fe55ec1725dc18f51`, dated 2026-08-19, during this review.
- Its Git tree includes `public/usd-webview-bindings/usdWebViewBindingsModule.wasm`, size 19,733,084 bytes; Git blob ID `756786b69fd893692f02239d162676e71e5a103c`. This blob ID is not a SHA-256 release checksum.
- The tree also includes MaterialX 1.39.5 WASM files. Their presence contradicts any assumption that all native components must be built before trying the frontend.
- Current CI shows a failed visual-regression job: [run 32314546304](https://github.com/usd-wg/usd-wg-webview/actions/runs/32314546304). This establishes a failing upstream check, not the cause or impact on the proposed fixtures.

No actual export, WASM startup, offline browser playback, visual comparison, or integrated-GPU performance test was performed. Those are the first implementation gates, not verified outcomes of this planning task.
