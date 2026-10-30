# WordCraft add-on for NVDA (beta)

An NVDA add-on for [WordCraft](https://github.com/storytold/wordcraft), the open-source word processor. It gives WordCraft's document NVDA's browse mode and table navigation, as NVDA does for Microsoft Word.

**Status: beta.** It's for people testing and developing WordCraft's screen reader support, while that support is being built. It isn't in the NVDA Add-on Store.

## Why it's needed

NVDA gives browse mode to a UI Automation document only in applications it knows: Word, web browsers and a few others, which it recognises by name. In any other application, NVDA+Space does nothing in the document, so the quick navigation keys (H, K, L, T…) aren't there.

This add-on is one small app module (`addon/appModules/wordcraft.py`). For WordCraft's document it:
- gives NVDA's own UI Automation browse mode, started with NVDA+Space as in Word. The document opens in focus mode;
- makes Ctrl+Alt+arrows move between table cells in focus mode, as in Word;
- announces a list once, with its number of items, on entering it, and again on leaving it, as for web pages. Without the add-on NVDA says "list" on every line of it: it takes a UI Automation list that isn't read-only for a list box, and corrects that only for applications it knows;
- announces the cell Tab and Shift+Tab move to in a table (its row and column, then its text), as NVDA does in Word.

Everything NVDA reads (headings, links, lists, tables, formatting, spelling errors) comes from what WordCraft exposes. Focus mode works without the add-on, apart from those lists and Tab in tables.

## What to expect

It works best with the WordCraft build of [storytold/wordcraft#4951](https://github.com/storytold/wordcraft/pull/4951), where the document is one text on Windows:
- browse mode reads the whole document;
- H and 1–6 find headings by their style, K links, L lists, T tables.

With that build, on a test document, 119 of 150 scripted NVDA 2026.2 steps said the same as Word. Most of the others are lists: Word hides them from NVDA, and this add-on announces them as web pages do. With H, browse mode went through all 30 headings of a 48-page document.

With WordCraft's `main` as of October 2026, the document is described node by node for the pages on screen only. Browse mode then sees only those pages, and H finds no headings.

## Install

1. Download `wordcraft-<version>.nvda-addon` from [Releases](https://github.com/squalorso/wordcraft-nvda/releases).
2. Open it: NVDA asks whether to install it.
3. Restart NVDA.

If you have a `wordcraft.py` app module of your own in NVDA's developer scratchpad (`%APPDATA%\nvda\scratchpad\appModules`), remove it first, or the two will clash.

Tested with NVDA 2026.2 on Windows 11.

## Not covered

- JAWS: it needs its own scripts for WordCraft.
- Braille output hasn't been checked.
- Other platforms: NVDA is Windows only.

## Build

```
python build.py
```

This writes `wordcraft-<version>.nvda-addon`, a zip of the `addon` folder.

## Feedback

Issues here, or in WordCraft's accessibility tracking issue, [storytold/craft-libs#437](https://github.com/storytold/craft-libs/issues/437). Please say your NVDA version, your Windows version, which WordCraft build you used, and what you heard.

## License

GNU General Public License version 2 or later, like NVDA: see [LICENSE](LICENSE).

AI-assisted: written with Claude Code.
