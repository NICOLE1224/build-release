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
TAG = "26.10_b202609302026"


class ImageExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name)
        self.target = self.source / "bin/targets/mediatek/filogic"
        self.target.mkdir(parents=True)

    def generate_metadata(self, device="cmcc_rax3000m"):
        # include/version.mk sanitizes '_' to '-'. Reproduce that actual
        # filename, while retaining the original tag in upstream metadata.
        prefix = f"x-wrt-26.10-b202609302026-mediatek-filogic-{device}"
        roles = [("kernel", "initramfs", "initramfs-recovery.itb" if device == "cmcc_rax3000m"
                  else "initramfs-kernel.bin"),
                 ("sysupgrade", "squashfs", "squashfs-sysupgrade.itb" if device == "cmcc_rax3000m"
                  else "squashfs-sysupgrade.bin")]
        if device.endswith("-nand-ubootlayout"):
            roles.append(("factory", "squashfs", "squashfs-factory.bin"))
        metadata = None
        for kind, filesystem, suffix in roles:
            name = f"{prefix}-{suffix}"
            (self.target / name).write_bytes(f"image fixture {name}\n".encode())
            info_file = self.source / "image.json"
            env = os.environ | {
                "FILE_DIR": str(self.target), "FILE_NAME": name,
                "FILE_TYPE": kind, "FILE_FILESYSTEM": filesystem,
                "DEVICE_ID": device, "DEVICE_IMG_PREFIX": prefix,
                "DEVICE_PACKAGES": "kmod-mt7915e", "SUPPORTED_DEVICES": "cmcc,rax3000m",
                "DEVICE_VENDOR": "CMCC", "DEVICE_MODEL": "RAX3000M",
                "TARGET": "mediatek", "SUBTARGET": "filogic",
                "VERSION_NUMBER": TAG, "VERSION_CODE": "Stonking",
                "SOURCE_DATE_EPOCH": "1790792760", "KERNEL_SIZE": "", "IMAGE_SIZE": "",
            }
            subprocess.run([sys.executable, "-B", str(UPSTREAM_INFO_SCRIPT), str(info_file)],
                           env=env, check=True, capture_output=True)
            info = json.loads(info_file.read_text())
            if metadata is None:
                metadata = info
            else:
                metadata["profiles"][device]["images"].extend(info["profiles"][device]["images"])
        (self.target / "profiles.json").write_text(json.dumps(metadata))
        return metadata

    def test_actual_upstream_metadata_exports_all_layouts_and_versioned_checksums(self):
        for device in sorted(exporter.DEVICES):
            with self.subTest(device=device), tempfile.TemporaryDirectory() as run:
                self.source = Path(run)
                self.target = self.source / "bin/targets/mediatek/filogic"
                self.target.mkdir(parents=True)
                metadata = self.generate_metadata(device)
                (self.target / "unrelated-device.bin").write_bytes(b"excluded")
                exported = exporter.export_images(self.source, TAG, device)
                expected = metadata["profiles"][device]["images"]
                self.assertEqual({p.name for p in exported}, {image["name"] for image in expected})
                self.assertTrue(all("26.10-b" in p.name for p in exported))
                checksum = self.source / "rom" / f"sha256-{TAG}.sum"
                self.assertEqual(checksum.read_text(), "".join(
                    f'{image["sha256"]}  {image["name"]}\n' for image in expected))
                self.assertEqual(len(list((self.source / "rom").iterdir())), len(expected) + 1)

    def test_corrupted_image_is_rejected_before_export(self):
        metadata = self.generate_metadata()
        (self.target / metadata["profiles"]["cmcc_rax3000m"]["images"][0]["name"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "differs from build metadata"):
            exporter.export_images(self.source, TAG, "cmcc_rax3000m")
        self.assertFalse((self.source / "rom").exists())

    def test_missing_image_is_rejected_before_export(self):
        metadata = self.generate_metadata()
        (self.target / metadata["profiles"]["cmcc_rax3000m"]["images"][1]["name"]).unlink()
        with self.assertRaisesRegex(ValueError, "missing or empty firmware"):
            exporter.export_images(self.source, TAG, "cmcc_rax3000m")
        self.assertFalse((self.source / "rom").exists())

    def test_wrong_release_target_and_device_are_rejected(self):
        for field, value in (("version_number", "wrong-release"), ("target", "ramips/mt7621")):
            metadata = self.generate_metadata()
            metadata[field] = value
            (self.target / "profiles.json").write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "target and release"):
                exporter.export_images(self.source, TAG, "cmcc_rax3000m")
        self.generate_metadata()
        with self.assertRaisesRegex(ValueError, "selected device"):
            exporter.export_images(self.source, TAG, "cmcc_rax3000m-emmc-ubootlayout")

    def test_ambiguous_sysupgrade_is_rejected(self):
        metadata = self.generate_metadata()
        images = metadata["profiles"]["cmcc_rax3000m"]["images"]
        images.append(images[1].copy())
        (self.target / "profiles.json").write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, "exactly one squashfs sysupgrade"):
            exporter.export_images(self.source, TAG, "cmcc_rax3000m")

    def test_metadata_cannot_reference_a_path_outside_target(self):
        metadata = self.generate_metadata()
        metadata["profiles"]["cmcc_rax3000m"]["images"][0]["name"] = "../foreign.itb"
        (self.target / "profiles.json").write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, "invalid firmware filename"):
            exporter.export_images(self.source, TAG, "cmcc_rax3000m")


if __name__ == "__main__":
    unittest.main()
