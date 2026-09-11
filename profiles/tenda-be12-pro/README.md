# Tenda BE12 Pro profile

This directory is the complete customization layer applied after cloning an
official X-WRT release tag and installing its matching feeds.

- `config.seed` is the canonical `scripts/diffconfig.sh` output. It selects
  only the Tenda BE12 Pro device and the desired packages.
- `sources.env` pins custom-package commits and build-time geodata hashes.
- `patches/` contains reviewable changes to official or pinned package trees.
- `prepare.sh` clones and patches custom packages.
- `configure.sh` expands the seed with `make defconfig`, validates package
  policy, and rejects configuration drift.
- `write-provenance.sh` records the exact source and feed commits used by a
  build.

The MosDNS runtime updater intentionally follows MetaCubeX's `latest` release.
Build-time geodata is instead pinned by commit and SHA-256 so rebuilding the
same source produces the same package input.

Sing-box is intentionally not pinned to a version. During preparation,
`prepare.sh` reads GitHub's official `releases/latest` API and requires the
response to be neither a draft nor a prerelease. It downloads that release's
source archive, calculates the package hash, and records the release ID,
publication time, resolved version, URL, and hash in the build manifest.
