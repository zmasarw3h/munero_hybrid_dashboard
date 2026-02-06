#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  # Run on an Ubuntu VM (22.04+ recommended)
  bash munero-platform/deploy/phase-5/vm-bootstrap-ubuntu.sh

Installs:
  - Docker Engine
  - Docker Compose v2 plugin (docker compose ...)

Notes:
  - Requires outbound internet access from the VM (apt + Docker repo).
  - Must be run as root or via sudo.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "Missing required command: sudo (run as root or install sudo)" >&2
    exit 1
  fi
  exec sudo -E bash "$0" "$@"
fi

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" && "${ID_LIKE:-}" != *"ubuntu"* ]]; then
    echo "Warning: this script is intended for Ubuntu; detected ID=${ID:-unknown}." >&2
  fi
else
  echo "Warning: /etc/os-release not found; continuing." >&2
fi

echo "== Installing Docker + Compose v2 (Ubuntu) ==" >&2

apt-get update -y
apt-get install -y ca-certificates curl gnupg

install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
fi

arch="$(dpkg --print-architecture)"
codename="$(
  if command -v lsb_release >/dev/null 2>&1; then
    lsb_release -cs
  else
    # shellcheck disable=SC2154
    echo "${VERSION_CODENAME:-}"
  fi
)"

if [[ -z "${codename}" ]]; then
  echo "Unable to determine Ubuntu codename (install lsb-release or ensure VERSION_CODENAME is set)." >&2
  exit 1
fi

cat >/etc/apt/sources.list.d/docker.list <<EOF
deb [arch=${arch} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${codename} stable
EOF

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

if getent group docker >/dev/null 2>&1; then
  true
else
  groupadd docker
fi

target_user="${SUDO_USER:-}"
if [[ -n "${target_user}" && "${target_user}" != "root" ]]; then
  usermod -aG docker "${target_user}" || true
  echo "Added ${target_user} to docker group (re-login required)." >&2
fi

echo "" >&2
echo "== Versions ==" >&2
docker --version
docker compose version

echo "" >&2
echo "✅ Docker + Compose v2 installed." >&2

