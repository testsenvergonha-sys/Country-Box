#!/bin/sh
# Country-Box: el tarball de cada release, junto a la AppImage (carta abierta de RecompLauncher, punto 3: un árbol
# normal, sin FUSE ni montaje). Sale del mismo AppDir que la AppImage, así que llevan lo mismo:
#
#   Country-Box/country-box        enlace a AppRun: lo que corre el jugador (./Country-Box/country-box)
#   Country-Box/AppRun, usr/...    el launcher, libSDL3, prep/ y el kit de compilación (igual que la AppImage)
#
# Portable igual que la AppImage: AppRun le dice al launcher que corre desde esta carpeta y todo lo que escribe va a
# Country-Box-data/ JUNTO a la carpeta extraída (no dentro): extraer una versión nueva encima no toca los datos, y
# una AppImage en la misma carpeta comparte la misma biblioteca.
#
#   sh launcher/make_tarball.sh APPDIR OUT_DIR      (make_appimage.sh lo llama; deja OUT_DIR/Country-Box-linux-x86_64.tar.gz)
set -eu
umask 022
APPDIR=$1
OUT=$2
[ -x "$APPDIR/AppRun" ] && [ -x "$APPDIR/usr/bin/country-box-launcher" ] ||
    { echo "make_tarball: $APPDIR no es un AppDir de Country-Box" >&2; exit 1; }
STAGE=$OUT/tarball
rm -rf "$STAGE"
mkdir -p "$STAGE/Country-Box"
cp -a "$APPDIR/." "$STAGE/Country-Box/"
ln -s AppRun "$STAGE/Country-Box/country-box"
# lo que el jugador lee al extraerlo (en inglés: es para él)
cat > "$STAGE/Country-Box/README.txt" <<'TXT'
Country-Box for Linux and Steam Deck.

Run:   ./country-box            (the launcher window)
       ./country-box --skip     (straight into the game you played last)
       ./country-box --help     (every option)

Everything Country-Box writes (your library, builds, saves, settings, logs, caches) goes into the folder
Country-Box-data next to this Country-Box folder. Delete both folders and Country-Box is gone completely.
To update, extract the new version over this folder; Country-Box-data is not touched.
TXT
TAR=$OUT/Country-Box-linux-x86_64.tar.gz
# orden y dueño fijos: el mismo árbol da el mismo tarball (salvo mtimes)
tar --sort=name --owner=0 --group=0 --numeric-owner -C "$STAGE" -czf "$TAR.part" Country-Box
mv "$TAR.part" "$TAR"
rm -rf "$STAGE"
echo "built $TAR"
