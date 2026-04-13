#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  scripts/remote-xcode.sh open
  scripts/remote-xcode.sh build

Required environment variables:
  IOS_MAC_HOST
  IOS_MAC_USER
  IOS_MAC_PROJECT_ROOT

Optional environment variables:
  IOS_MAC_SSH_PORT      default: 22
  XCODE_PROJECT         default: iosApp/MedLoquent.xcodeproj
  XCODE_SCHEME          default: MedLoquent
  XCODE_DESTINATION     default: generic/platform=iOS Simulator

This script syncs the repository to a remote macOS machine where Xcode is installed.
It can then open the Xcode project or run xcodebuild remotely.
EOF
}

require_env() {
    local name="$1"
    if [[ -z "${!name:-}" ]]; then
        echo "Missing required environment variable: ${name}" >&2
        exit 1
    fi
}

action="${1:-}"
if [[ -z "${action}" ]]; then
    usage
    exit 1
fi

require_env IOS_MAC_HOST
require_env IOS_MAC_USER
require_env IOS_MAC_PROJECT_ROOT

ssh_port="${IOS_MAC_SSH_PORT:-22}"
remote_target="${IOS_MAC_USER}@${IOS_MAC_HOST}"
xcode_project="${XCODE_PROJECT:-iosApp/MedLoquent.xcodeproj}"
xcode_scheme="${XCODE_SCHEME:-MedLoquent}"
xcode_destination="${XCODE_DESTINATION:-generic/platform=iOS Simulator}"
ssh_cmd=(ssh -p "${ssh_port}")
rsync_cmd=(rsync -az --delete --exclude .git --exclude .gradle --exclude build --exclude .devcontainer -e "ssh -p ${ssh_port}" ./ "${remote_target}:${IOS_MAC_PROJECT_ROOT}/")

"${rsync_cmd[@]}"

generate_project='if command -v xcodegen >/dev/null 2>&1 && [[ -f iosApp/project.yml ]]; then cd iosApp && xcodegen generate --spec project.yml && cd ..; fi'

case "${action}" in
    open)
        "${ssh_cmd[@]}" "${remote_target}" "set -e; cd '${IOS_MAC_PROJECT_ROOT}'; ${generate_project}; open -a Xcode '${xcode_project}'"
        ;;
    build)
        "${ssh_cmd[@]}" "${remote_target}" "set -e; cd '${IOS_MAC_PROJECT_ROOT}'; ${generate_project}; xcodebuild -project '${xcode_project}' -scheme '${xcode_scheme}' -destination '${xcode_destination}' build"
        ;;
    *)
        usage
        exit 1
        ;;
esac