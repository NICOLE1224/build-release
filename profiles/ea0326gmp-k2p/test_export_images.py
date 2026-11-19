#!/usr/bin/env python3
"""Exercise the exporter with metadata produced by the selected upstream tag."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("export_images", Path(__file__).with_name("export-images.py"))
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)
UPSTREAM_INFO_SCRIPT = Path(sys.argv.pop(1)).resolve()
TAG = "26.10_b202611171234"
# Image roles as defined by the upstream device recipes.
ROLES = {
    "nokia_ea0326gmp": [("kernel", "initramfs", "initramfs-recovery.itb"),
                        ("sysupgrade", "squashfs", "squashfs-sysupgrade.itb"),
                        ("preloader.bin", None, "preloader.bin"),
                        ("bl31-uboot.fip", None, "bl31-uboot.fip")],
    "phicomm_k2p": [("kernel", "initramfs", "initramfs-kernel.bin"),
                    ("sysupgrade", "squashfs", "squashfs-sysupgrade.bin")],
}


class ImageExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name)

    def target_dir(self, device):
        spec = exporter.DEVICES[device]
        target = self.source / "bin/targets" / spec.target / spec.subtarget
        target.mkdir(parents=True, exist_ok=True)
        return target

    def generate_metadata(self, device="nokia_ea0326gmp", roles=None):
        spec = exporter.DEVICES[device]
        target = self.target_dir(device)
        # include/version.mk sanitizes '_' to '-'. Reproduce that actual
        # filename, while retaining the original tag in upstream metadata.
        prefix = f"x-wrt-26.10-b202611171234-{spec.target}-{spec.subtarget}-{device}"
        metadata = None
        for kind, filesystem, suffix in roles or ROLES[device]:
            name = f"{prefix}-{suffix}"
            (target / name).write_bytes(f"image fixture {name}\n".encode())
            info_file = self.source / "image.json"
            env = os.environ | {
                "FILE_DIR": str(target), "FILE_NAME": name, "FILE_TYPE": kind,
                "DEVICE_ID": device, "DEVICE_IMG_PREFIX": prefix,
                "DEVICE_PACKAGES": "", "SUPPORTED_DEVICES": device.replace("_", ","),
                "DEVICE_VENDOR": "Vendor", "DEVICE_MODEL": "Model",
                "TARGET": spec.target, "SUBTARGET": spec.subtarget,
                "VERSION_NUMBER": TAG, "VERSION_CODE": "Stonking",
                "SOURCE_DATE_EPOCH": "1790792760", "KERNEL_SIZE": "", "IMAGE_SIZE": "",
            }
            env.pop("FILE_FILESYSTEM", None)
            if filesystem:
                env["FILE_FILESYSTEM"] = filesystem
            subprocess.run([sys.executable, "-B", str(UPSTREAM_INFO_SCRIPT), str(info_file)],
                           env=env, check=True, capture_output=True)
            info = json.loads(info_file.read_text())
            if metadata is None:
                metadata = info
            else:
                metadata["profiles"][device]["images"].extend(info["profiles"][device]["images"])
        (target / "profiles.json").write_text(json.dumps(metadata))
        return metadata

    def test_actual_upstream_metadata_exports_images_and_versioned_checksums(self):
        for device in sorted(exporter.DEVICES):
            with self.subTest(device=device), tempfile.TemporaryDirectory() as run:
                self.source = Path(run)
                metadata = self.generate_metadata(device)
                (self.target_dir(device) / "unrelated-device.bin").write_bytes(b"excluded")
                exported = exporter.export_images(self.source, TAG, device)
                expected = metadata["profiles"][device]["images"]
                self.assertEqual({p.name for p in exported}, {image["name"] for image in expected})
                checksum = self.source / "rom" / f"sha256-{TAG}-{device}.sum"
                self.assertEqual(checksum.read_text(), "".join(
                    f'{image["sha256"]}  {image["name"]}\n' for image in expected))
                self.assertEqual(len(list((self.source / "rom").iterdir())), len(expected) + 1)

    def test_bootloader_artifacts_are_optional(self):
        self.generate_metadata(roles=ROLES["nokia_ea0326gmp"][:2])
        self.assertEqual(len(exporter.export_images(self.source, TAG, "nokia_ea0326gmp")), 2)

    def test_corrupted_image_is_rejected_before_export(self):
        metadata = self.generate_metadata("phicomm_k2p")
        name = metadata["profiles"]["phicomm_k2p"]["images"][0]["name"]
        (self.target_dir("phicomm_k2p") / name).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "differs from build metadata"):
            exporter.export_images(self.source, TAG, "phicomm_k2p")
        self.assertFalse((self.source / "rom").exists())

    def test_missing_image_is_rejected_before_export(self):
        metadata = self.generate_metadata()
        name = metadata["profiles"]["nokia_ea0326gmp"]["images"][1]["name"]
        (self.target_dir("nokia_ea0326gmp") / name).unlink()
        with self.assertRaisesRegex(ValueError, "missing or empty firmware"):
            exporter.export_images(self.source, TAG, "nokia_ea0326gmp")
        self.assertFalse((self.source / "rom").exists())

    def test_wrong_release_and_target_are_rejected(self):
        for field, value in (("version_number", "wrong-release"), ("target", "ramips/mt7621")):
            metadata = self.generate_metadata()
            metadata[field] = value
            (self.target_dir("nokia_ea0326gmp") / "profiles.json").write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "target and release"):
                exporter.export_images(self.source, TAG, "nokia_ea0326gmp")

    def test_missing_sysupgrade_is_rejected(self):
        self.generate_metadata("phicomm_k2p", roles=ROLES["phicomm_k2p"][:1])
        with self.assertRaisesRegex(ValueError, "exactly one squashfs sysupgrade"):
            exporter.export_images(self.source, TAG, "phicomm_k2p")

    def test_metadata_cannot_reference_a_path_outside_target(self):
        metadata = self.generate_metadata()
        metadata["profiles"]["nokia_ea0326gmp"]["images"][0]["name"] = "../foreign.itb"
        (self.target_dir("nokia_ea0326gmp") / "profiles.json").write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, "invalid firmware filename"):
            exporter.export_images(self.source, TAG, "nokia_ea0326gmp")


if __name__ == "__main__":
    unittest.main()
