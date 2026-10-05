#!/usr/bin/env python3
"""Export this device's verified images using X-WRT's generated metadata."""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from configure import DEVICES


def export_images(source: Path, tag: str, device: str) -> list[Path]:
    if device not in DEVICES or not re.fullmatch(r"\d+\.\d+_b\d{12}", tag):
        raise ValueError("invalid release tag or device")
    target = source / "bin/targets/mediatek/filogic"
    metadata = json.loads((target / "profiles.json").read_text(encoding="utf-8"))
    if metadata.get("target") != "mediatek/filogic" or metadata.get("version_number") != tag:
        raise ValueError("image metadata does not match the requested target and release")
    profiles = metadata.get("profiles", {})
    if set(profiles) != {device}:
        raise ValueError("image metadata does not contain exactly the selected device")
    images = profiles[device]["images"]
    selected = []
    for kind, filesystem in (("kernel", "initramfs"), ("sysupgrade", "squashfs")):
        matches = [image for image in images
                   if image.get("type") == kind and image.get("filesystem") == filesystem]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one {filesystem} {kind} image, found {len(matches)}")
        selected.extend(matches)
    factories = [image for image in images
                 if image.get("type") == "factory" and image.get("filesystem") == "squashfs"]
    if len(factories) > 1 or (device.endswith("-nand-ubootlayout") and len(factories) != 1):
        raise ValueError("missing or ambiguous NAND factory image")
    selected.extend(factories)

    # Validate the entire set before exporting anything. Names come from the
    # build rather than reconstructing OpenWrt's version sanitization rules.
    checked = []
    for image in selected:
        name = image["name"]
        if not re.fullmatch(r"[A-Za-z0-9._-]+\.(bin|itb)", name):
            raise ValueError(f"invalid firmware filename in metadata: {name}")
        path = target / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"missing or empty firmware: {name}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != image.get("sha256") or path.stat().st_size != image.get("size"):
            raise ValueError(f"firmware differs from build metadata: {name}")
        checked.append((path, digest))
    output = source / "rom"
    if output.exists() and any(output.iterdir()):
        raise ValueError("firmware export directory must be empty")
    output.mkdir(exist_ok=True)
    exported = []
    for path, digest in checked:
        destination = output / path.name
        shutil.copyfile(path, destination)
        exported.append(destination)
        print(f"Exported {path.name} (sha256 {digest})")
    checksum = output / f"sha256-{tag}.sum"
    checksum.write_text("".join(f"{digest}  {path.name}\n" for path, digest in checked),
                        encoding="utf-8", newline="\n")
    return exported


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: export-images.py SOURCE_ROOT RELEASE_TAG DEVICE")
    try:
        export_images(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
    except (ValueError, OSError, KeyError, TypeError) as error:
        sys.exit(f"export: {error}")
