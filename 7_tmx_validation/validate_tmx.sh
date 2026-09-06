#!/bin/bash
# TMX 1.4 DTD validator
# Usage:
#   ./validate_tmx.sh file.tmx              # validate one file
#   ./validate_tmx.sh *.tmx                 # validate multiple files
#   ./validate_tmx.sh /path/to/folder/      # validate every .tmx in folder

set -u

DTD="$(dirname "$0")/tmx14.dtd"

if [ ! -f "$DTD" ]; then
    echo "ERROR: tmx14.dtd not found next to this script."
    echo "Expected at: $DTD"
    exit 2
fi

if ! command -v xmllint >/dev/null 2>&1; then
    echo "ERROR: xmllint not installed."
    echo "  macOS:  brew install libxml2 (xmllint usually preinstalled)"
    echo "  Ubuntu: sudo apt install libxml2-utils"
    echo "  Windows: install via WSL, or use Notepad++ XML Tools plugin"
    exit 2
fi

if [ $# -eq 0 ]; then
    echo "Usage: $0 <file.tmx | folder | glob>"
    exit 1
fi

# Expand folder argument into all .tmx inside
FILES=()
for arg in "$@"; do
    if [ -d "$arg" ]; then
        while IFS= read -r f; do FILES+=("$f"); done < <(find "$arg" -maxdepth 1 -name '*.tmx' | sort)
    else
        FILES+=("$arg")
    fi
done

pass=0
fail=0
for f in "${FILES[@]}"; do
    if [ ! -f "$f" ]; then
        echo "✗  $f  (file not found)"
        fail=$((fail+1))
        continue
    fi
    # Run xmllint, capture stderr
    if err=$(xmllint --noout --dtdvalid "$DTD" "$f" 2>&1); then
        echo "✓  $f"
        pass=$((pass+1))
    else
        echo "✗  $f"
        echo "$err" | sed 's/^/     /'
        fail=$((fail+1))
    fi
done

echo "---"
echo "Passed: $pass    Failed: $fail    Total: $((pass+fail))"
[ $fail -eq 0 ]
