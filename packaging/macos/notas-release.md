## Instalar en macOS

| Tu Mac | Descarga |
|---|---|
| Procesador **Intel** | `aacyoutube-*-macos-x86_64.dmg` |
| Chip **M1 / M2 / M3 / M4** | `aacyoutube-*-macos-arm64.dmg` |

¿No sabes cuál tienes?  → «Acerca de este Mac».

Abre el `.dmg`, arrastra la app a `Applications` y **la primera vez ábrela con
clic derecho → Abrir**. La app no está firmada con una cuenta de desarrollador
de Apple de pago, así que macOS pide confirmación una vez.

Trae **ffmpeg incluido**: no hay que instalar nada más.

O, con la [CLI de GitHub](https://cli.github.com), que se encarga de elegir la
arquitectura y de quitar la marca de cuarentena:

```bash
gh repo clone @REPO@
cd aacyoutube && ./install.sh
```

## Instalar en Linux

Fedora, Ubuntu, Debian, Arch y openSUSE:

```bash
git clone git@github.com:@REPO@.git
cd aacyoutube && ./install.sh
```

---

Documentación: [instalación](https://github.com/@REPO@/blob/main/docs/INSTALACION.md) ·
[uso](https://github.com/@REPO@/blob/main/docs/USO.md) ·
[solución de problemas](https://github.com/@REPO@/blob/main/docs/SOLUCION-DE-PROBLEMAS.md)
