#!/usr/bin/env python3
"""Adapt the pinned legacy LuCI app to X-WRT and the pinned VLMCSd service."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
makefile = root / "Makefile"
text = makefile.read_text()
assert text.count("include ../../luci.mk") == 1, "unexpected LuCI include"
assert text.count("LUCI_DEPENDS:=+vlmcsd") == 1, "unexpected LuCI dependencies"
text = text.replace("include ../../luci.mk", "include $(TOPDIR)/feeds/luci/luci.mk")
text = text.replace("LUCI_DEPENDS:=+vlmcsd", "LUCI_DEPENDS:=+vlmcsd +luci-compat")
assert text.count("PKG_RELEASE:=6") == 1, "unexpected LuCI package release"
text = text.replace("PKG_RELEASE:=6", "PKG_RELEASE:=7")
makefile.write_text(text, newline="\n")
# The service package owns its configuration, procd init and UCI defaults.
# The legacy app's defaults also refer to the obsolete kms init script.
for relative in ("etc/config/vlmcsd", "etc/init.d/kms", "etc/uci-defaults/luci-vlmcsd"):
    (root / "root" / relative).unlink()

basic = root / "luasrc/model/cbi/vlmcsd/basic.lua"
text = basic.read_text()
assert text.count('"autoactivate"') == 1, "unexpected auto activation option"
basic.write_text(text.replace('"autoactivate"', '"auto_activate"'), newline="\n")

config = root / "luasrc/model/cbi/vlmcsd/config.lua"
text = config.read_text()
assert text.count("/etc/vlmcsd/vlmcsd.ini") == 3, "unexpected VLMCSd INI path"
text = text.replace("/etc/vlmcsd/vlmcsd.ini", "/etc/vlmcsd.ini")
write = '\tnixio.fs.writefile("/etc/vlmcsd.ini", value)'
assert text.count(write) == 1, "unexpected VLMCSd INI writer"
text = text.replace(write, '\tif nixio.fs.writefile("/etc/vlmcsd.ini", value) then\n'
                          '\t\trequire("luci.sys").call("/etc/init.d/vlmcsd reload >/dev/null 2>&1")\n'
                          '\tend')
config.write_text(text, newline="\n")

controller = root / "luasrc/controller/vlmcsd.lua"
text = controller.read_text()
marker = '\tentry({"admin", "services", "vlmcsd"},'
assert text.count(marker) == 1, "unexpected VLMCSd controller"
text = text.replace(marker, '\tlocal page = entry({"admin", "services", "vlmcsd"},', 1)
text = text.replace('100).dependent = true', '100)\n\tpage.dependent = true\n\tpage.acl_depends = { "luci-app-vlmcsd" }', 1)
controller.write_text(text, newline="\n")
acl = root / "root/usr/share/rpcd/acl.d/luci-app-vlmcsd.json"
acl.parent.mkdir(parents=True, exist_ok=True)
acl.write_text(json.dumps({"luci-app-vlmcsd": {
    "description": "Grant access to the VLMCSd configuration",
    "read": {"uci": ["vlmcsd"], "file": {"/etc/vlmcsd.ini": ["read"]}},
    "write": {"uci": ["vlmcsd"], "file": {"/etc/vlmcsd.ini": ["write"]}},
}}, indent=2) + "\n", newline="\n")
