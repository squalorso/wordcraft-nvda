# WordCraft app module for NVDA: browse mode and table navigation in the document.
# Copyright (C) 2026 squalorso
# This file is covered by the GNU General Public License version 2 or later.
#
# NVDA gives browse mode to a UI Automation document only in applications it knows (Word,
# browsers, a few others, recognised by name). In any other application NVDA+Space does nothing.
# This module gives WordCraft's document NVDA's own UI Automation browse mode, started with
# NVDA+Space as in Word, and Ctrl+Alt+arrows table navigation in focus mode. Everything else
# (headings, links, lists, tables, formatting, errors) comes from what WordCraft exposes.

import appModuleHandler
import controlTypes
from NVDAObjects.UIA import UIA
from UIAHandler.browseMode import UIABrowseModeDocument, UIADocumentWithTableNavigation


class WordCraftDocument(UIADocumentWithTableNavigation, UIA):
	"""WordCraft's document, with browse mode and table navigation."""

	treeInterceptorClass = UIABrowseModeDocument
	# As in Word, the document opens in focus mode, and NVDA+Space switches to browse mode.
	shouldCreateTreeInterceptor = False


class AppModule(appModuleHandler.AppModule):
	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		# Only the document: WordCraft's dialogs and ribbon keep NVDA's usual behaviour.
		if isinstance(obj, UIA) and obj.UIATextPattern and obj.role == controlTypes.Role.DOCUMENT:
			clsList.insert(0, WordCraftDocument)
