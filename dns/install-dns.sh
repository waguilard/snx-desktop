#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Ejecutar con KDE AskPass y sudo -A.'; exit 1; }
src=$(cd -- "$(dirname -- "$0")" && pwd)
[ ! -e /etc/systemd/system/snx-desktop-dns.service ] || { echo 'Integración ya instalada; revisar antes de actualizar.'; exit 1; }
[ ! -L /etc/resolv.conf ] || { echo 'Este método requiere resolv.conf regular gestionado por NetworkManager.'; exit 1; }
[ -x /usr/sbin/dnsmasq ]
install -d -m 755 /usr/local/libexec
install -d -m 700 /var/lib/snx-desktop-dns
install -m 600 /etc/resolv.conf /var/lib/snx-desktop-dns/resolv.before
install -m 644 "$src/service.py" /usr/local/libexec/snx-desktop-dns.py
install -m 644 "$src/snx-desktop-dns.service" /etc/systemd/system/snx-desktop-dns.service
systemctl daemon-reload
systemctl enable --now snx-desktop-dns.service
