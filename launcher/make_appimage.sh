#!/bin/sh
# Country-Box: arma la AppImage del launcher que se sube a cada release:
#   AppRun, country-box.desktop, country-box.png (.DirIcon)  launcher/appimage/
#   recomplauncher.json                                      la raíz del repo (RecompLauncher la lee en /recomplauncher.json)
#   usr/bin/country-box-launcher                             launcher/build.py, en un contenedor ubuntu:22.04
#   usr/lib/libSDL3.so.0                                     SDL $SDL_TAG compilada en ese contenedor
#                                                            (appimage/container-build.sh; docker o podman)
#   usr/share/country-box/prep/                              launcher/make_prep_payload.py (traductor: core/build/xlate)
#   usr/share/country-box/toolkit/                           el kit de compilación para máquinas sin compilador (SteamOS):
#                                                            appimage/toolkit-build.sh en el mismo contenedor; ~155 MB
#                                                            comprimidos (LLVM 98, Python del lifter 42, sysroot 14)
# Nada derivado de un juego entra (ver make_prep_payload.py).
#
#   sh launcher/make_appimage.sh [OUT_DIR]     (por defecto build/; necesita appimagetool en el PATH o en ~/.local/bin)
#
# Deja en OUT_DIR lo que sube a la release: la AppImage, el tarball del mismo árbol (make_tarball.sh,
# Country-Box-linux-x86_64.tar.gz) y SHA256SUMS con los dos.
#
# El launcher y SDL se arman en ubuntu:22.04 (glibc 2.35) para que la AppImage corra en cualquier distribución
# con esa glibc o más nueva; armados en esta máquina pedirían su glibc (Arch: 2.43) y no arrancarían en Ubuntu,
# Debian, Mint ni SteamOS. Al final se revisa: nada dentro puede pedir más de GLIBC_2.35.
# CB_APPIMAGE_LOCAL=1 arma con el sistema (sólo para pruebas en esta máquina; no sale en una release).
# CB_XLATE_DIR: el traductor (mp4_xlate) de otra carpeta, para make_prep_payload.py --xlate (un worktree sin core/build).
set -eu
umask 022   # la AppImage la corren otros usuarios: appimagetool rechaza carpetas y programas 0700
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-$ROOT/build}
VERSION=$(cat "$ROOT/VERSION")
APPDIR=$OUT/appimage/Country-Box.AppDir
TOOL=$(command -v appimagetool || echo "$HOME/.local/bin/appimagetool")
[ -x "$TOOL" ] || { echo "make_appimage: no encuentro appimagetool" >&2; exit 1; }
python3 -m json.tool "$ROOT/recomplauncher.json" >/dev/null   # un recomplauncher.json roto no sale en una release

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/usr/share/country-box"
SDL_TAG=${SDL_TAG:-release-3.4.18}
if [ "${CB_APPIMAGE_LOCAL:-}" = 1 ]; then
    python3 "$ROOT/launcher/build.py" --out "$OUT/appimage/launcher"
    cp "$OUT/appimage/launcher/country-box-launcher" "$APPDIR/usr/bin/"
    cp -L "$(pkg-config --variable=libdir sdl3)/libSDL3.so.0" "$APPDIR/usr/lib/"
else
    ENGINE=$(command -v docker || command -v podman || true)
    [ -n "$ENGINE" ] || { echo "make_appimage: hace falta docker o podman (o CB_APPIMAGE_LOCAL=1 para una prueba local)" >&2; exit 1; }
    mkdir -p "$OUT/appimage/container"
    "$ENGINE" run --rm -v "$ROOT:/src:ro" -v "$OUT/appimage/container:/out" -e SDL_TAG="$SDL_TAG" \
        -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" ubuntu:22.04 sh /src/launcher/appimage/container-build.sh
    cp "$OUT/appimage/container/country-box-launcher" "$APPDIR/usr/bin/"
    cp "$OUT/appimage/container/libSDL3.so.0" "$APPDIR/usr/lib/"
    # el kit: entradas fijadas por versión y SHA-256, bajadas una vez a CB_TOOLKIT_CACHE (LLVM pesa 1.9 GB)
    CACHE=${CB_TOOLKIT_CACHE:-$OUT/toolkit-cache}
    mkdir -p "$CACHE"
    fetch() {   # nombre url sha256
        if [ ! -f "$CACHE/$1" ]; then
            curl -fsSL -o "$CACHE/$1.part" "$2" || { echo "make_appimage: no pude bajar $2" >&2; exit 1; }
            mv "$CACHE/$1.part" "$CACHE/$1"
        fi
        echo "$3  $CACHE/$1" | sha256sum -c --quiet || { echo "make_appimage: $1 no coincide con su SHA-256" >&2; exit 1; }
    }
    fetch LLVM-23.1.5-Linux-X64.tar.xz \
        https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.5/LLVM-23.1.5-Linux-X64.tar.xz \
        f72edb0b36580ece7f52e23858f00c18fad4e87395ea7ad05d7e55c39f8fc78a
    fetch cpython-3.12.16-20261110.tar.gz \
        https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.12.16%2B20261110-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz \
        6a9e62dad033790aef722dbd370e0ce76ce17b73627ba3ae679f537049350b39
    fetch linux-api-headers-7.3-1-x86_64.pkg.tar.zst \
        https://archive.archlinux.org/packages/l/linux-api-headers/linux-api-headers-7.3-1-x86_64.pkg.tar.zst \
        a5a6f5fc8922ef454c54e65e321906183e6606acaadaf416896dcbc44f2194ed
    # podman sin root: el root del contenedor ya es este usuario (un chown a su uid lo mandaría a un subuid)
    case "$ENGINE" in *podman) KUID=0 KGID=0 ;; *) KUID=$(id -u) KGID=$(id -g) ;; esac
    "$ENGINE" run --rm -v "$ROOT:/src:ro" -v "$CACHE:/cache:ro" -v "$OUT/appimage/container:/out" \
        -e LLVM_TAR=LLVM-23.1.5-Linux-X64.tar.xz -e PY_TAR=cpython-3.12.16-20261110.tar.gz \
        -e KHDR_PKG=linux-api-headers-7.3-1-x86_64.pkg.tar.zst -e VK_TAG=v1.4.363 -e H264_TAG=v2.6.0 \
        -e SDL_TAG="$SDL_TAG" -e HOST_UID="$KUID" -e HOST_GID="$KGID" ubuntu:22.04 sh /src/launcher/appimage/toolkit-build.sh
    cp -a "$OUT/appimage/container/toolkit" "$APPDIR/usr/share/country-box/toolkit"
fi
python3 "$ROOT/launcher/make_prep_payload.py" "$APPDIR/usr/share/country-box/prep" ${CB_XLATE_DIR:+--xlate "$CB_XLATE_DIR"}
# la garantía: ningún programa o biblioteca de la AppImage pide una glibc más nueva que 2.35
if [ "${CB_APPIMAGE_LOCAL:-}" != 1 ]; then
    worst=$(find "$APPDIR" -type f \( -perm -u+x -o -name '*.so*' \) -exec sh -c 'objdump -T "$1" 2>/dev/null' _ {} \; |
            grep -oE 'GLIBC_[0-9]+\.[0-9]+' | sort -Vu | tail -1)
    [ "$(printf '%s\nGLIBC_2.35\n' "$worst" | sort -V | tail -1)" = GLIBC_2.35 ] ||
        { echo "make_appimage: algo dentro pide $worst (el máximo es GLIBC_2.35)" >&2; exit 1; }
    echo "glibc: lo más nuevo que se pide es $worst"
fi
cp "$ROOT/launcher/appimage/AppRun" "$ROOT/launcher/appimage/country-box.desktop" "$ROOT/launcher/appimage/country-box.png" "$APPDIR/"
chmod -R a+rX "$APPDIR"
chmod 755 "$APPDIR/AppRun" "$APPDIR/usr/bin/country-box-launcher"
ln -s country-box.png "$APPDIR/.DirIcon"
cp "$ROOT/recomplauncher.json" "$APPDIR/recomplauncher.json"
chmod 644 "$APPDIR/recomplauncher.json"   # the repo keeps its files 0600; other users must read it

IMG=$OUT/Country-Box-$VERSION-linux-x86_64.AppImage
ARCH=x86_64 "$TOOL" --no-appstream "$APPDIR" "$IMG"
echo "built $IMG"
sh "$ROOT/launcher/make_tarball.sh" "$APPDIR" "$OUT"
# el actualizador verifica con esta lista (update.cpp) cuando el asset no trae digest
(cd "$OUT" && sha256sum "$(basename "$IMG")" Country-Box-linux-x86_64.tar.gz > SHA256SUMS)
echo "built $OUT/SHA256SUMS"
