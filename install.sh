#!/data/data/com.termux/files/usr/bin/env bash
# Weatui installer: prefix-aware venv + symlink, with a safe uninstall.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX_DIR="${PREFIX:-$HOME/.local}"
DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/weatui"
VENV="$DATA_ROOT/venv"
BIN_DIR="$PREFIX_DIR/bin"
LAUNCHER="$BIN_DIR/weatui"
UNINSTALL=0
DRY=0

usage() {
    cat <<EOF
Usage: ./install.sh [options]

Install:
  --prefix DIR   launcher prefix (default: \$PREFIX, else ~/.local)
  --dry-run      print what would change

Uninstall:
  --uninstall    remove the launcher and managed venv

  -h, --help     show this help
EOF
}

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
info() { printf '[weatui] %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

while [ "$#" -gt 0 ]; do
    case "$1" in
        --prefix) shift; [ "$#" -gt 0 ] || die "--prefix needs a directory"; PREFIX_DIR="$1" ;;
        --prefix=*) PREFIX_DIR="${1#*=}" ;;
        --dry-run) DRY=1 ;;
        --uninstall) UNINSTALL=1 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown option: $1 (try --help)" ;;
    esac
    shift
done

case "$PREFIX_DIR" in
    /*) ;;
    *) PREFIX_DIR="$PWD/$PREFIX_DIR" ;;
esac
BIN_DIR="$PREFIX_DIR/bin"
LAUNCHER="$BIN_DIR/weatui"

if [ "$UNINSTALL" = "1" ]; then
    if [ -f "$DATA_ROOT/launcher" ]; then
        LAUNCHER="$(cat "$DATA_ROOT/launcher")"
    fi
    if [ -L "$LAUNCHER" ] && [ "$(readlink "$LAUNCHER")" = "$VENV/bin/weatui" ]; then
        rm -f "$LAUNCHER"
        info "removed launcher"
    elif [ -e "$LAUNCHER" ]; then
        printf 'keeping unexpected launcher: %s\n' "$LAUNCHER" >&2
    fi
    case "$VENV" in
        "$DATA_ROOT"/venv) rm -rf "$VENV" ;;
        *) die "refusing to remove unexpected venv path: $VENV" ;;
    esac
    rm -f "$DATA_ROOT/launcher"
    rmdir "$DATA_ROOT" 2>/dev/null || true
    info "uninstall complete"
    exit 0
fi

have python3 || die "python3 is required"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
    || die "Python 3.10 or newer is required"

if [ "$DRY" = "1" ]; then
    printf '  would create venv: %s\n' "$VENV"
    printf '  would install %s into it\n' "$REPO_DIR"
    printf '  would link %s -> %s\n' "$LAUNCHER" "$VENV/bin/weatui"
    exit 0
fi

mkdir -p "$(dirname "$VENV")"
[ -d "$VENV" ] || python3 -m venv "$VENV" || die "could not create venv (install python3-venv?)"
"$VENV/bin/python" -m pip install --disable-pip-version-check --quiet --upgrade "$REPO_DIR" \
    || die "pip install failed"
[ -x "$VENV/bin/weatui" ] || die "venv has no weatui launcher"

mkdir -p "$BIN_DIR"
if [ -L "$LAUNCHER" ] && [ "$(readlink "$LAUNCHER")" = "$VENV/bin/weatui" ]; then
    info "launcher already up to date: $LAUNCHER"
else
    if [ -e "$LAUNCHER" ] && [ ! -L "$LAUNCHER" ]; then
        bak="$LAUNCHER.bak-$(date +%Y%m%d-%H%M%S)-$$"
        cp -p "$LAUNCHER" "$bak"
        printf '  backup: %s\n' "$bak"
    fi
    ln -sfn "$VENV/bin/weatui" "$LAUNCHER"
    info "installed launcher -> $LAUNCHER"
fi

mkdir -p "$DATA_ROOT"
printf '%s\n' "$LAUNCHER" > "$DATA_ROOT/launcher"

info "installed: $("$VENV/bin/weatui" --version 2>/dev/null | head -n1 || echo weatui)"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) printf 'Add %s to PATH to run weatui.\n' "$BIN_DIR" ;;
esac
