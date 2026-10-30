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
# More things NVDA does only for applications it knows, done here as NVDA does them:
# - a list in the text is announced on entering and leaving it, not on every line: NVDA takes a
#   UI Automation list that isn't read-only for a list box, as it does for Word and web pages;
# - Tab and Shift+Tab in a table announce the cell they move to, as in Word;
# - the page and the section are announced when they change (with "Report pages" on), as in
#   Word. NVDA gets them from Word through an extension of Word's own; here the page is counted
#   with UI Automation's page unit, and the section is the numbered pane WordCraft puts around
#   each section's text.

from comtypes import COMError

import appModuleHandler
import controlTypes
import speech
import textInfos
import UIAHandler
from NVDAObjects.UIA import UIA, UIATextInfo
from scriptHandler import script
from UIAHandler.browseMode import UIABrowseModeDocument, UIADocumentWithTableNavigation

# More pages than any document has: moving back by this many reaches the first page.
_MANY_PAGES = 1000000
# How far up from a position the section's pane can be (table cell, list item, link…).
_MAX_DEPTH = 20


def _isSection(element):
	"""Whether a UI Automation element is one of the document's sections: a pane with no name
	and a place among the sections."""
	if element.CurrentControlType != UIAHandler.UIA_PaneControlTypeId or element.CurrentName:
		return False
	number = element.GetCurrentPropertyValue(UIAHandler.UIA_PositionInSetPropertyId)
	return isinstance(number, int) and number > 0


class WordCraftTextInfo(UIATextInfo):
	"""The document's text, with its lists read as lists in a document, and its page and section."""

	def _getControlFieldForUIAObject(self, obj, isEmbedded=False, startOfNode=False, endOfNode=False):
		field = super()._getControlFieldForUIAObject(
			obj,
			isEmbedded=isEmbedded,
			startOfNode=startOfNode,
			endOfNode=endOfNode,
		)
		if field.get("role") == controlTypes.Role.PANE and _isSection(obj.UIAElement):
			# A section, which the format fields announce by number.
			field["role"] = controlTypes.Role.SECTION
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

	def _get_NVDAObjectAtStart(self):
		# A section's pane is structure around the text, not an object: the document stands for it.
		# Otherwise, back in focus mode from browse mode, NVDA moves the review to the pane as the
		# object at the caret, and a braille display shows "pane 1 of 1 lv 1" before the line.
		obj = super()._get_NVDAObjectAtStart()
		if isinstance(obj, UIA) and obj.UIAElement and _isSection(obj.UIAElement):
			return self.obj
		return obj

	def _getFormatFieldAtRange(self, textRange, formatConfig, ignoreMixedValues=False):
		formatField = super()._getFormatFieldAtRange(
			textRange,
			formatConfig,
			ignoreMixedValues=ignoreMixedValues,
		)
		if formatField and formatConfig["reportPage"]:
			try:
				page, section = self._pageAndSection(textRange)
			except COMError:
				page = section = None
			if page:
				formatField.field["page-number"] = page
			if section:
				formatField.field["section-number"] = section
		return formatField

	def _pageAndSection(self, textRange):
		"""The page and the section where the range starts, counted from 1."""
		at = textRange.Clone()
		at.MoveEndpointByRange(
			UIAHandler.TextPatternRangeEndpoint_End,
			at,
			UIAHandler.TextPatternRangeEndpoint_Start,
		)
		section = None
		element = at.GetEnclosingElement()
		root = self.obj.UIAElement
		walker = UIAHandler.handler.clientObject.RawViewWalker
		for _ in range(_MAX_DEPTH):
			if not element or UIAHandler.handler.clientObject.compareElements(element, root):
				break
			if _isSection(element):
				section = element.GetCurrentPropertyValue(UIAHandler.UIA_PositionInSetPropertyId)
				break
			element = walker.GetParentElement(element)
		# From the start of the page, back to the start of the first: one move per page before.
		at.ExpandToEnclosingUnit(UIAHandler.TextUnit_Page)
		moved = at.MoveEndpointByUnit(
			UIAHandler.TextPatternRangeEndpoint_Start,
			UIAHandler.TextUnit_Page,
			-_MANY_PAGES,
		)
		return 1 - moved, section


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
