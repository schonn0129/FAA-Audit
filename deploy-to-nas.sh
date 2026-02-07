#!/bin/bash
# deploy-to-nas.sh — Sync FAA-Audit code from local repo to NAS deployment
#
# Usage:
#   ./deploy-to-nas.sh          # dry-run (preview changes)
#   ./deploy-to-nas.sh --go     # actually sync files
#
# The NAS copy is a deployment target only — no .git on the NAS.
# All git operations happen in ~/FAA-Audit on your local machine.

set -euo pipefail

SRC="$HOME/FAA-Audit/"
DEST="/Volumes/audit-app/"

# Verify source exists
if [ ! -d "$SRC/.git" ]; then
    echo "ERROR: $SRC is not a git repo. Clone it first:"
    echo "  git clone https://github.com/schonn0129/FAA-Audit.git ~/FAA-Audit"
    exit 1
fi

# Verify NAS is mounted
if [ ! -d "$DEST" ]; then
    echo "ERROR: NAS not mounted at $DEST"
    exit 1
fi

# Warn if there are uncommitted changes
cd "$SRC"
if ! git diff --quiet HEAD 2>/dev/null; then
    echo "WARNING: You have uncommitted changes in $SRC"
    echo "  Consider committing and pushing to GitHub first."
    echo ""
fi

EXCLUDES=(
    --exclude='.git/'
    --exclude='data/'
    --exclude='node_modules/'
    --exclude='__pycache__/'
    --exclude='.env'
    --exclude='*.pyc'
    --exclude='.DS_Store'
)

if [ "${1:-}" = "--go" ]; then
    echo "Deploying $SRC -> $DEST"
    rsync -av --delete "${EXCLUDES[@]}" "$SRC" "$DEST"
    echo ""
    echo "Deploy complete. To rebuild containers:"
    echo "  1. Open Container Manager on the NAS"
    echo "  2. Stop the project"
    echo "  3. Delete old images (faa-audit-backend, faa-audit-frontend)"
    echo "  4. Rebuild and start the project"
else
    echo "DRY RUN — showing what would change (add --go to apply):"
    echo ""
    rsync -avn --delete "${EXCLUDES[@]}" "$SRC" "$DEST"
fi
