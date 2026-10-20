#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE='https://github.com/AmuroRX-93/AC4-Chinese-Patch/releases/download/v2026.10.20-loadguard.1-rc1/'
ARCHIVE='AC4_delta5_LoadGuard_Normal_20261020_rc1.zip'
EXPECTED='2aedb74015f7d39ef766ca85ca9648bebae86231e26d5924bb61bacc08c7977d'
case "$(uname -s)" in
 Darwin) hash_file() { shasum -a 256 "$1" | cut -d ' ' -f 1; } ;;
 Linux) hash_file() { sha256sum "$1" | cut -d ' ' -f 1; } ;;
 *) echo 'Unsupported operating system'; exit 1 ;;
esac
if [ -f "$ROOT/$ARCHIVE" ] && [ "$(hash_file "$ROOT/$ARCHIVE")" = "$EXPECTED" ]; then
 echo 'Archive already verified.'
else
 while IFS=' ' read -r NAME HASH; do
  FILE="$ROOT/$NAME"
  if [ -f "$FILE" ] && [ "$(hash_file "$FILE")" = "$HASH" ]; then
   echo "Verified: $NAME"
  else
   echo "Downloading: $NAME"
   curl -fL --connect-timeout 20 --max-time 1200 --retry 2 --retry-delay 2 "$BASE$NAME" -o "$FILE.download"
   [ "$(hash_file "$FILE.download")" = "$HASH" ] || { echo "Checksum failed: $NAME"; exit 1; }
   if [ -e "$FILE" ]; then mv "$FILE" "$FILE.invalid.$(date +%Y%m%d%H%M%S)"; fi
   mv "$FILE.download" "$FILE"
  fi
 done <<'AC4_PARTS'
AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part001 09b7be3ae306f01726176f75ee9f453c471aee1941fc8be303cb082bda67e94e
AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part002 c4091d004c845ff7e0003cf15c6972560b5b2cafc6c5fe7afe258fc92da2c06e
AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part003 e0ba84423a9d0c2cf2f2c3da1c9eff6f8fd37802b31e76104ca3e08117836443
AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part004 d686d1fc4bddb368c0bdc0366732e6158a6835c49d1857325f69fbc4aba0d3c1
AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part005 b401df9d1144c1204acfbbc9d53c4a91577d0ac8c468777ec6404bd672550401
AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part006 ada1e043fb5ba057eefb9833137c40a2d02447d338ac0535fbd1337a0d443362
AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part007 11931f6ce00dd52d777ea31f2cb872111bc50994b3b22f9a4516685ae7c06502
AC4_PARTS
 cat "$ROOT/AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part001" "$ROOT/AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part002" "$ROOT/AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part003" "$ROOT/AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part004" "$ROOT/AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part005" "$ROOT/AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part006" "$ROOT/AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part007" > "$ROOT/$ARCHIVE.assembling"
 [ "$(hash_file "$ROOT/$ARCHIVE.assembling")" = "$EXPECTED" ] || { echo 'Combined archive checksum failed'; exit 1; }
 if [ -e "$ROOT/$ARCHIVE" ]; then mv "$ROOT/$ARCHIVE" "$ROOT/$ARCHIVE.old.$(date +%Y%m%d%H%M%S)"; fi
 mv "$ROOT/$ARCHIVE.assembling" "$ROOT/$ARCHIVE"
fi
if [ "${1:-}" = '--merge-only' ]; then echo "Verified archive: $ROOT/$ARCHIVE"; exit 0; fi
DEST="$ROOT/AC4_loadguard_20261020_rc1_extracted"
if [ -e "$DEST" ]; then
 echo "Extraction directory already exists; keep it or rename it before retrying: $DEST"
 exit 1
fi
unzip -q "$ROOT/$ARCHIVE" -d "$DEST"
echo "Complete: $DEST/AC4_delta5_LoadGuard_Normal_20261020_rc1"
echo 'Run the installation entry inside the extracted folder. Python is included.'
