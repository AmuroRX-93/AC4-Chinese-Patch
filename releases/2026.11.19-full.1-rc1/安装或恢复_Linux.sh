#!/bin/sh
AC4_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
case "$(uname -s)/$(uname -m)" in
 Darwin/arm64) AC4_HOST=macos-arm64 ;;
 Darwin/x86_64) AC4_HOST=macos-x64 ;;
 Linux/x86_64) AC4_HOST=linux-x64 ;;
 Linux/aarch64|Linux/arm64) AC4_HOST=linux-arm64 ;;
 *) echo "Unsupported OS / CPU architecture"; exit 1 ;;
esac
AC4_PY="$AC4_ROOT/runtime/$AC4_HOST/python/bin/python3"
if [ ! -f "$AC4_PY" ]; then echo "Bundled Python missing. Extract the whole package first."; exit 1; fi
if [ ! -x "$AC4_PY" ]; then chmod u+x "$AC4_PY" || exit 1; fi
"$AC4_PY" -E -s -B "$AC4_ROOT/player_tools.py" "$@"
AC4_STATUS=$?
if [ "$#" -eq 0 ]; then printf '按回车关闭...'; read -r AC4_REPLY; fi
exit "$AC4_STATUS"
