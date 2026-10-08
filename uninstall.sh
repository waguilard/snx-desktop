#!/bin/bash
set -euo pipefail
app="$HOME/.local/share/snx-desktop"
launcher="$HOME/.local/share/applications/snx-desktop.desktop"
archive="$HOME/.local/share/snx-desktop-backups/retirada-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$archive"; chmod 700 "$archive"
[ ! -e "$app" ] || mv "$app" "$archive/app"
[ ! -e "$launcher" ] || mv "$launcher" "$archive/snx-desktop.desktop"
echo "App archivada en: $archive"
echo 'El perfil, SNX y la sesión VPN se conservan.'
command -v update-desktop-database >/dev/null && update-desktop-database "$HOME/.local/share/applications" || true
