# X-WRT for Nokia EA0326GMP and Phicomm K2P

The `ea0326gmp-k2p` branch builds only Nokia EA0326GMP (`nokia_ea0326gmp`,
mediatek/filogic) and Phicomm K2P (`phicomm_k2p`, ramips/mt7621) firmware,
based on the selected official X-WRT tag's device configuration. Both images add:

- `luci-app-wol` and etherwake;
- `luci-app-vlmcsd`, vlmcsd and LuCI Lua compatibility support.

The EA0326GMP image also adds the official feeds' `tailscale` client and
`luci-app-tailscale-community`. The K2P is omitted because its 16 MiB flash
(15744k firmware partition) cannot hold the Tailscale binary.

Unlike the `rax3000m` branch, no Clash or MosDNS packages are built:
OpenClash, Mihomo, MosDNS, v2dat and v2ray GeoIP/GeoSite data are removed from
the upstream configuration and the device package list, and preparation fails
if any of them is still selected after `make defconfig`.

The `tenda-be12-pro` and `rax3000m` branches and their releases are independent.

## Build and download

Pushing build-definition changes to `ea0326gmp-k2p` builds both devices with
the newest official tag. To run manually, select the existing `main.yml`
workflow in Actions and choose branch **ea0326gmp-k2p**. The workflow list may
show the name from the default BE12 Pro branch; the selected branch determines
which definition runs. A CLI alternative is:

```sh
gh workflow run main.yml --repo NICOLE1224/build-release --ref ea0326gmp-k2p \
  -f device=all
```

`device` is `all` (default), `nokia_ea0326gmp` or `phicomm_k2p`. Each device
is built in its own job; one device failing does not cancel the other. Leave
`release_tag` empty for the newest official tag, or specify an exact tag.
A new push replaces an older running push build. Manual runs are queued.

Successful builds publish release assets under the tag
`<device>-<release_tag>`, for example `phicomm_k2p-26.10_b202611171234`:

- EA0326GMP: `initramfs-recovery.itb`, `squashfs-sysupgrade.itb`, and the
  `preloader.bin` / `bl31-uboot.fip` bootloader artifacts when produced;
- K2P: `initramfs-kernel.bin` and `squashfs-sysupgrade.bin`;
- `build-manifest.txt` and `sha256-<release_tag>-<device>.sum`:

```sh
sha256sum -c sha256-26.10_b202611171234-phicomm_k2p.sum
```

Rebuilding the same version/device updates only that release.

## Configuration

Official feeds follow the chosen X-WRT tag; Tailscale and its LuCI app come
from that tag's packages and luci feeds. The VLMCSd commits are pinned in
`profiles/ea0326gmp-k2p/sources.env`. The device list, per-device applications
and root filesystem providers are defined in
`profiles/ea0326gmp-k2p/configure.py`:

| Device | Upstream config | TLS providers | Extra apps |
| --- | --- | --- | --- |
| `nokia_ea0326gmp` | `config.mediatek-filogic*` | `apk-openssl`, `wpad-openssl` | WOL, VLMCSd, Tailscale |
| `phicomm_k2p` | `config.ramips-mt7621*` | `apk-mbedtls`, `wpad-mbedtls` | WOL, VLMCSd |

The configuration keeps upstream default applications other than Clash/MosDNS,
selects only the requested device and requires the added applications to be
built in after `make defconfig`. Every package in the selected device's image
list is also selected for compilation (`m` or `y`). The conflicting TLS
variants are excluded from both root filesystems, and preparation checks
X-WRT's generated conflict rules against the base and device package sets.
`CONFIG_JSON_OVERVIEW_IMAGE_INFO` is enabled (ramips disables it upstream) so
images are exported and verified from `profiles.json`. Unrelated module
selections, all-kernel-module builds and SDK builds are omitted.

The manifest records source, feed and custom-package revisions and the
configuration hash. The resolved configuration is also an Actions artifact.
A checked patch fixes the upstream Squeezelite Kconfig issue. VLMCSd's LuCI
include, dependencies and ACL are adapted for X-WRT; its APK package version
is `1113-r5` from the pinned `svn1113` archive. VLMCSd keeps the service's
default of disabled; enable it in LuCI when needed.

Local Linux preparation uses the same order as CI:

```sh
tag=26.10_b202611171234
device=phicomm_k2p   # or nokia_ea0326gmp
git clone --depth 1 --branch "$tag" https://github.com/x-wrt/x-wrt.git x-wrt
(cd x-wrt && ./scripts/feeds update -a && ./scripts/feeds install -a)
sh prepare-custom-packages.sh x-wrt
sh profiles/ea0326gmp-k2p/configure.sh x-wrt "$tag" "$device"
sh profiles/ea0326gmp-k2p/write-provenance.sh x-wrt "$tag" "$device" build-manifest.txt
cp build.sh upload.sh x-wrt/
(cd x-wrt && CONFIG_VERSION_NUMBER="$tag" BUILD_DEVICE="$device" bash build.sh "$(nproc)")
```
