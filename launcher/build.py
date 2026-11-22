#!/usr/bin/env python3
# Country-Box: builds the launcher, country-box-launcher (launcher/src, SDL 3 + SDL_Renderer + Dear ImGui, the same
# Dear ImGui as the game runtime: core/runtime/third_party/imgui). Nothing from a game goes in, so the output may live
# in the repository's ignored build/ folder.
#
#   python3 launcher/build.py [--out DIR] [--jobs N] [--toolchain DIR] [--deps DIR] [--ninja EXE]
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
IMGUI = ROOT / 'core' / 'runtime' / 'third_party' / 'imgui'
BACKENDS = HERE / 'third_party' / 'imgui_backends'
WARN = ['-Wall', '-Wno-c23-extensions']
COMMON = ['-O2', '-g', '-fno-strict-aliasing', '-D_GNU_SOURCE', f'-ffile-prefix-map={HERE.parent}=.']


def pkg(flag):
    r = subprocess.run(['pkg-config', flag, 'sdl3'], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'pkg-config {flag} sdl3: {r.stderr.strip()}')
    return r.stdout.split()


def main():
    ap = argparse.ArgumentParser(description='Build country-box-launcher.')
    ap.add_argument('--out', type=Path, default=ROOT / 'build' / 'launcher')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--toolchain', type=Path, default=None)
    ap.add_argument('--deps', type=Path, default=None)
    ap.add_argument('--ninja', type=Path, default=None)
    a = ap.parse_args()

    is_win = sys.platform == 'win32' or os.name == 'nt'

    clang = 'clang'
    clangxx = 'clang++'
    ninja = 'ninja'

    if a.toolchain:
        tc = a.toolchain.resolve()
        clang = str(tc / 'bin' / ('clang.exe' if is_win else 'clang'))
        clangxx = str(tc / 'bin' / ('clang++.exe' if is_win else 'clang++'))
    elif is_win:
        default_tc = ROOT / 'toolchain' / 'llvm'
        if default_tc.is_dir():
            clang = str(default_tc / 'bin' / 'clang.exe')
            clangxx = str(default_tc / 'bin' / 'clang++.exe')

    if a.ninja:
        ninja = str(a.ninja.resolve())
    elif is_win:
        default_ninja = ROOT / 'toolchain' / 'deps-mingw' / 'bin' / 'ninja.exe'
        if default_ninja.is_file():
            ninja = str(default_ninja)

    deps = a.deps.resolve() if a.deps else (ROOT / 'toolchain' / 'deps-mingw' if is_win else None)

    if not is_win:
        for tool in ('clang', 'clang++', 'ninja', 'pkg-config'):
            if not shutil.which(tool):
                sys.exit(f'missing: {tool}')

    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    version = (ROOT / 'VERSION').read_text().strip()

    if is_win:
        compat_dir = ROOT / 'core' / 'runtime' / 'platform' / 'compat'
        inc = ['-I', str(HERE / 'src'), '-I', str(IMGUI), '-I', str(BACKENDS), '-I', str(compat_dir)]
        if deps and (deps / 'include').is_dir():
            inc += ['-I', str(deps / 'include')]
        defs = [f'-DCB_VERSION=\\"{version}\\"', '-D_WIN32_WINNT=0x0A00']
        libs = ['-static-libgcc', '-static-libstdc++']
        if deps and (deps / 'lib').is_dir():
            libs += ['-L' + str(deps / 'lib')]
        libs += ['-lSDL3', '-lkernel32', '-luser32', '-lshell32', '-lgdi32', '-lole32', '-luuid', '-lversion']
    else:
        inc = ['-I', str(HERE / 'src'), '-I', str(IMGUI), '-I', str(BACKENDS)] + pkg('--cflags')
        defs = [f'-DCB_VERSION=\\"{version}\\"']
        libs = pkg('--libs') + ['-ldl', '-lpthread']

    srcs = sorted(HERE.glob('src/*.c')) + sorted(HERE.glob('src/*.cpp')) + sorted(BACKENDS.glob('*.cpp')) + \
        [IMGUI / n for n in ('imgui.cpp', 'imgui_draw.cpp', 'imgui_tables.cpp', 'imgui_widgets.cpp')]
    q = lambda p: str(p).replace('\\', '/').replace('$', '$$').replace(' ', '$ ').replace(':', '$:')
    
    # Country-Box: no backslash inside an f-string expression: Python < 3.12 (the release container, Ubuntu 22.04's
    # 3.10) refuses it; Windows paths are written with forward slashes for Ninja
    fwd = lambda x: str(x).replace('\\', '/')
    inc_fwd, libs_fwd = [fwd(x) for x in inc], [fwd(x) for x in libs]
    clang_q = str(clang).replace('\\', '/')
    clangxx_q = str(clangxx).replace('\\', '/')

    lines = [
        '# Written by launcher/build.py; do not edit.',
        f'cflags = {" ".join(["-std=gnu17"] + COMMON + WARN + inc_fwd + defs)}',
        f'cxxflags = {" ".join(["-std=c++20"] + COMMON + WARN + inc_fwd + defs)}',
        f'libs = {" ".join(libs_fwd)}',
        'rule cc', f'  command = {clang_q} $cflags -MD -MF $out.d -c $in -o $out', '  deps = gcc', '  depfile = $out.d',
        '  description = CC $in',
        'rule cxx', f'  command = {clangxx_q} $cxxflags -MD -MF $out.d -c $in -o $out', '  deps = gcc', '  depfile = $out.d',
        '  description = CXX $in',
        'rule link', f'  command = {clangxx_q} -fuse-ld=lld $in $libs -o $out', '  description = LINK $out',
    ]
    objs = []
    for s in srcs:
        o = out / 'obj' / (s.parent.name + '_' + s.stem + '.o')
        lines.append(f'build {q(o)}: {"cc" if s.suffix == ".c" else "cxx"} {q(s)}')
        objs.append(o)
    exe_name = 'country-box-launcher.exe' if is_win else 'country-box-launcher'
    exe = out / exe_name
    lines += [f'build {q(exe)}: link ' + ' '.join(q(o) for o in objs), f'default {q(exe)}', '']
    text = '\n'.join(lines)
    nf = out / 'build.ninja'
    if not nf.is_file() or nf.read_text() != text:
        nf.write_text(text)

    cmd = [ninja, '-C', str(out), '-j', str(a.jobs)]
    if not is_win and shutil.which('nice'):
        cmd = ['nice', '-n', '19'] + cmd
    r = subprocess.run(cmd)
    if r.returncode:
        sys.exit(r.returncode)
    print(f'built {exe}')


if __name__ == '__main__':
    main()
