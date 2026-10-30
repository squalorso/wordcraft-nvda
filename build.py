"""Build the add-on package: python build.py -> wordcraft-<version>.nvda-addon.

Translations (addon/locale/<lang>/LC_MESSAGES/nvda.po) go into the package compiled, as the
nvda.mo files NVDA reads."""

import ast
import pathlib
import re
import struct
import zipfile

root = pathlib.Path(__file__).resolve().parent
addon = root / "addon"


def parse_po(text):
	"""The (msgid, msgstr) pairs of a .po file with single-form entries."""
	entries, msgid, msgstr, field = [], None, None, None
	for line in text.splitlines() + [""]:
		line = line.strip()
		if line.startswith("msgid "):
			if msgid is not None:
				entries.append((msgid, msgstr or ""))
			msgid, msgstr, field = ast.literal_eval(line[6:]), None, "id"
		elif line.startswith("msgstr "):
			msgstr, field = ast.literal_eval(line[7:]), "str"
		elif line.startswith('"'):
			if field == "id":
				msgid += ast.literal_eval(line)
			elif field == "str":
				msgstr += ast.literal_eval(line)
		elif not line and msgid is not None:
			entries.append((msgid, msgstr or ""))
			msgid, msgstr, field = None, None, None
	return [(i, s) for i, s in entries if s]


def mo_bytes(entries):
	"""A GNU gettext .mo file of the entries."""
	entries = sorted(entries)
	ids = [i.encode("utf-8") for i, _ in entries]
	strs = [s.encode("utf-8") for _, s in entries]
	n = len(entries)
	start = 7 * 4 + 16 * n
	table, data = [], b""
	for blobs in (ids, strs):
		for b in blobs:
			table.append((len(b), start + len(data)))
			data += b + b"\0"
	header = struct.pack("<7I", 0x950412DE, 0, n, 7 * 4, 7 * 4 + 8 * n, 0, 0)
	return header + b"".join(struct.pack("<2I", *t) for t in table) + data


manifest = (addon / "manifest.ini").read_text(encoding="utf-8")
version = re.search(r"^version\s*=\s*(\S+)", manifest, re.MULTILINE).group(1)
out = root / f"wordcraft-{version}.nvda-addon"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
	for path in sorted(addon.rglob("*")):
		if not path.is_file() or "__pycache__" in path.parts:
			continue
		name = path.relative_to(addon).as_posix()
		if path.suffix == ".po":
			z.writestr(name[: -len(".po")] + ".mo", mo_bytes(parse_po(path.read_text(encoding="utf-8"))))
		else:
			z.write(path, name)
print(out.name)
