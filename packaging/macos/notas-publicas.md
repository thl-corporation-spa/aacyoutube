## Instalar

Pega esto en la app **Terminal**:

```bash
curl -fsSL https://raw.githubusercontent.com/@REPO@/main/instalar.sh | bash
```

Detecta si tu Mac es Intel o Apple Silicon, descarga la versión que toca y la
deja lista en Aplicaciones, sin avisos.

### O a mano

| Tu Mac | Descarga |
|---|---|
| Procesador **Intel** | `aacyoutube-*-macos-x86_64.dmg` |
| Chip **M1 · M2 · M3 · M4** | `aacyoutube-*-macos-arm64.dmg` |

¿No sabes cuál tienes?  → «Acerca de este Mac».

Arrastra la app a `Aplicaciones` y **la primera vez ábrela con clic derecho →
Abrir**. Si macOS dice que «está dañada», pega en la Terminal:

```bash
xattr -dr com.apple.quarantine /Applications/aacyoutube.app
```

**No hace falta instalar nada más:** `ffmpeg` viene dentro de la app.

Requiere macOS 11 Big Sur o posterior en Apple Silicon, y macOS 10.15 Catalina
o posterior en Intel.
