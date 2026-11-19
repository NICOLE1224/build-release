#!/bin/sh
set -eu
repository_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
exec sh "$repository_dir/profiles/ea0326gmp-k2p/prepare.sh" "${1:-$(pwd)}"
