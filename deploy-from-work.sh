#!/bin/bash
# deploy-from-work.sh — Pull from GitHub and deploy to NAS over SSH/Tailscale
#
# Usage (from work PC):
#   ./deploy-from-work.sh          # dry-run (preview changes)
#   ./deploy-from-work.sh --go     # pull from GitHub and sync to NAS
#
# Prerequisites:
#   - git clone https://github.com/schonn0129/FAA-Audit.git ~/FAA-Audit
#   - SSH access to NAS via Tailscale (schonn.underwood@100.126.188.60)
#   - SSH key configured for passwordless login (recommended)

set -euo pipefail

SRC="$HOME/FAA-Audit/"
NAS_USER="schonn.underwood"
NAS_HOST="100.126.188.60"
NAS_DEST="/volume1/audit-app/"

# Verify source exists
if [ ! -d "$SRC/.git" ]; then
    echo "ERROR: $SRC is not a git repo. Clone it first:"
    echo "  git clone https://github.com/schonn0129/FAA-Audit.git ~/FAA-Audit"
    exit 1
fi

# Pull latest from GitHub
cd "$SRC"
echo "Pulling latest from GitHub..."
git pull
echo ""

# Warn if there are uncommitted changes
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
    echo "Deploying $SRC -> ${NAS_USER}@${NAS_HOST}:${NAS_DEST}"
    rsync -avz --delete "${EXCLUDES[@]}" "$SRC" "${NAS_USER}@${NAS_HOST}:${NAS_DEST}"
    echo ""
    echo "Deploy complete. To rebuild containers:"
    echo "  1. Open Container Manager on the NAS (QuickConnect or http://${NAS_HOST}:5000)"
    echo "  2. Stop the project"
    echo "  3. Delete old images (faa-audit-backend, faa-audit-frontend)"
    echo "  4. Rebuild and start the project"
else
    echo "DRY RUN — showing what would change (add --go to apply):"
    echo ""
    rsync -avzn --delete "${EXCLUDES[@]}" "$SRC" "${NAS_USER}@${NAS_HOST}:${NAS_DEST}"
fi
