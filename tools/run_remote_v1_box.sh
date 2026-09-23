#!/usr/bin/env bash
set -euo pipefail

workspace=/home/ubuntu/isaac-web-exporter-v1
archive="$workspace/remote-source.tar.gz"
test -f "$archive"
tar -tzf "$archive" > "$workspace/archive-list.txt"
sed -n '1,8p' "$workspace/archive-list.txt"
tar -xzf "$archive" -C "$workspace"
mkdir -p "$workspace/runs"
chmod 755 "$workspace"
chmod 777 "$workspace/runs"

docker run --rm --gpus all --network host --ipc host --entrypoint /bin/bash \
  -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y \
  -v "$workspace:/work" -w /work \
  nvcr.io/nvidia/isaac-sim@sha256:af1d2b4e75d553bfa27beb5a401198654aa8d607f3b7a6749196e9ce253def20 \
  -lc 'PYTHONPATH=/work/src /isaac-sim/python.sh -m isaac_web_exporter.export --config /work/tests/v1_falling_box.json'
