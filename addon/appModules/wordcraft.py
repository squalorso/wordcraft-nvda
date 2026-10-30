# WordCraft app module for NVDA: browse mode and table navigation in the document.
# Copyright (C) 2026 squalorso
# This file is covered by the GNU General Public License version 2 or later.
#
# NVDA gives browse mode to a UI Automation document only in applications it knows (Word,
# browsers, a few others, recognised by name). In any other application NVDA+Space does nothing.
# This module gives WordCraft's document NVDA's own UI Automation browse mode, started with
# NVDA+Space as in Word, and Ctrl+Alt+arrows table navigation in focus mode. Everything else
# (headings, links, lists, tables, formatting, errors) comes from what WordCraft exposes.
#
# Two more things NVDA does only for applications it knows, done here as NVDA does them:
# - a list in the text is announced on entering and leaving it, not on every line: NVDA takes a
#   UI Automation list that isn't read-only for a list box, as it does for Word and web pages;
# - Tab and Shift+Tab in a table announce the cell they move to, as in Word.

import appModuleHandler
import controlTypes
import speech
import textInfos
import UIAHandler
from NVDAObjects.UIA import UIA, UIATextInfo
from scriptHandler import script
from UIAHandler.browseMode import UIABrowseModeDocument, UIADocumentWithTableNavigation


class WordCraftTextInfo(UIATextInfo):
	"""The document's text, with its lists read as lists in a document."""

	def _getControlFieldForUIAObject(self, obj, isEmbedded=False, startOfNode=False, endOfNode=False):
		field = super()._getControlFieldForUIAObject(
			obj,
			isEmbedded=isEmbedded,
			startOfNode=startOfNode,
			endOfNode=endOfNode,
		)
		if field.get("role") == controlTypes.Role.LIST:
			# Read-only: a list of the text, which NVDA announces on entering and leaving, rather than
			# a list box, announced on every line (as NVDA does for Word and web pages).
			field["states"].add(controlTypes.State.READONLY)
			# Its number of items, from its first item's place in it, as for web pages.
			try:
				child = UIAHandler.handler.clientObject.ControlViewWalker.GetFirstChildElement(obj.UIAElement)
				count = child.getCurrentPropertyValue(UIAHandler.UIA_SizeOfSetPropertyId) if child else 0
			except Exception:
				count = 0
			if isinstance(count, int) and count > 0:
				field["_childcontrolcount"] = count
		return field


def _inTableCell(info):
	"""Whether the text starts inside a table cell."""
	for command in info.getTextWithFields():
		if not isinstance(command, textInfos.FieldCommand) or command.command != "controlStart":
			return False
		if command.field.get("role") == controlTypes.Role.TABLECELL:
			return True
	return False


class WordCraftDocument(UIADocumentWithTableNavigation, UIA):
	"""WordCraft's document, with browse mode and table navigation."""

	TextInfo = WordCraftTextInfo
	treeInterceptorClass = UIABrowseModeDocument
	# As in Word, the document opens in focus mode, and NVDA+Space switches to browse mode.
	shouldCreateTreeInterceptor = False

	@script(gestures=["kb:tab", "kb:shift+tab"])
	def script_tab(self, gesture):
		# In a table WordCraft moves to the next (or previous) cell and selects its text: announce
		# the cell, as in Word. Elsewhere Tab types a tab or changes a list item's level, as usual.
		old = self.makeTextInfo(textInfos.POSITION_CARET).bookmark
		gesture.send()
		moved, info = self._hasCaretMoved(old)
		if not info:
			return
		info = self.makeTextInfo(textInfos.POSITION_SELECTION)
		if info.isCollapsed:
			info.expand(textInfos.UNIT_PARAGRAPH)
			if not _inTableCell(info):
				return
		speech.speakTextInfo(info, reason=controlTypes.OutputReason.FOCUS)


class AppModule(appModuleHandler.AppModule):
	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		# Only the document: WordCraft's dialogs and ribbon keep NVDA's usual behaviour.
		if isinstance(obj, UIA) and obj.UIATextPattern and obj.role == controlTypes.Role.DOCUMENT:
			clsList.insert(0, WordCraftDocument)
