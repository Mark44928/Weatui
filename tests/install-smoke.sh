#!/data/data/com.termux/files/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="${TMPDIR:-${RUNNER_TEMP:-$HOME/.cache}}/weatui-install-smoke.$$"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/home" "$TMP/data" "$TMP/prefix"
export HOME="$TMP/home" XDG_DATA_HOME="$TMP/data" PREFIX="$TMP/prefix"

bash "$ROOT/install.sh" >/dev/null
test -L "$TMP/prefix/bin/weatui"
"$TMP/prefix/bin/weatui" --version | grep -Fq "weatui"
bash "$ROOT/install.sh" --uninstall >/dev/null
test ! -e "$TMP/prefix/bin/weatui"
test ! -e "$TMP/data/weatui/venv"
custom="$TMP/custom"
bash "$ROOT/install.sh" --prefix "$custom" >/dev/null
test -L "$custom/bin/weatui"
bash "$ROOT/install.sh" --uninstall >/dev/null
test ! -e "$custom/bin/weatui"
echo "installer smoke OK"
