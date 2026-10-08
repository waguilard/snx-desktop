# Arquitectura y mantenimiento

## Componentes

| Archivo | Responsabilidad |
| --- | --- |
| app.py | UI Tk, wizard, perfil privado, detección local de SNX y contador |
| terminal_session.py | Ejecutar SNX con su terminal interactiva, sin capturar stdin |
| tray.py | Icono PyQt6 y comandos por socket UNIX privado |
| install.sh / uninstall.sh | Instalar o archivar la aplicación por usuario |
| dns/service.py | Configuración validada, dnsmasq local y restauración del resolvedor |
| dns/snx-desktop-dns.service | Servicio root acotado mediante restricciones systemd |
| tests/ | Pruebas con perfiles temporales y DNS ficticio |

## Separación de privilegios

La UI funciona como usuario normal. Solo el servicio DNS y su configuración requieren root. La UI invoca KDE AskPass al guardar cambios DNS; no recibe ni reenvía la contraseña. El servicio copia únicamente listas de dominios validadas; no ejecuta contenido del perfil.

## Estado y sesiones

La interfaz detecta procesos y nombres de interfaces SNX localmente, sin sondear servidores. El contador identifica la sesión por arranque del sistema y proceso. El backend DNS recuerda los servidores recibidos solo para el mismo arranque e identidad de interfaz, evitando reutilizarlos entre sesiones diferentes.

## Extensiones

No añadas servidores, usuarios, sufijos ni nombres internos como constantes. Conserva los valores variables en configuración local. Para soportar otro gestor DNS, implementa un backend que respete sus API y restauración; no sobrescribas indiscriminadamente resolv.conf.

## Pruebas y límites

Las pruebas comprueban validación, permisos, selección de DNS, restauración, ausencia de proxy sin configuración, reloj y separación entre túneles. Las pruebas de UI requieren una sesión gráfica. Una conexión VPN real depende del cliente autorizado y de la política del gateway; no se ejecuta en las pruebas automatizadas.
