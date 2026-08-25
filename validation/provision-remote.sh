#!/usr/bin/env bash
# Run this ON the rented box (Ubuntu 22.04/24.04). Idempotent.
#   ssh vc 'bash -s' < validation/provision-remote.sh
set -euo pipefail

echo "== CPU check (this is the whole reason we rented a box) =="
for f in avx2 fma bmi2; do
  grep -qw "$f" /proc/cpuinfo && echo "  $f: YES" || { echo "  $f: MISSING — wrong instance type, destroy it"; exit 1; }
done
echo "  $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-)"

echo "== disk / memory =="
df -h / | awk 'NR==2{print "  disk free: "$4}'
free -g | awk 'NR==2{print "  ram total: "$2"G"}'

echo "== docker =="
if ! command -v docker >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg >/dev/null
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io >/dev/null
fi
docker --version

echo "== VC3D image (~2.8GB compressed) =="
docker pull -q ghcr.io/scrollprize/villa/volume-cartographer:edge
docker run --rm ghcr.io/scrollprize/villa/volume-cartographer:edge vc_grow_seg_from_seed --help >/dev/null
echo "  binary runs: OK"

echo "== workspace =="
mkdir -p /root/vc-work/out /root/vc-work/cache
cat > /root/vc-work/params.json <<'JSON'
{
  "mode": "seed",
  "use_cuda": false,
  "thread_limit": 4,
  "cache_size": 3000000000,
  "cache_root": "/work/cache",
  "step_size": 20.0,
  "search_effort": 10,
  "min_area_cm": 0.3,
  "tgt_overlap_count": 20
}
JSON
echo "  /root/vc-work ready"
echo
echo "PROVISIONED. Next: validation/trace-remote.sh"
