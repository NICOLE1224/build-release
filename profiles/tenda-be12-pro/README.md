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

The seed disables the unused `audio-support` feature gate. This keeps
`ALL_KMODS` from selecting audio modules which pull in USB support. USB core
and common modules remain prohibited by the profile checks.

The Squeezelite Kconfig patch puts its codec options in an independent menu.
Guarding them with the parent package creates a recursive dependency through
the newer FFmpeg package. The codec options still default to disabled.

The MosDNS runtime updater intentionally follows MetaCubeX's `latest` release.
Build-time geodata is instead pinned by commit and SHA-256 so rebuilding the
same source produces the same package input.

Sing-box is intentionally not pinned to a version. During preparation,
`prepare.sh` reads GitHub's official `releases/latest` API and requires the
response to be neither a draft nor a prerelease. It downloads that release's
source archive, calculates the package hash, and records the release ID,
publication time, resolved version, URL, and hash in the build manifest.

`prepare.sh` removes X-WRT's hostapd patch
`820-ap-remove-a-sta-from-other-radios-before-adding-it-to-the-driver.patch`.
It works around an ath11k firmware crash by removing a station from the other
radios before adding it to the driver. In an AP MLD every link is a separate
radio, so the patch deauthenticates the partner links of each MLO client during
association and no MLO client completes the 4-way handshake. The BE12 Pro uses
mt7996 and does not need the workaround. The removal is pinned by SHA-256; a
changed or missing patch fails preparation so that the removal is reviewed.
