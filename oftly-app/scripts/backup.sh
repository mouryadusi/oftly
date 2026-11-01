#!/usr/bin/env bash
# Copies your database and photos into backups/oftly-<timestamp>/ (stop OFTLY first for a perfectly consistent copy,
# or use Settings > Backup in the app, which is always consistent).
set -e
cd "$(dirname "$0")/.."
DEST="backups/oftly-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST" && cp -R data/oftly.db data/media "$DEST"/ && echo "Backup saved to $DEST"
