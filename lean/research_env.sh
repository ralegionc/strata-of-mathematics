# Source before building a research project (Git Bash on Windows, or any POSIX shell).
# Keeps every toolchain, mathlib cache and temporary file inside this project's tools/ folder,
# so nothing lands in the home directory or on the system drive:
#   ELAN_HOME          Lean toolchains (about 3 GB each)
#   MATHLIB_CACHE_DIR  compressed mathlib cache files (`lake exe cache get` otherwise uses ~/.cache/mathlib)
#   XDG_CACHE_HOME, TMP, TEMP, TMPDIR  other caches and temporary files
# Install elan into it once with: elan-init -y --default-toolchain none --no-modify-path
T="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)/tools"
mkdir -p "$T/elan" "$T/mathlib-cache" "$T/cache" "$T/tmp"
native() { if command -v cygpath > /dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi; }
export ELAN_HOME="$(native "$T/elan")"
export MATHLIB_CACHE_DIR="$(native "$T/mathlib-cache")"
export XDG_CACHE_HOME="$(native "$T/cache")"
export TMP="$(native "$T/tmp")"
export TEMP="$TMP"
export TMPDIR="$T/tmp"
export PATH="$T/elan/bin:$(echo "$PATH" | tr ':' '\n' | grep -v '/.elan/bin' | paste -sd:)"
