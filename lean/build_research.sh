# Clone, fetch cache, build and extract one research project, entirely on this drive.
# Usage: bash lean/build_research.sh <name> <repo> <commit> <module> [extra import for the extractor]
set -u
P="$(cd "$(dirname "$0")/.." && pwd)"
N="$1"; REPO="$2"; COMMIT="$3"; M="$4"; EXTRA="${5:-}"
source "$P/lean/research_env.sh"
L="$P/results/${N}_rebuild.log"
cd "$P/research" && rm -rf "$N" && git clone https://github.com/$REPO.git "$N" > "$L" 2>&1 && cd "$N" && git checkout -q "$COMMIT" >> "$L" 2>&1 || { echo "CLONE_FAILED" >> "$L"; exit 1; }
{ [ -n "$EXTRA" ] && echo "import $EXTRA"; cat "$P/lean/Extract.lean"; } > Extract.lean
printf '\n[[lean_exe]]\nname = "extract"\nroot = "Extract"\nsupportInterpreter = true\n' >> lakefile.toml
for try in 1 2 3; do lake exe cache get >> "$L" 2>&1 && break; done
rm -f "$P/tools/mathlib-cache/"*.ltar
lake build "$M" extract >> "$L" 2>&1; echo "BUILD_EXIT=$?" >> "$L"
mkdir -p "$P/data/derived/research/$N"
lake exe extract "$P/data/derived/research/$N/graph" "$M" >> "$L" 2>&1; echo "EXTRACT_EXIT=$?" >> "$L"
