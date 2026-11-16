#!/bin/sh
# Country-Box: corre DENTRO de un contenedor ubuntu:22.04 (glibc 2.35) que lanza launcher/make_appimage.sh.
# Arma el kit de compilación que viaja dentro de la AppImage (usr/share/country-box/toolkit/) para las máquinas sin
# compilador (SteamOS): Prepare lo usa directo desde la AppImage montada, sin instalar ni copiar nada.
#
#   llvm/      clang y lld oficiales de LLVM (sin símbolos) + los headers propios de clang
#   sysroot/   headers y bibliotecas de enlace de Ubuntu 22.04: glibc, libstdc++ 12, Vulkan (headers de Khronos
#              $VK_TAG), Opus y vpx (estáticas: el soname de libvpx cambia entre distribuciones), zlib, SDL 3
#   python/    CPython autónomo (python-build-standalone) con capstone, numpy y unicorn (lo que importa el lifter)
#   bin/       ninja de Ubuntu y los envoltorios clang, clang++, ld.lld y pkg-config (launcher/appimage/toolkit/)
#   lib/       libSDL3.so.0 (la de la AppImage): Prepare la deja junto al juego, que la busca con rpath $ORIGIN
#
# El juego enlazado contra este sysroot pide como mucho GLIBC_2.35, igual que la AppImage.
#
#   /src = el repo (sólo lectura)   /cache = LLVM y CPython ya bajados   /out = salida
#   LLVM_TAR, PY_TAR, KHDR_PKG = nombres de los archivos en /cache   VK_TAG, H264_TAG, SDL_TAG   HOST_UID/HOST_GID = dueño de /out
set -eu
export DEBIAN_FRONTEND=noninteractive
K=/out/toolkit
rm -rf "$K"
mkdir -p "$K/bin" "$K/lib" "$K/llvm/bin" "$K/sysroot"
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    libc6-dev linux-libc-dev libgcc-12-dev libstdc++-12-dev libvulkan-dev libopus-dev libvpx-dev zlib1g-dev \
    ninja-build xz-utils zstd ca-certificates git cmake binutils python3 >/dev/null

# clang + lld: sólo los dos programas y los headers de clang (el tar trae 1.9 GB)
tar -xJf "/cache/$LLVM_TAR" -C /tmp --wildcards '*/bin/clang-[0-9]*' '*/bin/lld' '*/lib/clang/*/include'
L=$(ls -d /tmp/LLVM-*)
CLANG=$(ls "$L"/bin/clang-[0-9]*)
strip -o "$K/llvm/bin/clang" "$CLANG"
strip -o "$K/llvm/bin/lld" "$L/bin/lld"
ln -s lld "$K/llvm/bin/ld.lld"
ln -s clang "$K/llvm/bin/clang++"
mkdir -p "$K/llvm/lib/clang"
cp -a "$L"/lib/clang/* "$K/llvm/lib/clang/"
ln -s "$(basename "$(ls -d "$K"/llvm/lib/clang/*)")" "$K/llvm/lib/clang/current"

# sysroot: los archivos de los paquetes de desarrollo (dpkg -L), sin docs; los symlinks absolutos se vuelven relativos
for p in libc6 libc6-dev linux-libc-dev libgcc-12-dev libgcc-s1 libstdc++-12-dev libstdc++6 \
         libvulkan-dev libvulkan1 libopus-dev libvpx-dev zlib1g-dev zlib1g; do
    dpkg -L "$p" | while read -r f; do
        case "$f" in /usr/share/*|/etc/*|/usr/bin/*|/usr/sbin/*|/sbin/*|/bin/*) continue ;; esac
        [ -d "$f" ] && continue
        [ -f "$f" ] || [ -L "$f" ] || continue
        d=$(readlink -f "$(dirname "$f")")   # usrmerge: /lib/... is /usr/lib/...
        mkdir -p "$K/sysroot$d"
        cp -a "$f" "$K/sysroot$d/"
    done
done
# Ubuntu 22.04 fusiona /lib en /usr/lib: la ruta /lib de los linker scripts (libc.so) tiene que existir
[ -e "$K/sysroot/lib" ] || ln -s usr/lib "$K/sysroot/lib"
[ -e "$K/sysroot/lib64" ] || ln -s usr/lib64 "$K/sysroot/lib64"
# headers del kernel nuevos (los de 22.04 son 5.15; memory.c usa PAGEMAP_SCAN y UFFD_FEATURE_WP_ASYNC, Linux 6.7+):
# los de Arch (paquete linux-api-headers $KHDR_PKG, sólo headers UAPI)
mkdir -p /tmp/khdr && tar --zstd -xf "/cache/$KHDR_PKG" -C /tmp/khdr usr/include
rm -rf "$K/sysroot/usr/include/x86_64-linux-gnu/asm"   # the multiarch asm/ would shadow the new one
cp -a /tmp/khdr/usr/include/. "$K/sysroot/usr/include/"
# headers de Vulkan nuevos (los de 22.04 son 1.3.204; el runtime usa los de 1.4)
git clone -q --depth 1 -b "$VK_TAG" https://github.com/KhronosGroup/Vulkan-Headers.git /tmp/vkh
rm -rf "$K/sysroot/usr/include/vulkan" "$K/sysroot/usr/include/vk_video"
cp -a /tmp/vkh/include/vulkan /tmp/vkh/include/vk_video "$K/sysroot/usr/include/"
# OpenH264: sólo los headers (ov_movie.c abre la biblioteca con dlopen y pide la ABI de 2.6.0, soname 8)
git clone -q --depth 1 -b "$H264_TAG" https://github.com/cisco/openh264.git /tmp/h264
mkdir -p "$K/sysroot/usr/include/wels"
cp /tmp/h264/codec/api/wels/*.h "$K/sysroot/usr/include/wels/"
# SDL 3: la misma que lleva la AppImage (container-build.sh la dejó en /out)
git clone -q --depth 1 -b "$SDL_TAG" https://github.com/libsdl-org/SDL.git /tmp/SDL
cp -a /tmp/SDL/include/SDL3 "$K/sysroot/usr/include/"
cp -L /out/libSDL3.so.0 "$K/lib/libSDL3.so.0"
ln -s ../../../../lib/libSDL3.so.0 "$K/sysroot/usr/lib/x86_64-linux-gnu/libSDL3.so"
python3 - "$K/sysroot" <<'EOF'
import os, sys
root = sys.argv[1]
for d, dirs, files in os.walk(root):
    for n in dirs + files:
        p = os.path.join(d, n)
        if os.path.islink(p) and os.readlink(p).startswith('/'):
            t = root + os.readlink(p)
            os.remove(p)
            os.symlink(os.path.relpath(t, d), p)
EOF

# Python del lifter
tar -xzf "/cache/$PY_TAR" -C "$K"
"$K/python/bin/python3" -m pip install -q --no-cache-dir --disable-pip-version-check \
    -r /src/launcher/appimage/toolkit/requirements.txt
find "$K/python" -name __pycache__ -prune -exec rm -rf {} +
rm -rf "$K/python/lib/python3"*/test "$K/python/lib/python3"*/idlelib "$K/python/lib/python3"*/tkinter \
       "$K/python/lib/python3"*/ensurepip "$K/python/lib/python3"*/site-packages/pip
# ninja y los envoltorios
cp /usr/bin/ninja "$K/bin/ninja"
for w in clang clang++ ld.lld pkg-config; do cp "/src/launcher/appimage/toolkit/$w" "$K/bin/$w"; done
chmod 755 "$K"/bin/*
cp /src/launcher/appimage/toolkit/README "$K/README"
chown -R "$HOST_UID:$HOST_GID" "$K"
du -sh "$K" "$K"/*
