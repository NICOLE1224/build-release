#!/bin/sh
set -eu
profile_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
usage='usage: configure.sh SOURCE_ROOT RELEASE_TAG DEVICE'
source_root=${1:?$usage}
release_tag=${2:?$usage}
device=${3:?$usage}
python3 "$profile_dir/configure.py" "$source_root" "$release_tag" "$device"
make -C "$source_root" defconfig

python3 "$profile_dir/verify-config.py" "$source_root" "$device"
