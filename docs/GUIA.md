# Guía de instalación y operación - SNX Desktop

## Objetivo y alcance

Facilitar el uso de un cliente SNX ya instalado, manteniendo la autenticación interactiva y una configuración local privada. Esta guía usa únicamente ejemplos ficticios. No incluye perfiles, certificados, servidores ni rutas de organizaciones reales.

## Requisitos

Linux con Python 3, Tk, PyQt6, Konsole, iproute2 y procps. SNX debe estar autorizado y funcionar previamente en `/usr/bin/snx`. El instalador de esta aplicación no descarga ni instala el cliente propietario. Obtén instrucciones del proveedor o administrador para instalar SNX y sus bibliotecas compatibles; no añadas repositorios antiguos globalmente ni reemplaces bibliotecas del sistema para resolver dependencias.

Debian 13/KDE es el entorno verificado. Para otras distribuciones, busca los paquetes equivalentes en sus repositorios oficiales. El backend DNS descrito aquí requiere systemd, dnsmasq, el usuario `dnsmasq`, el grupo `nogroup` y un `/etc/resolv.conf` regular gestionado por NetworkManager. No utilizarlo sobre systemd-resolved, resolvconf u otros gestores sin adaptación.

## Instalación de la aplicación

```bash
sudo apt install python3-tk python3-pyqt6 konsole iproute2 procps
bash install.sh
```

Ejecuta el instalador como usuario normal. Instala bajo `~/.local/share/snx-desktop` y crea un lanzador de escritorio. Si hay una instalación previa, la respalda bajo `~/.local/share/snx-desktop-backups`. No inicia ni desconecta la VPN.

## Asistente

1. Revisa requisitos locales.
2. Introduce nombre del sitio, servidor y usuario. Ejemplo ficticio: `vpn.example.com`. El puerto interno predeterminado es 443.
3. Decide si deseas configurar sufijos DNS, separados por espacios. Ejemplo: `internal.example.com`. El campo adicional permite indicar nombres o dominios que deben usar el DNS de la VPN sin convertirlos en sufijos de búsqueda. Ambos campos son opcionales.
4. Revisa y guarda. Guardar no inicia la conexión.

Sin sufijos ni reglas adicionales, la app muestra **DNS: No configurado**, tanto conectada como desconectada. Para cambiar valores vuelve a **Configurar**.

## DNS dividido opcional

Antes de instalarlo, revisa el script y respalda tu configuración de resolución. En Debian compatible:

```bash
sudo apt install dnsmasq-base
SUDO_ASKPASS=/usr/bin/ksshaskpass sudo -A bash dns/install-dns.sh
```

Introduce la contraseña de sudo únicamente en la ventana gráfica de KDE. Después vuelve a Configurar y guarda tus dominios; la aplicación solicita autorización gráfica para copiar las listas validadas a configuración propiedad de root. Si el servicio no está instalado, el perfil se guarda, pero las reglas DNS no se aplican.

El servicio espera los DNS entregados por SNX y excluye los DNS normales de esa lista. Un dnsmasq local escucha únicamente en `127.0.0.54:53`: los dominios configurados utilizan el DNS de SNX; Internet conserva los servidores previos. El servicio no modifica las rutas: las redes que atraviesan la VPN dependen de SNX y de la política del gateway.

Al desconectar o detenerse restaura el archivo previo únicamente si aún conserva la configuración escrita por este servicio. Respeta cambios concurrentes. Si no configuraste dominios, no activa el proxy DNS. Aplicaciones con DNS propio/DoH o mDNS pueden comportarse de forma distinta.

## Conexión y desconexión

**Conectar** abre Konsole. Introduce tus credenciales directamente en SNX y verifica con el administrador cualquier certificado antes de aceptarlo. La app no captura ni guarda contraseñas y no acepta certificados automáticamente.

**Desconectar** ejecuta `snx -d`. Cerrar la ventana la oculta en la bandeja; salir de la aplicación conserva una VPN activa. El contador puede mostrar un tiempo aproximado si encuentra una sesión que ya existía.

## Comprobaciones puntuales

```bash
ip -br addr
getent ahostsv4 www.debian.org
getent ahostsv4 recurso.internal.example.com
systemctl status snx-desktop-dns.service
```

Sustituye el recurso ficticio por uno autorizado. La detección de túnel no garantiza acceso a todos los recursos. No es necesario explorar ni escanear el gateway.

## Archivos privados

- `~/.config/snx-desktop/profile.json`: servidor, usuario, sufijos y reglas, modo 600.
- `/var/lib/snx-desktop-dns/settings.json`: listas DNS validadas, modo 600.
- El servicio conserva respaldos y estado de sesión bajo `/var/lib/snx-desktop-dns`.

No publiques estos archivos, respaldos, registros ni capturas. Comparte únicamente el código y documentación genérica del proyecto.

## Retirada

```bash
bash uninstall.sh
# Solo si instalaste el servicio DNS:
SUDO_ASKPASS=/usr/bin/ksshaskpass sudo -A bash dns/remove-dns.sh
```

La retirada archiva la aplicación y el servicio. Conserva perfiles, respaldos y SNX; no termina una VPN activa. Desconecta primero si deseas terminarla.
