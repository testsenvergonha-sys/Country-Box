#!/usr/bin/env python3
# Country-Box: test of starting a game straight from the command line (country-box-launcher --play GAME, --returns,
# --freeze: Steam launch options and shortcuts). The game is a stand-in script that writes the arguments it got and
# exits with a known code, so nothing real starts and no window opens. Uses a scratch library; the real copy is only
# read (--add checks it).
#
#   python3 launcher/tests/play_test.py build/launcher/country-box-launcher RETURNS_COPY
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

fails = 0


def check(ok, what):
    global fails
    print(('ok    ' if ok else 'FAIL  ') + what)
    fails += not ok


def run(exe, home, *args, path=None):
    # stderr is a pipe here (no terminal): the "can't start" window would come up, so the test asks for none
    env = dict(os.environ, CB_LAUNCHER_HOME=str(home), CB_SETTINGS_FILE=str(home / 'settings.ini'),
               CB_LAUNCHER_NO_UPDATE='1', SDL_VIDEO_DRIVER='dummy')
    if path is not None:   # a machine without compilers (Steam Deck): nothing of the toolchain on PATH
        env['PATH'] = path
        env.pop('CB_PYTHON', None)
    p = subprocess.run([exe, *args], env=env, capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout, p.stderr


def fake_build(d, dump='{}'):
    d.mkdir(parents=True)
    exe = d / 'country-box'
    exe.write_text('#!/bin/sh\n[ "$1" = --settings-dump ] && { echo \'' + dump + '\'; exit 0; }\n'
                   'printf "%s\\n" "$@" > "$(dirname "$0")/args.txt"\nexit 7\n')
    exe.chmod(0o755)
    return d


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__ or 'usage: play_test.py LAUNCHER RETURNS_COPY')
    exe, rcopy = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    tmp = Path(tempfile.mkdtemp(prefix='cb-play-'))
    home = tmp / 'home'
    try:
        home.mkdir()
        code, _, err = run(exe, home, '--play', 'returns')
        check(code == 1 and "can't start yet" in err, 'without a copy, --play says why and fails')
        code, _, err = run(exe, home, '--play', 'mario')
        check(code == 2 and 'Use --play returns or --play freeze' in err, 'an unknown game names the right ones')
        code, out, _ = run(exe, home, '--add', 'returns', str(rcopy))
        check(code == 0 and json.loads(out)['ok'], '--add takes the short name too')
        code, _, err = run(exe, home, '--returns')
        check(code == 1 and 'still has to be built' in err, 'a copy without a build: --returns says it needs preparing')
        b = fake_build(tmp / 'build')
        code, _, _ = run(exe, home, '--set-build', 'dkcrhd', str(b))
        check(code == 0, 'a stand-in build is set')
        for args in (['--play', 'dkcrhd'], ['--play', 'returns'], ['--play', 'returns-hd'], ['--returns']):
            (b / 'args.txt').unlink(missing_ok=True)
            code, _, _ = run(exe, home, *args)
            got = (b / 'args.txt').read_text().split('\n') if (b / 'args.txt').exists() else []
            check(code == 7 and got[:2] == ['--exefs', str(rcopy / 'exefs')] and '--romfs' in got,
                  f'{" ".join(args)} starts Returns HD with the copy and hands back its exit code')
        code, _, err = run(exe, home, '--freeze')
        check(code == 1 and 'Tropical Freeze' in err, '--freeze is Tropical Freeze (not set up here: says so)')
        # a build from an older Country-Box (the Steam Deck case of 2026-11-14): it keeps playing, and a Prepare on a
        # machine without compilers keeps it instead of failing
        old = fake_build(tmp / 'old', '{"version": "1.0.1", "game": "dkcr-hd", "groups": []}')
        run(exe, home, '--set-build', 'dkcrhd', str(old))
        code, out, _ = run(exe, home, '--status')
        g = {x['id']: x for x in json.loads(out)['games']}['dkcrhd']
        check(g['state'] == 'update_available' and 'Plays as before' in g['detail'],
              'an older build reads as an update, and says it still plays')
        code, _, _ = run(exe, home, '--returns')
        check(code == 7 and (old / 'args.txt').exists(), 'the older build still starts')
        nobin = tmp / 'nobin'
        nobin.mkdir()
        code, _, err = run(exe, home, '--setup', f'dkcrhd={rcopy}', path=str(nobin))
        check(code == 0 and 'Playing the build already here' in err,
              '--setup without compilers keeps the build it has instead of failing')
    finally:
        shutil.rmtree(tmp)
    print('play test:', 'passed' if not fails else f'{fails} FAILED')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
