# The WordCraft add-on's releases on GitHub: which one is newest, and whether it is newer.
# Copyright (C) 2026 squalorso
# This file is covered by the GNU General Public License version 2 or later.
#
# No NVDA imports here, so it can be tried with plain Python.

import json
import re
import urllib.request

REPOSITORY = "squalorso/wordcraft-nvda"
RELEASES_URL = f"https://api.github.com/repos/{REPOSITORY}/releases"
# Packages are only taken from the repository's own release downloads.
DOWNLOAD_PREFIX = f"https://github.com/{REPOSITORY}/releases/download/"
TIMEOUT_SECONDS = 20
# Largest package accepted (the add-on is a few kilobytes).
MAX_PACKAGE_BYTES = 20 * 1024 * 1024


def parseVersion(text):
	"""(0, 2, 1) from "0.2.1" or "v0.2.1", (0, 2, 1, 1) from "0.2.1.1"; None if it isn't a
	version. Versions have at least three numbers ("0.2" is 0.2.0), and zeros after the third
	don't count ("0.2.1.0" is 0.2.1), so the tuples compare as the versions do."""
	match = re.fullmatch(r"v?(\d+(?:\.\d+)+)", (text or "").strip())
	if not match:
		return None
	parts = [int(part) for part in match.group(1).split(".")]
	parts += [0] * (3 - len(parts))
	while len(parts) > 3 and parts[-1] == 0:
		parts.pop()
	return tuple(parts)


class Release:
	"""A release with an add-on package."""

	def __init__(self, version, versionText, url, name, size, sha256, page):
		self.version = version
		self.versionText = versionText
		self.url = url
		self.name = name
		self.size = size
		self.sha256 = sha256
		self.page = page


def newest(releases):
	"""The release with the highest version that has an .nvda-addon package, or None. Betas
	count: every release of this add-on is one so far."""
	best = None
	for release in releases:
		if not isinstance(release, dict) or release.get("draft"):
			continue
		version = parseVersion(release.get("tag_name"))
		if version is None:
			continue
		for asset in release.get("assets") or []:
			name = asset.get("name") or ""
			url = asset.get("browser_download_url") or ""
			if not name.endswith(".nvda-addon") or not url.startswith(DOWNLOAD_PREFIX):
				continue
			digest = asset.get("digest") or ""
			sha256 = digest[len("sha256:") :] if digest.startswith("sha256:") else None
			if best is None or version > best.version:
				best = Release(
					version,
					".".join(str(part) for part in version),
					url,
					name,
					asset.get("size"),
					sha256,
					release.get("html_url") or "",
				)
			break
	return best


def _get(url):
	request = urllib.request.Request(
		url,
		headers={"Accept": "application/vnd.github+json", "User-Agent": "wordcraft-nvda-updater"},
	)
	return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS)


def fetchNewest():
	"""The newest release on GitHub (network errors propagate)."""
	with _get(RELEASES_URL) as response:
		return newest(json.loads(response.read().decode("utf-8")))


def download(release, path):
	"""Save the release's package to `path`, checking its size and, when GitHub gives one, its
	SHA-256. Raises ValueError if the file isn't the one announced."""
	import hashlib

	digest = hashlib.sha256()
	total = 0
	with _get(release.url) as response, open(path, "wb") as out:
		while True:
			chunk = response.read(65536)
			if not chunk:
				break
			total += len(chunk)
			if total > MAX_PACKAGE_BYTES:
				raise ValueError("package too large")
			digest.update(chunk)
			out.write(chunk)
	if isinstance(release.size, int) and total != release.size:
		raise ValueError(f"package size {total}, expected {release.size}")
	if release.sha256 and digest.hexdigest() != release.sha256.lower():
		raise ValueError("package checksum doesn't match")
