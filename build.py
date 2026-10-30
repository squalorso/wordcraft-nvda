"""Build the add-on package: python build.py -> wordcraft-<version>.nvda-addon."""

import pathlib
import re
import zipfile

root = pathlib.Path(__file__).resolve().parent
addon = root / "addon"
manifest = (addon / "manifest.ini").read_text(encoding="utf-8")
version = re.search(r"^version\s*=\s*(\S+)", manifest, re.MULTILINE).group(1)
out = root / f"wordcraft-{version}.nvda-addon"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
	for path in sorted(addon.rglob("*")):
		if path.is_file() and "__pycache__" not in path.parts:
			z.write(path, path.relative_to(addon).as_posix())
print(out.name)
