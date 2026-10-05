#!/usr/bin/env python3
"""Check the prepared LuCI payload against the service's installed files."""
import json
import re
import sys
from pathlib import Path

app, service = map(Path, sys.argv[1:])
recipe = (service / "Makefile").read_text()
install = recipe.split("define Package/vlmcsd/install\n", 1)[1].split("\nendef", 1)[0]
service_files = set()
for line in install.splitlines():
    if "$(INSTALL_DIR)" not in line:
        service_files.update(re.findall(r"\$\(1\)(/\S+)", line))
app_files = {"/" + path.relative_to(app / "root").as_posix()
             for path in (app / "root").rglob("*") if path.is_file()}
overlap = app_files & service_files
assert not overlap, f"VLMCSd package file ownership conflict: {sorted(overlap)}"
assert "/etc/config/vlmcsd" in service_files, "service UCI config is missing"

ini = "/etc/vlmcsd.ini"
assert ini in service_files, "service INI file is missing"
init = (service / "files/vlmcsd.init").read_text()
assert re.search(rf'^INI_FILE=[\"\']?{re.escape(ini)}[\"\']?$', init, re.M), "service uses a different INI file"
assert 'procd_add_reload_trigger "$CONF"' in init, "service UCI reload trigger is missing"
basic = (app / "luasrc/model/cbi/vlmcsd/basic.lua").read_text()
defaults = (service / "files/vlmcsd.config").read_text()
for option in re.findall(r's:option\(Flag, "([^"]+)"', basic):
    assert re.search(rf"option\s+{re.escape(option)}\s", defaults), f"unknown UCI option: {option}"
config = (app / "luasrc/model/cbi/vlmcsd/config.lua").read_text()
assert config.count(ini) == 3, "LuCI INI editor does not match the service"
assert "/etc/init.d/vlmcsd reload" in config, "INI changes must reload the service"
acl = json.loads((app / "root/usr/share/rpcd/acl.d/luci-app-vlmcsd.json").read_text())
for access in ("read", "write"):
    assert acl["luci-app-vlmcsd"][access]["file"][ini] == [access], "INI ACL mismatch"
for path in list((app / "root").rglob("*")) + list((app / "luasrc").rglob("*")):
    if path.is_file() and path.suffix != ".lmo":
        text = path.read_text()
        assert "/etc/vlmcsd/vlmcsd.ini" not in text, f"obsolete INI path in {path}"
        assert "/etc/init.d/kms" not in text, f"obsolete init script in {path}"
print("VLMCSd integration verified: unique file ownership, UCI options, INI path, reload and ACL")
