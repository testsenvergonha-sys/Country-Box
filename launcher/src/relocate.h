// Country-Box launcher: where the launcher keeps everything (the "data folder"), and moving it.
//
// Portable by default (1.0.7): run from the AppImage or from the extracted tarball, everything Country-Box writes —
// the library (builds, the C made from the game, saves, settings, logs), its Python, caches and temporary files —
// lives in ONE folder next to it: <folder holding the .AppImage or the extracted Country-Box/>/Country-Box-data.
// Deleting that folder removes the game completely. AppRun says where the package is (CB_PORTABLE_EXE). A bare
// binary (development, a distribution package) keeps the old place, $XDG_DATA_HOME/country-box or
// ~/.local/share/country-box; so does the AppImage when the folder next to it can't hold programs (read-only, exFAT,
// noexec), and it says why.
//
// That place is the "base": it also records where the player moved the library (<base>/library-location), so later
// runs (and updates) find it there; --home / --data-dir / CB_LAUNCHER_HOME still win over it for one run.
//
// The move is all or nothing: on the same drive every piece is renamed; across drives everything is copied first,
// checked (every file's size, and the bytes of saves and settings), the new place is recorded, and only then the old
// copy is removed. Any failure before that leaves the library where it was and removes what the move had made. A
// player's move leaves the launcher's Python (python/) and its own install (app/) in the base: they are tools.
//
// Saves first (1.0.7): before any move, every game's saves (games/<id>/profile and mp4.ini) are copied to a
// new folder on the player's Desktop ("Country-Box saves backup <date>", with a README) and read back byte for byte;
// if that copy fails, nothing moves. The saves then move with the games, so they are in two places afterwards.
//
// Migration (first start of a portable Country-Box, 1.0.7): when the data folder holds no library yet and the old
// place (~/.local/share/country-box) does, the launcher ASKS once — keep it where it is (recorded, never asked
// again), move it next to Country-Box (the data folder), or move it to a folder the player picks (the tools and the
// record of that place go to the data folder). Nothing moves without that answer; starting a game straight away
// (Steam shortcut) just uses the old place. A library the player had already moved elsewhere stays where it is:
// only its record and the tools come over, without asking. If the move fails, Country-Box keeps the old place.
#pragma once
#include <atomic>
#include <cstdint>
#include <string>

std::string default_launcher_home();   // the base: the data folder when portable, else the legacy place (above)
std::string legacy_launcher_home();    // $XDG_DATA_HOME/country-box, else ~/.local/share/country-box
std::string portable_data_dir();       // <next to the AppImage / extracted folder>/Country-Box-data; "" for a bare binary
std::string base_note();               // why the base is not the data folder ("" when it is, or for a bare binary)
void set_base_home(const std::string &dir);   // this run uses dir as the base (migration pending or failed; done)
std::string library_location_file();   // <base>/library-location
bool launcher_home_fixed();            // --home, --data-dir or CB_LAUNCHER_HOME chose this run's home (can't be moved)

// Portable runs (and --data-dir): the children (Python, clang, the game) and the launcher itself write their temporary files and
// caches inside the base too (TMPDIR=<base>/tmp, XDG_CACHE_HOME=<base>/cache) — nothing in /tmp or ~/.cache.
void contain_temp_files(const std::string &base);

// Where a move to `picked` puts the library: picked itself when it is empty (or does not exist yet) or is the
// default place, else a "Country-Box" folder inside it.
std::string library_target(const std::string &picked);

struct LibraryMove {
    bool everything = false;                  // migration: python/ and app/ move too, the target is taken as is
    std::atomic<int64_t> done{0}, total{0};   // bytes (a copy across drives); total 0 while counting or renaming
    std::atomic<bool> finished{false};
    bool ok = false;
    std::string from, to;                     // to: the library's new folder
    std::string headline, explain;            // why it failed
    bool backup_saves = true;                 // copy the saves to the Desktop before anything moves (above)
    bool no_record = false;                   // the caller records the new place itself (a migration)
    std::string backup;                       // where that copy went; "" when there were no saves to copy
};

// The player's Desktop (XDG_DESKTOP_DIR in user-dirs.dirs, else ~/Desktop, else the home). CB_DESKTOP_DIR overrides.
std::string desktop_dir();
// Copies the saves of every game in `library` (games/<id>/profile, games/<id>/mp4.ini) into a new folder on the
// Desktop and reads it back byte for byte. true with dir "" when there is nothing to copy; false with err on failure.
bool backup_saves(const std::string &library, const std::string &moving_to, std::string &dir, std::string &err);

// Moves the library from `from` to library_target(picked). Run it on a thread; read the fields once finished is true.
void move_library(const std::string &from, const std::string &picked, LibraryMove &m);

// The first-run migration (above). needed: the data folder has no library and the old place has one, and the player
// has not chosen to keep it there (stay). same_drive: the data folder is on the old place's drive. busy: a game runs
// from the old place right now (try again next start).
struct Migration {
    bool needed = false, same_drive = false, busy = false;
    bool stay = false;       // the player chose "keep it where it is": the old place stays the base, not asked again
    std::string from;        // the old base (~/.local/share/country-box)
    std::string to;          // the data folder
    std::string library;     // where the library is now: from, or the folder the player moved it to
    bool ask() const { return needed && !busy && library == from; }   // the player decides; else it just happens
};
Migration plan_migration();
// "Keep it where it is": recorded in the old place (<from>/library-choice), so later starts don't ask again.
bool keep_library_here(const Migration &plan, std::string &err);
// Runs it (blocking; run on a thread for progress). picked: "" = the data folder, else the folder the player chose
// (library_target rules). On success the base is the data folder (set_base_home), recording where the library is.
void migrate_library(const Migration &plan, const std::string &picked, LibraryMove &m);
