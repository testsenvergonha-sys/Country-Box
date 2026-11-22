#!/usr/bin/env python3
# Country-Box: the portable data folder and the first-start question of 1.0.7 (relocate.h: keep the library where it
# is, move it next to Country-Box, or to a folder the player picks; the saves are copied to the Desktop first), on
# scratch HOMEs — never the real one. The launcher runs through the real AppRun in a fake package folder, as the tarball does (and as the AppImage
# does, with $APPIMAGE/$APPDIR set like its runtime sets them). No game needed: the libraries are stand-ins with a
# build, saves, settings, the C made from the game, logs and the launcher's Python.
#
#   python3 launcher/tests/portable_test.py LAUNCHER [OTHER_DRIVE_DIR]
#
# OTHER_DRIVE_DIR: a writable folder on another filesystem than /tmp (migration by copy); skipped without it.
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ODD = "Mis Juegos (ñ) $HOME"
failures = 0


def check(cond, what):
    global failures
    print(('ok    ' if cond else 'FAIL  ') + what)
    failures += not cond


def package(where, exe):
    """An extracted Country-Box folder: AppRun (the real one) + usr/bin/country-box-launcher + the country-box link."""
    d = where / 'Country-Box'
    (d / 'usr' / 'bin').mkdir(parents=True)
    shutil.copy(ROOT / 'launcher' / 'appimage' / 'AppRun', d / 'AppRun')
    (d / 'AppRun').chmod(0o755)
    os.symlink(exe, d / 'usr' / 'bin' / 'country-box-launcher')
    os.symlink('AppRun', d / 'country-box')
    return d


def env_for(home, **extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ('XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'CB_LAUNCHER_HOME', 'CB_DESKTOP_DIR', 'APPIMAGE', 'APPDIR', 'TMPDIR')}
    env.update(HOME=str(home), CB_LAUNCHER_NO_UPDATE='1', SDL_VIDEO_DRIVER='dummy')
    env.update(extra)
    return env


def run(cmd, env, *args, cwd=None):
    p = subprocess.run([str(cmd), *args], env=env, capture_output=True, text=True, timeout=600, cwd=cwd)
    return p.returncode, p.stdout, p.stderr


def status(cmd, env, *args):
    rc, out, err = run(cmd, env, *args, '--status')
    try:
        return rc, json.loads(out), err
    except ValueError:
        return rc, {}, err + out


def fake_library(home, with_python=True):
    b = home / 'games' / 'dkctf'
    (b / 'profile' / 'save').mkdir(parents=True)
    (b / 'profile' / 'save' / 'slot0.bin').write_bytes(b'save data \x00\x01')
    (b / 'mp4.ini').write_text('fullscreen = 1\n')
    exe = b / 'country-box'
    exe.write_bytes(b'\x7fELF' + b'\0' * 4096)
    exe.chmod(0o755)
    (home / 'gen' / 'dkctf').mkdir(parents=True)
    (home / 'gen' / 'dkctf' / 'dkctf_0000.c').write_text('int x;\n')
    (home / 'logs').mkdir(exist_ok=True)
    (home / 'logs' / 'prepare.log').write_text('log\n')
    if with_python:
        (home / 'python' / 'bin').mkdir(parents=True)
        (home / 'python' / 'pyvenv.cfg').write_text('home = /usr/bin\n')
    (home / 'update.ini').write_text('declined = 1.0.6\n')
    (home / 'library.ini').write_text(f'[dkctf]\nbuild = {home}/games/dkctf\n')


def library_ok(lib, what, python=True):
    b = lib / 'games' / 'dkctf'
    check((b / 'profile' / 'save' / 'slot0.bin').read_bytes() == b'save data \x00\x01'
          and (b / 'mp4.ini').read_text() == 'fullscreen = 1\n', f'{what}: saves and settings are there, byte for byte')
    check(os.access(b / 'country-box', os.X_OK), f'{what}: the game binary is still runnable')
    check((lib / 'gen' / 'dkctf' / 'dkctf_0000.c').is_file() and (lib / 'logs' / 'prepare.log').is_file(),
          f'{what}: the C and the logs are there')
    check(f'build = {lib}/games/dkctf' in (lib / 'library.ini').read_text(), f'{what}: library.ini build= follows')
    if python:
        check((lib / 'python' / 'pyvenv.cfg').is_file() and (lib / 'update.ini').is_file(),
              f'{what}: the launcher\'s Python and update choice came along')


def backup_ok(desktop, what, game_name='Donkey Kong Country: Tropical Freeze'):
    """The copy of the saves on the Desktop: one backup folder with the README, the save and the settings, byte for byte."""
    found = sorted(desktop.glob('Country-Box saves backup *')) if desktop.is_dir() else []
    ok = len(found) == 1
    if ok:
        b = found[0]
        games = [d for d in b.iterdir() if d.is_dir()]
        g = games[0] if len(games) == 1 else b / game_name
        ok = ((g / 'profile' / 'save' / 'slot0.bin').read_bytes() == b'save data \x00\x01'
              and (g / 'mp4.ini').read_text() == 'fullscreen = 1\n' and 'copy of your saves' in (b / 'README.txt').read_text())
    check(ok, f'{what}: a copy of the saves is on the Desktop ({found[0].name if found else "none"})')
    return found[0] if found else None


def leftovers(home):
    """Anything Country-Box left in the player's home outside the data folder."""
    found = []
    for sub in ('.local/share/country-box', '.cache/country-box', '.config/country-box', '.cache/mesa_shader_cache'):
        if (home / sub).exists():
            found.append(sub)
    return found


def main():
    exe = Path(sys.argv[1]).resolve()
    other = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    tmp = Path(tempfile.mkdtemp(prefix='cb-portable-test-'))
    try:
        # 1. a new player: the data folder next to the package, nothing in the home
        case = tmp / 'fresh'
        home = case / 'home'
        home.mkdir(parents=True)
        games = case / ODD
        games.mkdir()
        pkg = package(games, exe)
        rc, st, err = status(pkg / 'country-box', env_for(home))
        data = games / 'Country-Box-data'
        check(rc == 0 and st.get('home') == str(data) and st.get('portable') is True,
              f'tarball: the library is Country-Box-data next to the extracted folder ({err.strip() or "ok"})')
        check((data / 'tmp').is_dir() and (data / 'cache').is_dir(), 'temporary files and caches go inside it')
        check(not leftovers(home) and not (home / '.local').exists(), 'nothing is written in the home')
        rc, out, _ = run(pkg / 'country-box', env_for(home), '--add', str(case / 'no copy here'))
        shutil.rmtree(data)
        check(not any(case.rglob('*country-box*.ini')) and not leftovers(home),
              'deleting Country-Box-data removes everything Country-Box wrote')

        # 2. the AppImage: $APPIMAGE (set by its runtime, with $APPDIR = the mount) names the file
        img = games / 'Country-Box-1.0.7-linux-x86_64.AppImage'
        img.write_bytes(b'stand-in')
        rc, st, _ = status(pkg / 'AppRun', env_for(home, APPIMAGE=str(img), APPDIR=str(pkg)))
        check(st.get('home') == str(data), 'AppImage: the library is Country-Box-data next to the .AppImage')
        other_ai = case / 'elsewhere' / 'RecompLauncher.AppImage'
        other_ai.parent.mkdir()
        rc, st, _ = status(pkg / 'AppRun', env_for(home, APPIMAGE=str(other_ai), APPDIR='/tmp/.mount_other'))
        check(st.get('home') == str(data), 'an $APPIMAGE inherited from another AppImage is ignored')
        shutil.rmtree(data)

        # 3. --data-dir / --home / CB_LAUNCHER_HOME: one folder the player names, temporary files inside it too
        mine = case / 'my data'
        rc, st, _ = status(pkg / 'country-box', env_for(home), '--data-dir', str(mine))
        check(st.get('home') == str(mine) and (mine / 'tmp').is_dir() and not data.exists(),
              '--data-dir DIR keeps everything in DIR')
        rc, st, _ = status(pkg / 'country-box', env_for(home, CB_LAUNCHER_HOME=str(mine)))
        check(st.get('home') == str(mine), 'CB_LAUNCHER_HOME still works')

        # 4. same drive, XDG_DATA_HOME unset and set: nothing moves until the player answers; "here" moves it, with
        #    the saves copied to the Desktop first (XDG_DESKTOP_DIR from user-dirs.dirs in one, ~/Desktop in the other)
        for xdg in (False, True):
            label = 'XDG_DATA_HOME set' if xdg else 'XDG_DATA_HOME unset'
            case = tmp / ('mig-xdg' if xdg else 'mig')
            home = case / f'home {ODD}'
            extra = {}
            if xdg:
                extra['XDG_DATA_HOME'] = str(case / 'xdg data')
                legacy = case / 'xdg data' / 'country-box'
                desktop = home / 'Escritorio'
                (home / '.config').mkdir(parents=True)
                (home / '.config' / 'user-dirs.dirs').write_text('XDG_DESKTOP_DIR="$HOME/Escritorio"\n')
            else:
                legacy = home / '.local' / 'share' / 'country-box'
                desktop = home / 'Desktop'
            desktop.mkdir(parents=True)
            fake_library(legacy)
            games = case / 'Games'
            games.mkdir(parents=True)
            pkg = package(games, exe)
            data = games / 'Country-Box-data'
            rc, st, err = status(pkg / 'country-box', env_for(home, **extra))
            check(rc == 0 and st.get('home') == str(legacy) and 'choose where it goes' in err and not (data / 'games').exists(),
                  f'{label}: nothing moves on its own; the old place is used and it says to choose')
            library_ok(legacy, f'{label}, before answering')
            rc, st, err = status(pkg / 'country-box', env_for(home, **extra), '--library-choice', 'here')
            check(rc == 0 and st.get('home') == str(data) and 'moved from' in err and 'Desktop' in err,
                  f'{label}: "next to Country-Box" moves it into the data folder ({err.strip().splitlines()[-1] if err.strip() else ""})')
            library_ok(data, f'{label}, same drive')
            backup_ok(desktop, label)
            check(not legacy.exists(), f'{label}: the old folder is gone')
            check(not leftovers(home), f'{label}: nothing of Country-Box is left in the home')
            rc, st, err = status(pkg / 'country-box', env_for(home, **extra))
            check(st.get('home') == str(data) and 'moved' not in err and 'choose' not in err, f'{label}: the next run just uses it')

        # 4b. "keep it where it is": nothing moves, no copy is made, and it is not asked again
        case = tmp / 'keep'
        home = case / 'home'
        legacy = home / '.local' / 'share' / 'country-box'
        fake_library(legacy)
        (home / 'Desktop').mkdir()
        games = case / 'Games'
        games.mkdir(parents=True)
        pkg = package(games, exe)
        data = games / 'Country-Box-data'
        rc, st, err = status(pkg / 'country-box', env_for(home), '--library-choice', 'keep')
        check(rc == 0 and st.get('home') == str(legacy) and 'stays in' in err, 'keep: the library stays where it is')
        rc, st, err = status(pkg / 'country-box', env_for(home))
        check(st.get('home') == str(legacy) and 'choose' not in err and not (data / 'games').exists(), 'keep: later starts don\'t ask again')
        library_ok(legacy, 'kept')
        check(not any((home / 'Desktop').iterdir()), 'keep: no copy is made when nothing moves')

        # 4c. a folder the player picks: the library goes there, the tools and its record go to the data folder
        case = tmp / 'pick'
        home = case / 'home'
        legacy = home / '.local' / 'share' / 'country-box'
        fake_library(legacy)
        desktop = case / 'desk'
        desktop.mkdir(parents=True)
        games = case / 'Games'
        games.mkdir(parents=True)
        pkg = package(games, exe)
        data = games / 'Country-Box-data'
        mine = case / f'Mis juegos {ODD}'
        mine.mkdir()
        (mine / 'other game.txt').write_text('not ours')
        rc, st, err = status(pkg / 'country-box', env_for(home, CB_DESKTOP_DIR=str(desktop)), '--library-choice', str(mine))
        lib = mine / 'Country-Box'
        check(rc == 0 and st.get('home') == str(lib), 'a picked folder with files: the library goes into its Country-Box folder')
        library_ok(lib, 'picked folder', python=False)
        check((data / 'library-location').read_text().strip() == str(lib) and (data / 'python' / 'pyvenv.cfg').is_file(),
              'picked folder: the data folder records it and keeps the tools')
        check((mine / 'other game.txt').read_text() == 'not ours' and not legacy.exists(), 'picked folder: its files untouched, the old place gone')
        backup_ok(desktop, 'picked folder')
        rc, st, _ = status(pkg / 'country-box', env_for(home))
        check(st.get('home') == str(lib), 'picked folder: the next start finds it')

        # 4d. the copy to the Desktop fails (read-only Desktop): nothing moves
        case = tmp / 'nodesk'
        home = case / 'home'
        legacy = home / '.local' / 'share' / 'country-box'
        fake_library(legacy)
        desktop = case / 'desk'
        desktop.mkdir(parents=True)
        desktop.chmod(0o555)
        games = case / 'Games'
        games.mkdir(parents=True)
        pkg = package(games, exe)
        data = games / 'Country-Box-data'
        try:
            rc, st, err = status(pkg / 'country-box', env_for(home, CB_DESKTOP_DIR=str(desktop)), '--library-choice', 'here')
            check(st.get('home') == str(legacy) and 'could not be copied to the Desktop' in err and not (data / 'games').exists(),
                  'the saves can\'t be copied to the Desktop: nothing moves, it says why')
            library_ok(legacy, 'Desktop not writable, nothing moved')
        finally:
            desktop.chmod(0o755)

        # 5. a library the player had moved elsewhere stays there; its record and the tools come over
        case = tmp / 'mig-moved'
        home = case / 'home'
        legacy = home / '.local' / 'share' / 'country-box'
        far = case / 'big drive' / 'Country-Box'
        fake_library(far, with_python=False)
        (legacy / 'python' / 'bin').mkdir(parents=True)
        (legacy / 'library-location').write_text(f'{far}\n')
        games = case / 'Games'
        games.mkdir()
        pkg = package(games, exe)
        data = games / 'Country-Box-data'
        rc, st, err = status(pkg / 'country-box', env_for(home))
        check(st.get('home') == str(far) and (data / 'library-location').read_text().strip() == str(far),
              'a moved library stays where the player put it; the data folder records it')
        check((data / 'python' / 'bin').is_dir() and not legacy.exists(), 'its tools came over, the old folder is gone')
        library_ok(far, 'moved library, untouched', python=False)

        # 6. the data folder can't be used (read-only folder): the old place stays, and it says why
        case = tmp / 'readonly'
        home = case / 'home'
        legacy = home / '.local' / 'share' / 'country-box'
        fake_library(legacy)
        games = case / 'Games'
        games.mkdir(parents=True)
        pkg = package(games, exe)
        games.chmod(0o555)
        try:
            rc, st, err = status(pkg / 'country-box', env_for(home))
            check(st.get('home') == str(legacy) and 'can\'t be used' in st.get('note', '') and 'written' in err,
                  f'a read-only folder: the old place stays, saying why ({st.get("note", "")[:60]}…)')
            library_ok(legacy, 'read-only folder, nothing moved')
        finally:
            games.chmod(0o755)

        # 7. a game running from the old place: nothing moves this time, even when the player answers; it says so
        case = tmp / 'busy'
        home = case / 'home'
        legacy = home / '.local' / 'share' / 'country-box'
        fake_library(legacy)
        games = case / 'Games'
        games.mkdir(parents=True)
        pkg = package(games, exe)
        data = games / 'Country-Box-data'
        game = subprocess.Popen(['sleep', '60'], cwd=legacy / 'games' / 'dkctf')
        try:
            rc, st, err = status(pkg / 'country-box', env_for(home), '--library-choice', 'here')
            check(st.get('home') == str(legacy) and 'a game is running from there' in err and not (data / 'games').exists(),
                  'a game running from the old place: the library stays this time')
        finally:
            game.kill()
            game.wait()
        rc, st, _ = status(pkg / 'country-box', env_for(home), '--library-choice', 'here')
        check(st.get('home') == str(data), 'after the game closed, the answer moves it')
        library_ok(data, 'after the game closed')

        # 8. both places hold a library: the data folder wins, the old one is never touched
        case = tmp / 'both'
        home = case / 'home'
        legacy = home / '.local' / 'share' / 'country-box'
        fake_library(legacy)
        games = case / 'Games'
        games.mkdir(parents=True)
        pkg = package(games, exe)
        data = games / 'Country-Box-data'
        (data / 'games').mkdir(parents=True)
        rc, st, _ = status(pkg / 'country-box', env_for(home))
        check(st.get('home') == str(data), 'a data folder with a library is used as it is')
        library_ok(legacy, 'the old library next to it, untouched')

        # 9. a bare binary (development, a distribution package) keeps ~/.local/share/country-box
        rc, st, _ = status(exe, env_for(home))
        check(st.get('home') == str(legacy) and st.get('portable') is False and st.get('data_folder') == '',
              'a bare binary keeps the old place and moves nothing')

        # 10. another drive: starting a game never waits (nothing moves); the answer copies it, reads it back, then the
        #     old one goes; in the window the question comes first and the copy runs on its progress screen
        if other:
            case = tmp / 'far'
            home = case / 'home'
            legacy = home / '.local' / 'share' / 'country-box'
            fake_library(legacy)
            (home / 'Desktop').mkdir()
            games = other / f'cb-portable-test {ODD}'
            shutil.rmtree(games, ignore_errors=True)
            games.mkdir(parents=True)
            try:
                pkg = package(games, exe)
                data = games / 'Country-Box-data'
                rc, _, err = run(pkg / 'country-box', env_for(home), '--skip', '--auto', 'frames:2;quit')
                check('choose where it goes' in err and legacy.is_dir() and not (data / 'games').exists(),
                      'another drive: starting a game moves nothing and does not wait')
                rc, st, err = status(pkg / 'country-box', env_for(home), '--library-choice', 'here')
                check(st.get('home') == str(data) and 'moved from' in err, 'another drive: the library is copied over')
                library_ok(data, 'another drive')
                backup_ok(home / 'Desktop', 'another drive')
                check(not legacy.exists(), 'another drive: the old folder goes only after the copy checked out')
                # the launcher window: the question, "Ask me later" (nothing recorded), then "next to Country-Box"
                home2 = case / 'home2'
                legacy2 = home2 / '.local' / 'share' / 'country-box'
                fake_library(legacy2)
                (home2 / 'Desktop').mkdir()
                shutil.rmtree(data)
                shots = case / 'shots'
                shots.mkdir()
                rc, out, err = run(pkg / 'country-box', env_for(home2), '--shot-dir', str(shots), '--auto', 'frames:4;shot:choose;choose:later;frames:3;quit')
                rc2, st, _ = status(pkg / 'country-box', env_for(home2))
                check(rc == 0 and (shots / 'choose.png').is_file() and st.get('home') == str(legacy2) and not (legacy2 / 'library-choice').exists(),
                      'the window asks; "Ask me later" moves nothing and records nothing')
                rc, out, err = run(pkg / 'country-box', env_for(home2), '--shot-dir', str(shots),
                                   '--auto', 'frames:3;choose:here;wait-move;frames:3;shot:moved;key:a;frames:3;quit')
                rc2, st, _ = status(pkg / 'country-box', env_for(home2))
                check(rc == 0 and st.get('home') == str(data) and not legacy2.exists(),
                      'another drive, the launcher window: "next to Country-Box" runs on its progress screen')
                library_ok(data, 'another drive, from the window')
                backup_ok(home2 / 'Desktop', 'from the window')
                print(f'      screenshots: {shots}/choose.png, {shots}/moved.png')
                if os.environ.get('CB_KEEP_SHOTS'):
                    shutil.copytree(shots, os.environ['CB_KEEP_SHOTS'], dirs_exist_ok=True)
            finally:
                shutil.rmtree(games, ignore_errors=True)
    finally:
        for p in tmp.rglob('*'):
            if p.is_dir() and not p.is_symlink():
                p.chmod(0o755)
        shutil.rmtree(tmp, ignore_errors=True)
    print('portable test:', 'passed' if not failures else f'{failures} failed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
