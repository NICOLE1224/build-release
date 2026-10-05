# X-WRT for CMCC RAX3000M

The `rax3000m` branch builds only CMCC RAX3000M firmware, based on the
selected official X-WRT tag's device configuration. It adds:

- `luci-app-mosdns`, MosDNS, v2dat and official GeoIP/GeoSite packages;
- `luci-app-wol` and etherwake;
- `luci-app-vlmcsd`, vlmcsd and LuCI Lua compatibility support.

Upstream applications, including OpenClash, remain in the image. MosDNS is
installed with its upstream default of **disabled**; configure DNS ports and
forwarding before enabling it alongside OpenClash.

The existing `tenda-be12-pro` branch and its releases are independent.
This branch does not build Nokia EA0326GMP, K2P or BE12 Pro.

## Build and download

Pushing build-definition changes to `rax3000m` starts a build with the newest
official tag. To run manually, select the existing `main.yml` workflow in
Actions and choose branch **rax3000m**. The workflow list may show the name
from the default BE12 Pro branch; the selected branch determines which
definition runs. A CLI alternative is:

```sh
gh workflow run main.yml --repo NICOLE1224/build-release --ref rax3000m
```

A new push replaces an older running RAX3000M build of the same layout.
Manual runs are queued. The BE12 Pro workflow has a separate concurrency group.

Leave `release_tag` empty for the newest official tag, or specify an exact tag.
The `device` input defaults to `cmcc_rax3000m`, the unified NAND/eMMC profile.
For an existing installation with the corresponding U-Boot layout, select
`cmcc_rax3000m-emmc-ubootlayout` or `cmcc_rax3000m-nand-ubootlayout`.
Each run selects exactly one device. Choose the profile matching your
installed bootloader and partition layout.

Successful builds publish recovery/initramfs and sysupgrade images, an
available factory image, `build-manifest.txt`, and
`sha256-<release_tag>.sum` directly as release assets. For example:

```sh
sha256sum -c sha256-26.10_b202609302026.sum
```

Release tags are `rax3000m-<release_tag>-<device>`. This keeps layouts and
BE12 Pro assets separate. Rebuilding the same version/layout updates only
that RAX3000M release. Scheduled builds still run only on the repository's
existing default BE12 Pro branch.

## Configuration

Official feeds follow the chosen X-WRT tag. Custom package commits are pinned
in `profiles/rax3000m/sources.env`. The configuration retains upstream default
applications, selects only the requested device and requires all three new
applications after `make defconfig`. Every package in the selected device's
image list is also selected for compilation (`m` or `y`); the image list alone
does not select packages in Kconfig. After `make defconfig`, preparation checks
all device packages before starting the build. Input and printer support
switches are retained to satisfy the USB packages' visibility dependencies.
The base root filesystem uses `apk-openssl` and `wpad-openssl`, matching the
official RAX3000M image; the conflicting mbedTLS variants are disabled.
Preparation checks X-WRT's generated conflict rules against the base and
device package sets after `make defconfig`.
Unrelated module selections, all-kernel-module builds and SDK builds are omitted.

The manifest records source, feed and custom-package revisions and the
configuration hash. The resolved configuration is also an Actions artifact.
A checked patch fixes the upstream Squeezelite Kconfig issue. VLMCSd's LuCI
include, dependencies and ACL are adapted for X-WRT.
VLMCSd's APK package version is `1113-r5`; its source remains the pinned
`svn1113` archive with the original hash.
The service package alone supplies the VLMCSd configuration and init script.
The LuCI page uses the service's `auto_activate` option and `/etc/vlmcsd.ini`,
and reloads VLMCSd after saving the INI file. VLMCSd keeps the service's
default of disabled; enable it in LuCI when needed. Preparation checks file
ownership and the app/service configuration before compilation.

Local Linux preparation uses the same order as CI:

```sh
tag=26.10_b202609302026
device=cmcc_rax3000m
git clone --depth 1 --branch "$tag" https://github.com/x-wrt/x-wrt.git x-wrt
(cd x-wrt && ./scripts/feeds update -a && ./scripts/feeds install -a)
sh prepare-custom-packages.sh x-wrt
sh profiles/rax3000m/configure.sh x-wrt "$tag" "$device"
sh profiles/rax3000m/write-provenance.sh x-wrt "$tag" "$device" build-manifest.txt
cp build.sh upload.sh x-wrt/
(cd x-wrt && CONFIG_VERSION_NUMBER="$tag" RAX3000M_DEVICE="$device" bash build.sh "$(nproc)")
```
