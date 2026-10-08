# SNX Desktop

Interfaz local independiente para Check Point SNX en Linux/KDE. Incluye asistente, conexión mediante Konsole, desconexión, IP del túnel, duración de sesión, bandeja del sistema y DNS dividido opcional.

No es una aplicación oficial de Check Point. No incluye ni redistribuye el cliente propietario SNX. Debes obtener una versión autorizada y compatible con tu entorno. Este proyecto no sustituye todas las funciones de Harmony Endpoint.

## Instalación rápida en Debian/KDE

Con un cliente SNX funcional en `/usr/bin/snx`:

```bash
sudo apt install python3-tk python3-pyqt6 konsole iproute2 procps
bash install.sh
```

Abre **SNX Desktop** desde el menú. El wizard solicita sitio, servidor y usuario; puedes dejar los sufijos DNS vacíos. La contraseña se introduce directamente en SNX, en Konsole. Los datos de conexión no tienen valores predeterminados.

Para habilitar la integración DNS opcional, consulta primero las condiciones de compatibilidad en la [guía de instalación y operación](docs/GUIA.md). No requiere habilitar DNS para conectar la VPN.

## Documentación

- [Guía de instalación, configuración y diagnóstico](docs/GUIA.md)
- [Arquitectura y mantenimiento del código](docs/ARQUITECTURA.md)
- [Privacidad y seguridad](SECURITY.md)

## Validación

Validado localmente en Debian 13/KDE. La disponibilidad de SNX y sus dependencias depende de la versión y del gateway. Otras distribuciones no han sido verificadas.

```bash
python3 tests/test_snx_dns.py
python3 tests/test_dns_lifecycle.py
python3 tests/test_dns_optional.py
python3 tests/test_dns_forwarding.py
python3 tests/test_snx_clock.py
# Requiere sesión gráfica con Tk; no inicia conexión VPN:
python3 tests/test_snx_desktop.py
```

Las pruebas DNS utilizan dominios ficticios y servidores simulados. No contienen datos de ninguna organización.
