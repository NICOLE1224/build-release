#!/usr/bin/env python3
"""Reject missing per-device build selections immediately after defconfig."""
import json
import re
import sys
from pathlib import Path


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
    missing = sorted(package for package in requested
                     if values.get(f"CONFIG_PACKAGE_{package}") not in ("y", "m"))
    if missing:
        raise ValueError("device packages are not selected for compilation: " + ", ".join(missing))
    required = (Path(__file__).parent / "packages.required").read_text().splitlines()
    for package in required:
        if package and not package.startswith("#") and values.get(f"CONFIG_PACKAGE_{package}") != "y":
            raise ValueError(f"required package is not built in: {package}")
    print(f"Verified {device}: all {len(requested)} device packages selected for compilation")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: verify-config.py SOURCE_ROOT DEVICE")
    try:
        verify(Path(sys.argv[1]), sys.argv[2])
    except ValueError as error:
        sys.exit(f"configure: {error}")
