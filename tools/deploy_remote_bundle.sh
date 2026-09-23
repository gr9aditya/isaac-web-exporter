#!/usr/bin/env bash
set -euo pipefail

workspace=/home/ubuntu/isaac-web-exporter-v1
assets="$workspace/src/isaac_web_exporter/player_dist/assets"
test -f "$workspace/remote-source.tar.gz"
test "$(realpath "$workspace")" = /home/ubuntu/isaac-web-exporter-v1
if test -d "$assets"; then
  test "$(realpath "$assets")" = "$assets"
  find "$assets" -maxdepth 1 -type f \( -name 'index-*.js' -o -name 'index-*.css' \) -delete
fi
tar -xzf "$workspace/remote-source.tar.gz" -C "$workspace"
