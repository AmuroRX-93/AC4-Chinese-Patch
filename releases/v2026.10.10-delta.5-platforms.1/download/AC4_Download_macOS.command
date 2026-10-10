#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASE='https://github.com/AmuroRX-93/AC4-Chinese-Patch/releases/download/v2026.10.10-delta.5-platforms.1/'
ARCHIVE='AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip'
EXPECTED='650c095b17bd83354640ee115a22e93b8fe291a70911f82ba14c56b72b018a43'
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
AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part001 bcd844dd91bf25b7d8a4f00184897e466c96b58240727da162f8bace2f2b84bf
AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part002 8f1588e53a6e8fc5110e47a42684d3a8631a7aebb4a664a0058ded2f3c14277b
AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part003 4942c596eef1a0d42e3f45aace51372fd625c07ad2bb0544ec7214dfc9c50cee
AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part004 26ae37b06dc37d68e67eb5ec7ee4270400949119e67441e291d732924d94afb9
AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part005 5e4df92a8f2a9cca53a42b4929d00890dff9e295e64f19b4b1cb6e6bff9d793f
AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part006 10d6ae65958bfdf813ebaa6033b62c98507079328c9e9822af92ce254179cefd
AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part007 ceb9a3be78afde5bddcad68a9ade845d74f2a6125bf0eae94e7b5b09316c8546
AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part008 ff1010f233f6422f88a8b02b7709a496daa48da089fb440d1112a900f131f907
AC4_PARTS
 cat "$ROOT/AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part001" "$ROOT/AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part002" "$ROOT/AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part003" "$ROOT/AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part004" "$ROOT/AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part005" "$ROOT/AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part006" "$ROOT/AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part007" "$ROOT/AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part008" > "$ROOT/$ARCHIVE.assembling"
 [ "$(hash_file "$ROOT/$ARCHIVE.assembling")" = "$EXPECTED" ] || { echo 'Combined archive checksum failed'; exit 1; }
 if [ -e "$ROOT/$ARCHIVE" ]; then mv "$ROOT/$ARCHIVE" "$ROOT/$ARCHIVE.old.$(date +%Y%m%d%H%M%S)"; fi
 mv "$ROOT/$ARCHIVE.assembling" "$ROOT/$ARCHIVE"
fi
if [ "${1:-}" = '--merge-only' ]; then echo "Verified archive: $ROOT/$ARCHIVE"; exit 0; fi
DEST="$ROOT/AC4_delta5_20261010_extracted"
if [ -e "$DEST" ]; then
 echo "Extraction directory already exists; keep it or rename it before retrying: $DEST"
 exit 1
fi
unzip -q "$ROOT/$ARCHIVE" -d "$DEST"
echo "Complete: $DEST/AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012"
echo 'Run the installation entry inside the extracted folder. Python is included.'
