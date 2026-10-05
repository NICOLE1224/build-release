#!/bin/sh
set -eu
profile_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
source_root=${1:?usage: configure.sh SOURCE_ROOT RELEASE_TAG DEVICE}
release_tag=${2:?usage: configure.sh SOURCE_ROOT RELEASE_TAG DEVICE}
device=${3:-cmcc_rax3000m}
python3 "$profile_dir/configure.py" "$source_root" "$release_tag" "$device"
make -C "$source_root" defconfig

python3 "$profile_dir/verify-config.py" "$source_root" "$device"
