#!/bin/zsh
cd -- "${0:A:h}"
case "$(/usr/bin/uname -m)" in
 arm64) AC4_PY="./runtime/macos-arm64/python/bin/python3" ;;
 x86_64) AC4_PY="./runtime/macos-x64/python/bin/python3" ;;
 *) echo "不支持的 Mac 架构"; exit 1 ;;
esac
if [[ ! -x "$AC4_PY" ]]; then
 echo "包内 Python 缺失或无执行权限，请完整解压。"
 read -r "?按回车关闭"; exit 1
fi
"$AC4_PY" -E -s -B install.py "$@"
AC4_EXIT=$?
read -r "?按回车关闭"
exit $AC4_EXIT
