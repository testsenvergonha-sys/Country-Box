# Changelog

## Unreleased — next version (1.0.6), in testing

- **Installing from RecompLauncher.** It didn't work properly: after picking your copy, setup stopped with "Its setup
  program is missing", so installing and launching from RecompLauncher wasn't reliable. Country-Box's RecompLauncher
  file pointed at the wrong program. That file is fixed now, and RecompLauncher reads it straight from this
  repository, so the fix applies without waiting for a new version. This should fix it; I'm on it and testing it on
  a Steam Deck right now.
- **Steam Deck: prepare the game on the Deck itself.** SteamOS has no compiler, so until now a Deck could only play a
  build made on a PC. Country-Box now carries the tools it needs to prepare the game. They are used only while a game
  is being prepared, and nothing is installed on your system. Because of that, **the download grows from about 10 MB
  to about 200 MB**.
- **An update never takes PLAY away.** After updating Country-Box, your games keep playing as before; *Prepare
  update* is optional and brings the newest fixes when you like. Until now the card asked you to prepare first, which
  on a Steam Deck meant you couldn't play.
- **B exits** Country-Box from the Games tab (handy on the Steam Deck).
- About: the text no longer runs past the bottom of the panel on the Steam Deck's screen.
- Steam Deck: with FSR on, the picture looked blocky. The Deck's screen is only slightly taller than the game's
  picture, and FSR is made for bigger enlargements; for small ones the regular scaling is used now, which looks
  smoother.
- Start a game directly, skipping the launcher: `--returns` or `--freeze` (also `--play returns` / `--play freeze`),
  handy as Steam launch options or in a desktop shortcut. If the game can't start yet, a window tells you why
  ([#6](https://github.com/zWalt01/Country-Box/issues/6)).
- RomFS mods (`MP4_ROMFS_MODS`) work again: an overlay that replaces a game file was always refused, because the
  original was hashed from a packed image that these builds don't use. Thanks to cat99sky
  ([#9](https://github.com/zWalt01/Country-Box/pull/9)).
- For developers: the `MP4_TRACE=perf` slow-frame line also shows `drain` and `other` (the frame time not spent
  waiting), so a slow frame's time adds up ([#12](https://github.com/zWalt01/Country-Box/issues/12)).

## 1.0.5 — 2026-11-14

- *Donkey Kong Country Returns HD* now accepts copies of the **physical cartridge**. Until now the launcher only
  recognised the eShop version and called a cartridge copy incompatible, even though it is the same game
  ([#7](https://github.com/zWalt01/Country-Box/issues/7)).
- After updating, each game asks for a quick Prepare (a few seconds on PC; your saves and settings stay).
- A reminder: **save states are still experimental** (F5 saves, F6 loads; Select+Start opens the menu). I haven't
  received any feedback on them yet, so if you try them, please tell me how it went in
  [#3](https://github.com/zWalt01/Country-Box/issues/3) or a new issue — even "it worked fine" helps.

Thank you for playing and for every report so far. Any feedback is appreciated: it's what helps me make Country-Box
better.

## 1.0.4 — 2026-11-13

- **Save states (experimental).** F5 saves, F6 loads; with a controller, Select+Start opens the menu with *Save
  state*, *Load state* and *Load older state*. The last 3 states are kept, so a save made mid-fall can be undone, and
  they only work while the game stays open (closing it deletes them). They have not been deeply tested yet, so I
  can't promise they work in every level or on every machine: a load can be refused after some level changes, the
  sound may skip for a moment, and each state is about 2 GB on disk (under a second on a fast SSD, longer on a
  microSD card). **Feedback is needed to polish them**: if a save or load fails or does something odd, please tell me
  in [#3](https://github.com/zWalt01/Country-Box/issues/3) or a new issue, with the game, the level and what happened.
- Folder picker: the list scrolls (mouse wheel, drag, d-pad), you can paste or type a folder path and press Enter, and
  on the desktop there is a button for your system's own file picker
  ([#1](https://github.com/zWalt01/Country-Box/issues/1)).
- Folders with spaces or other characters in their path (portable mode included) build again
  ([#2](https://github.com/zWalt01/Country-Box/issues/2)).
- About → *Move library…*: choose where the builds and saves live; everything moves there, saves included
  ([#2](https://github.com/zWalt01/Country-Box/issues/2)).
- The AppImage runs on older distributions now (built on Ubuntu 22.04: glibc 2.35 or newer; started on Ubuntu 22.04,
  Debian 12 and Fedora). 1.0.3 did not start on Ubuntu 22.04.
- Prepare no longer needs the `lz4` Python package (it had no ready-made package for Python 3.15, e.g. on current
  Fedora).
- The Prepare screen keeps its text clear of the buttons at any window size.
- After updating, each game asks to be prepared once more (only the game's runtime is rebuilt; saves and settings
  stay).

## 1.0.3 — 2026-11-12

- RecompLauncher's Easy Setup: you pick the folder of either game and the launcher tells which one it is
  (`country-box-launcher --setup auto=FOLDER`). To add the other game, pick its folder too; both stay set up.

## 1.0.2 — 2026-11-12

- RecompLauncher support: the AppImage carries `recomplauncher.json`, so [RecompLauncher](https://recomplauncher.com)
  can set Country-Box up from your copy, build it, show its main settings and start each game.
- New for launchers and scripts: `country-box-launcher --setup dkcrhd=FOLDER dkctf=FOLDER` checks each copy and
  prepares it without a window, printing `progress` lines. Nothing changes if you don't use it.
- The release file is now named `Country-Box-1.0.2-linux-x86_64.AppImage`. Updating from 1.0.1 works as before.

## 1.0.1 — 2026-11-12

- The launcher now updates itself when it runs as an AppImage: it downloads the new AppImage from the release,
  checks its SHA-256, replaces the file you run (the previous one is kept next to it as `.old`) and restarts.
  1.0.0 could not do this, so if you have 1.0.0, download 1.0.1 by hand once.

## 1.0.0 — 2026-11-12

First release: *Donkey Kong Country Returns HD* and *Donkey Kong Country: Tropical Freeze* on Linux and the Steam
Deck, built on your machine from your own copy, with the launcher (add your copy, Prepare, Play, updates, Import a
build). Known issues: [docs/KNOWN-ISSUES.md](docs/KNOWN-ISSUES.md).
