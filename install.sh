#!/bin/bash
set -euo pipefail
src=$(cd -- "$(dirname -- "$0")" && pwd)
app="$HOME/.local/share/snx-desktop"
launcher="$HOME/.local/share/applications/snx-desktop.desktop"
if ! /usr/bin/python3 -c 'import tkinter' 2>/dev/null; then
  echo 'Falta python3-tk. Instálalo con el gestor de tu distribución.'; exit 1
fi
if ! /usr/bin/python3 -c 'import PyQt6' 2>/dev/null; then
  echo 'Falta python3-pyqt6 para la bandeja. Instálalo con tu gestor de paquetes.'; exit 1
fi
command -v konsole >/dev/null || { echo 'Falta Konsole.'; exit 1; }
backup="$HOME/.local/share/snx-desktop-backups/$(date +%Y%m%d-%H%M%S)"
if [ -e "$app" ] || [ -e "$launcher" ]; then
 mkdir -p "$backup"; chmod 700 "$backup"
 [ ! -e "$app" ] || cp -a "$app" "$backup/app"
 [ ! -e "$launcher" ] || cp -a "$launcher" "$backup/snx-desktop.desktop"
fi
mkdir -p "$app" "$(dirname "$launcher")"
install -m 644 "$src/app.py" "$src/terminal_session.py" "$src/tray.py" "$app/"
install -d -m 755 "$app/docs"
install -m 644 "$src/docs/GUIA.md" "$app/docs/"
cat > "$launcher" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=SNX Desktop
Comment=Conexión y desconexión de Check Point SNX
Exec=/usr/bin/python3 "$app/app.py"
Icon=network-vpn
Terminal=false
Categories=Network;RemoteAccess;
StartupNotify=true
EOF
chmod 644 "$launcher"
command -v update-desktop-database >/dev/null && update-desktop-database "$HOME/.local/share/applications" || true
echo "Instalado: $app"
echo 'Abre SNX Desktop desde el menú de aplicaciones.'
