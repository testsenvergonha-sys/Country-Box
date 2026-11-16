#!/usr/bin/env bash
# Country-Box · RomFS overlay regression test (directory builds, MP4_ROMFS_MODS)
#
# Reproduces the upstream defect this patch fixes: in a ROMFS_DIRECTORY build the overlay loader hashed the
# *original* through `image`, which is -1 there, so any manifest that replaces an existing file stopped the start
# with "read of hash input". After the fix the original is hashed from <romfs>/<name>.
#
# Usage: test-overlay.sh <build dir containing country-box> <game dir with exefs/ romfs/> [work dir]
#   exit 0 = all cases PASS, 1 = a case failed
#
# The cases never touch the player's copy: every overlay lives in the work dir, the game directory is only read.

set -u

BUILD=${1:?usage: test-overlay.sh <build dir> <game dir> [work dir]}
GAME=${2:?usage: test-overlay.sh <build dir> <game dir> [work dir]}
WORK=${3:-$HOME/cb-test}
TARGET=${TARGET_REL:-UI/UIPak.pak}      # a RomFS file present in the index
SECONDS_RUN=${SECONDS_RUN:-10}

BIN=$BUILD/country-box
REL=$GAME/romfs/$TARGET
[ -x "$BIN" ] || { echo "FAIL: $BIN is not executable"; exit 1; }
[ -f "$REL" ] || { echo "FAIL: $REL missing in the game copy"; exit 1; }

SZ=$(stat -c %s "$REL")
SHA=$(sha256sum "$REL" | cut -d' ' -f1)
BASE=$(dirname "$TARGET")
[ -d "$GAME/romfs/$BASE" ] || { echo "FAIL: $BASE missing"; exit 1; }

echo "== test-overlay: $TARGET ($SZ bytes, ${SHA:0:12}…) =="
WORK=$WORK/overlay-$$
rm -rf "$WORK"; mkdir -p "$WORK"

mk_overlay() {                       # mk_overlay <name> <copy|zero|none> <orig-hash> <new-hash-optional>
    local d=$WORK/mod-$1 mode=$2 orig=${3:-} newhash=${4:-}
    mkdir -p "$d/$BASE"
    case $mode in
    copy) cp "$REL" "$d/$TARGET" ;;
    zero) python3 -c "open('$d/$TARGET','wb').write(b'\0'*$SZ)" ;;
    none) : ;;
    esac
    if [ -z "$newhash" ]; then newhash=$(sha256sum "$d/$TARGET" 2>/dev/null | cut -d' ' -f1); fi
    printf '%s\t%s\t%s\t%s\n' "$TARGET" "$SZ" "$newhash" "$orig" > "$d/manifest.tsv"
}

run_case() {                         # run_case <name> <expect: run|fatal> <needle>
    local name=$1 expect=$2 needle=${3:-} log=$WORK/$1.log rc
    MP4_ROMFS_MODS=$WORK/mod-$name timeout 120 "$BIN" --exefs "$GAME/exefs" --romfs "$GAME/romfs" \
        --seconds "$SECONDS_RUN" > "$log" 2>&1
    rc=$?
    if [ "$expect" = run ]; then
        if [ "$rc" -eq 0 ] && grep -q "RomFS overlay: .*replaces the original" "$log"; then
            echo "PASS  $name (exit 0, overlay loaded)"; return 0
        fi
        echo "FAIL  $name (exit $rc, expected a normal run)"; return 1
    fi
    if [ "$rc" -ne 0 ] && grep -q "$needle" "$log"; then
        echo "PASS  $name (exit $rc, refused: $(grep -m1 -o "$needle" "$log"))"; return 0
    fi
    echo "FAIL  $name (exit $rc, expected refusal: $needle)"; return 1
}

fails=0
mk_overlay ok       copy "$SHA";                       run_case ok       run   "" || fails=$((fails+1))
mk_overlay badorig  copy "0000000000000000000000000000000000000000000000000000000000000000"
                                                       run_case badorig  fatal "the original of" || fails=$((fails+1))
mk_overlay badnew   copy "$SHA" "1111111111111111111111111111111111111111111111111111111111111111"
                                                       run_case badnew   fatal "its manifest says" || fails=$((fails+1))
mk_overlay missing  none "$SHA" "$SHA";                              run_case missing  fatal "missing" || fails=$((fails+1))

# zero: same size, valid manifest, content wiped. The overlay must be *served*: the game loads it (log line) and then
# fails on the zeroed data, i.e. a non-zero exit after the "replaces the original" line.
mk_overlay zero     zero "$SHA"
MP4_ROMFS_MODS=$WORK/mod-zero timeout 120 "$BIN" --exefs "$GAME/exefs" --romfs "$GAME/romfs" \
    --seconds "$SECONDS_RUN" > "$WORK/zero.log" 2>&1
zero_rc=$?
if [ "$zero_rc" -ne 0 ] && grep -q "replaces the original" "$WORK/zero.log"; then
    echo "PASS  zero (exit $zero_rc after the overlay was served)"
else
    echo "FAIL  zero (exit $zero_rc, the zeroed file does not look served)"; fails=$((fails+1))
fi

echo "== cases failing: $fails (logs in $WORK) =="
[ "$fails" -eq 0 ]
