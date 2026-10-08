#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Ejecutar con KDE AskPass y sudo -A.'; exit 1; }
systemctl disable --now snx-desktop-dns.service
archive="/var/lib/snx-desktop-dns/retirada-$(date +%Y%m%d-%H%M%S)"
install -d -m 700 "$archive"
[ ! -e /etc/systemd/system/snx-desktop-dns.service ] || mv /etc/systemd/system/snx-desktop-dns.service "$archive/"
[ ! -e /usr/local/libexec/snx-desktop-dns.py ] || mv /usr/local/libexec/snx-desktop-dns.py "$archive/"
systemctl daemon-reload
printf '%s\n' 'Servicio retirado; DNS restaurado si el archivo seguía bajo su control.'
