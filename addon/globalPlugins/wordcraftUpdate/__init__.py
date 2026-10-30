# Updates of the WordCraft add-on from its GitHub releases.
# Copyright (C) 2026 squalorso
# This file is covered by the GNU General Public License version 2 or later.
#
# The add-on isn't in NVDA's Add-on Store, so NVDA doesn't update it. This plugin looks at the
# add-on's GitHub releases once a day, a little after NVDA starts, and when asked from NVDA's
# Tools menu. When a newer version is out it asks; on yes it downloads the package and opens it,
# so NVDA shows its own install dialog, as when the package is opened by hand.

import json
import os
import tempfile
import threading
import time

import addonHandler
import globalPluginHandler
import globalVars
import gui
import wx
from logHandler import log

from . import releases

# The add-on's strings are English for now: no translations yet.
addonHandler.initTranslation()

# When the last check ran and which version the user turned down, so the daily check doesn't ask
# again for it (the menu still offers it).
_STATE_FILE = os.path.join(globalVars.appArgs.configPath, "wordcraftUpdate.json")
_DAY_SECONDS = 24 * 60 * 60
_START_DELAY_MS = 20000


def _readState():
	try:
		with open(_STATE_FILE, encoding="utf-8") as f:
			state = json.load(f)
		return state if isinstance(state, dict) else {}
	except (OSError, ValueError):
		return {}


def _writeState(**changes):
	state = _readState()
	state.update(changes)
	try:
		with open(_STATE_FILE, "w", encoding="utf-8") as f:
			json.dump(state, f)
	except OSError:
		log.debugWarning("WordCraft add-on: could not save the update state", exc_info=True)


def _installedVersion():
	try:
		return releases.parseVersion(addonHandler.getCodeAddon().version)
	except Exception:
		log.debugWarning("WordCraft add-on: no version of its own", exc_info=True)
		return None


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super().__init__()
		self._menuItem = None
		self._busy = False
		# Secure screens (sign-in, UAC) have no network and no NVDA menu.
		if globalVars.appArgs.secure:
			return
		toolsMenu = gui.mainFrame.sysTrayIcon.toolsMenu
		# Translators: the item in NVDA's Tools menu that looks for a new WordCraft add-on.
		self._menuItem = toolsMenu.Append(wx.ID_ANY, _("Check for WordCraft add-on &updates..."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, lambda event: self._check(manual=True), self._menuItem)
		if time.time() - _readState().get("lastCheck", 0) >= _DAY_SECONDS:
			wx.CallLater(_START_DELAY_MS, self._check, False)

	def terminate(self):
		if self._menuItem is not None:
			try:
				gui.mainFrame.sysTrayIcon.toolsMenu.Remove(self._menuItem)
			except Exception:
				pass
		super().terminate()

	def _check(self, manual):
		if self._busy:
			return
		self._busy = True
		threading.Thread(target=self._checkInBackground, args=(manual,), daemon=True).start()

	def _checkInBackground(self, manual):
		try:
			newest = releases.fetchNewest()
		except Exception:
			log.debugWarning("WordCraft add-on: update check failed", exc_info=True)
			self._busy = False
			if manual:
				wx.CallAfter(
					gui.messageBox,
					# Translators: shown when GitHub can't be reached to look for an update.
					_("Could not check for updates of the WordCraft add-on. Check the internet connection."),
					_("WordCraft add-on update"),
					wx.OK | wx.ICON_ERROR,
				)
			return
		_writeState(lastCheck=time.time())
		self._busy = False
		wx.CallAfter(self._offer, newest, manual)

	def _offer(self, newest, manual):
		installed = _installedVersion()
		current = ".".join(str(part) for part in installed) if installed else "?"
		if newest is None or installed is None or newest.version <= installed:
			log.info(f"WordCraft add-on: {current} is up to date")
			if manual:
				gui.messageBox(
					# Translators: the WordCraft add-on is already the newest version.
					_("The WordCraft add-on is up to date (version {version}).").format(version=current),
					_("WordCraft add-on update"),
					wx.OK | wx.ICON_INFORMATION,
				)
			return
		log.info(f"WordCraft add-on: version {newest.versionText} is available, {current} is installed")
		if not manual and _readState().get("skipped") == newest.versionText:
			return
		answer = gui.messageBox(
			# Translators: asks whether to install a new version of the WordCraft add-on.
			_(
				"Version {new} of the WordCraft add-on is available (you have {current}). "
				"Download and install it now?",
			).format(new=newest.versionText, current=current),
			_("WordCraft add-on update"),
			wx.YES_NO | wx.ICON_QUESTION,
		)
		if answer != wx.YES:
			_writeState(skipped=newest.versionText)
			return
		threading.Thread(target=self._downloadAndOpen, args=(newest,), daemon=True).start()

	def _downloadAndOpen(self, newest):
		folder = tempfile.mkdtemp(prefix="wordcraft-nvda-")
		path = os.path.join(folder, os.path.basename(newest.name))
		try:
			releases.download(newest, path)
		except Exception:
			log.error("WordCraft add-on: download failed", exc_info=True)
			wx.CallAfter(
				gui.messageBox,
				# Translators: shown when the new WordCraft add-on couldn't be downloaded.
				_("Could not download the WordCraft add-on. You can get it from {page}.").format(
					page=newest.page or releases.RELEASES_URL,
				),
				_("WordCraft add-on update"),
				wx.OK | wx.ICON_ERROR,
			)
			return
		log.info(f"WordCraft add-on: opening {path}")
		wx.CallAfter(_openPackage, path)


def _openPackage(path):
	"""Open the package: NVDA shows its own install dialog, as from Windows Explorer. A portable
	NVDA has no file association, so the user is told where the file is."""
	try:
		os.startfile(path)
	except OSError:
		log.error("WordCraft add-on: could not open the package", exc_info=True)
		gui.messageBox(
			# Translators: shown when the downloaded WordCraft add-on can't be opened for install.
			_("Could not open the WordCraft add-on package. Open it by hand: {path}").format(path=path),
			_("WordCraft add-on update"),
			wx.OK | wx.ICON_ERROR,
		)
