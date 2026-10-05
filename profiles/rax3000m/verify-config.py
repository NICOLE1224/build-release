#!/usr/bin/env python3
"""Reject missing per-device build selections immediately after defconfig."""
import json
import re
import sys
from pathlib import Path

from configure import IMAGE_PROVIDERS


def verify_install_conflicts(values: dict, requested: set, removed: set, metadata: Path) -> int:
    # X-WRT emits both declared package conflicts and implicit provider conflicts
    # in this generated Kconfig. Unlike Kconfig itself, the image install combines
    # the built-in base packages with the device's modular package selections.
    base = {key.removeprefix("CONFIG_PACKAGE_") for key, value in values.items()
            if key.startswith("CONFIG_PACKAGE_") and value == "y"}
    image = (base - removed) | requested
    current = None
    conflicts = set()
    checked = 0
    for line in metadata.read_text().splitlines():
        entry = re.fullmatch(r"\s*(?:menu)?config\s+(\S+)\s*", line)
        if entry:
            current = entry[1].removeprefix("PACKAGE_") if entry[1].startswith("PACKAGE_") else None
        conflict = re.fullmatch(r"\s*depends on m \|\| \(PACKAGE_(\S+) != y\)\s*", line)
        if current and conflict:
            checked += 1
            other = conflict[1]
            if any(current in packages and other in packages for packages in (base, image)):
                conflicts.add(tuple(sorted((current, other))))
    if not checked:
        raise ValueError("no package conflict rules found in generated Kconfig")
    if conflicts:
        pairs = "; ".join(" + ".join(pair) for pair in sorted(conflicts))
        raise ValueError("conflicting packages in root filesystem: " + pairs)
    return checked


def verify(source: Path, device: str) -> None:
    text = (source / ".config").read_text()
    values = dict(re.findall(r"^(CONFIG_[^=\s]+)=(.*)$", text, re.M))
    selected = [key for key, value in values.items()
                if key.startswith("CONFIG_TARGET_DEVICE_") and value == "y"]
    expected = f"CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_{device}"
    if selected != [expected]:
        raise ValueError(f"expected only {expected}=y, found {selected}")
    if values.get("CONFIG_TARGET_PER_DEVICE_ROOTFS") != "y":
        raise ValueError("per-device root filesystem must be enabled")
    key = f"CONFIG_TARGET_DEVICE_PACKAGES_mediatek_filogic_DEVICE_{device}"
    packages = json.loads(values.get(key, '""')).split()
    if not packages:
        raise ValueError("device package list is empty")
    requested = {package for package in packages if not package.startswith("-")}
    removed = {package[1:] for package in packages if package.startswith("-")}
    missing = sorted(package for package in requested
                     if values.get(f"CONFIG_PACKAGE_{package}") not in ("y", "m"))
    if missing:
        raise ValueError("device packages are not selected for compilation: " + ", ".join(missing))
    required = (Path(__file__).parent / "packages.required").read_text().splitlines()
    for package in required:
        if package and not package.startswith("#") and values.get(f"CONFIG_PACKAGE_{package}") != "y":
            raise ValueError(f"required package is not built in: {package}")
    metadata = source / "tmp/.config-package.in"
    if not metadata.is_file():
        raise ValueError("generated package conflict metadata is missing; run make defconfig first")
    checked = verify_install_conflicts(values, requested, removed, metadata)
    for preferred, fallback in IMAGE_PROVIDERS.items():
        if values.get(f"CONFIG_PACKAGE_{preferred}") != "y":
            raise ValueError(f"base root filesystem must use {preferred}")
        if values.get(f"CONFIG_PACKAGE_{fallback}") in ("y", "m") or fallback in requested:
            raise ValueError(f"{fallback} must be disabled when using {preferred}")
    print(f"Verified {device}: all {len(requested)} device packages selected; {checked} rootfs conflict rules checked")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: verify-config.py SOURCE_ROOT DEVICE")
    try:
        verify(Path(sys.argv[1]), sys.argv[2])
    except ValueError as error:
        sys.exit(f"configure: {error}")
