<div align="center">

```
 ██████╗ ██╗   ██╗███████╗ █████╗ ███╗   ██╗ ██████╗      ██████╗██╗     ██╗
██╔════╝ ██║   ██║██╔════╝██╔══██╗████╗  ██║██╔═══██╗    ██╔════╝██║     ██║
██║  ███╗██║   ██║███████╗███████║██╔██╗ ██║██║   ██║    ██║     ██║     ██║
██║   ██║██║   ██║╚════██║██╔══██║██║╚██╗██║██║   ██║    ██║     ██║     ██║
╚██████╔╝╚██████╔╝███████║██║  ██║██║ ╚████║╚██████╔╝    ╚██████╗███████╗██║
 ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝     ╚═════╝╚══════╝╚═╝
```

**Aprende cómo se propaga el malware — de forma segura, interactiva, sin tocar tu sistema real**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-22c55e?style=flat-square)](LICENSE)
[![Plataforma](https://img.shields.io/badge/Plataforma-Linux%20%7C%20macOS-6366f1?style=flat-square)](https://github.com/AaronGonzalez03/Worm-CLI)
[![Propósito](https://img.shields.io/badge/Prop%C3%B3sito-Solo%20Educativo-f97316?style=flat-square)](#aviso-legal)
[![PRs Bienvenidas](https://img.shields.io/badge/PRs-Bienvenidas-84cc16?style=flat-square)](CONTRIBUTING.md)

[Características](#-características) · [Instalación](#-instalación) · [Uso](#-uso) · [Comandos](#-referencia-de-comandos) · [Arquitectura](#-arquitectura) · [Aviso Legal](#-aviso-legal) · [Contribuir](#-contribuir)

</div>

---

## Descripción general

**Worm-CLI** es un simulador de gusano interactivo con IA integrada, desarrollado en Python. Opera completamente sobre un sistema de archivos falso en memoria — ningún archivo real es leído, modificado ni eliminado. El simulador está diseñado para demostrar cómo un gusano navega por un sistema, identifica objetivos sensibles, se replica y ejecuta cargas útiles, todo a través de una interfaz de terminal rica que solicita permiso al operador antes de cada acción destructiva.

Este proyecto existe para hacer el comportamiento de un gusano **tangible y observable** sin necesitar una VM aislada, un laboratorio dedicado ni privilegios elevados. Todo corre en un único proceso Python, en tu terminal, ahora mismo.

---

## Demo

> **Las capturas de pantalla y el GIF de demostración se añadirán aquí.**
> Ejecuta `python3 main.py` para ver la interfaz en vivo.

<!-- PLACEHOLDER: Sustituir por una captura de terminal real o grabación GIF -->
<!-- Herramienta recomendada: `asciinema` o `ttyrec` + `ttygif` -->
```
  📸  [ GIF de demostración — próximamente ]
```

---

## Características

| Característica | Descripción |
|---|---|
| **Sistema de archivos falso en memoria** | Árbol tipo Linux generado aleatoriamente al arrancar. Sin I/O real. |
| **Gusano IA interactivo** | El gusano narra cada acción en lenguaje natural y sugiere el siguiente paso. |
| **Detección de archivos sensibles** | Siembra archivos realistas (`.env`, `id_rsa`, `passwords.txt`, etc.) y los encuentra mediante DFS recursivo. |
| **Acciones destructivas con permiso obligatorio** | `delete`, `edit` y `replicate` siempre requieren confirmación explícita antes de ejecutarse. |
| **Simulación de auto-replicación** | El gusano planta una copia simbólica de sí mismo en cualquier directorio destino. |
| **Autocompletado con TAB** | Completado de rutas con pistas visuales — archivos sensibles resaltados en rojo. |
| **UI de terminal enriquecida** | Tablas, árboles de directorios, paneles y salida en color mediante `rich`. |
| **Seeds reproducibles** | Pasa un entero como argumento al arrancar para generar siempre el mismo filesystem (ideal para demos). |
| **Sin dependencias externas salvo dos librerías** | Solo requiere `prompt_toolkit` y `rich`. |

---

## Instalación

### Requisitos previos

- Python **3.10 o superior**
- `pip`

### Clonar e instalar

```bash
git clone https://github.com/AaronGonzalez03/Worm-CLI.git
cd Worm-CLI
pip install prompt_toolkit rich
```

Opcionalmente, con entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install prompt_toolkit rich
```

---

## Uso

### Arrancar con filesystem aleatorio

```bash
python3 main.py
```

### Arrancar con seed fijo (reproducible — mismo filesystem en cada ejecución)

```bash
python3 main.py 42
```

El gusano aparece en `/home/usuario` dentro del árbol generado aleatoriamente y comienza a narrar su entorno. A partir de ahí, cada decisión es tuya.

---

## Referencia de comandos

| Comando | Descripción | Requiere Permiso |
|---|---|:---:|
| `ls` | Lista el contenido del directorio actual | No |
| `cd <ruta>` | Navega a un directorio (relativa, absoluta o `..`) | No |
| `scan` | Búsqueda DFS recursiva de archivos sensibles desde la posición actual | No |
| `tree` | Árbol visual de directorios desde la posición actual | No |
| `status` | Estado del gusano: ubicación, nodos visitados, archivos borrados/editados, replicaciones, tiempo activo | No |
| `delete <archivo>` | Elimina un nodo de archivo del filesystem falso | **Sí** |
| `edit <archivo>` | Sobreescribe el contenido de un archivo (multilínea, termina con `FIN`) | **Sí** |
| `replicate <dir>` | Planta una copia simbólica del gusano en un directorio destino | **Sí** |
| `help` | Muestra la referencia de comandos | No |
| `exit` | Termina la simulación | No |

### Atajos de teclado

| Atajo | Acción |
|---|---|
| `Tab` | Autocompletar comando o ruta |
| `↑` / `↓` | Navegar por el historial de comandos |
| `Ctrl+C` | Cancelar la línea de entrada actual |
| `Ctrl+D` | Salir de la simulación |

---

## Arquitectura

```
Worm-CLI/
├── filesystem.py   # Modelo de filesystem en memoria + generador de árbol aleatorio
├── worm.py         # Motor del gusano: máquina de estados, lógica de comandos, narración
└── main.py         # Shell interactiva: sesión prompt_toolkit, renderer rich, bucle REPL
```

### Flujo de datos

```
arranque
  └── FileSystem(seed) ──► generación del árbol ──► siembra de archivos sensibles

por comando
  └── PromptSession.prompt()
        └── WormShell._dispatch(entrada)
              ├── WormEngine.cmd_*(args)          ← no destructivo: ejecución inmediata
              └── WormEngine.plan_*(args)         ← destructivo: solo vista previa
                    └── [operador confirma]
                          └── WormEngine.run_*(args) ──► mutación del FileSystem
```

### Decisiones de diseño clave

- **División `plan_` / `run_`**: Los comandos destructivos se separan en una fase de vista previa (sin mutación) y una fase de ejecución. El shell nunca modifica el filesystem sin confirmación explícita del operador.
- **Back-pointer `parent` en `FileNode`**: Permite resolución de rutas en O(profundidad) sin mantener un diccionario de rutas separado.
- **RNG con seed**: El generador usa `random.Random(seed)`, haciendo cada ejecución reproducible cuando se provee un seed.
- **Salida rich fuera de `PromptSession`**: Todos los writes de `rich` ocurren entre iteraciones del REPL, nunca durante una llamada activa a `session.prompt()`, evitando corrupción visual del terminal.

---

## Archivos sensibles simulados

El generador siembra una instancia de cada uno de los siguientes archivos en un directorio aleatorio del árbol falso:

| Nombre de archivo | Tipo simulado |
|---|---|
| `passwords.txt` | Almacén de credenciales en texto plano |
| `.env` | Archivo de variables de entorno con secretos |
| `id_rsa` | Clave privada SSH |
| `token.json` | Par de tokens OAuth de acceso y refresco |
| `secret.key` | Clave HMAC / de cifrado |
| `credentials.json` | Credenciales de proveedor cloud |
| `private_key.pem` | Clave privada EC |
| `database.conf` | Configuración de base de datos con contraseña |

Todo el contenido es **completamente falso** — tokens generados aleatoriamente y valores de relleno. No se usan ni almacenan credenciales reales.

---

## Aviso Legal

> **Esta herramienta está destinada exclusivamente a fines educativos.**
>
> Worm-CLI simula el comportamiento de un gusano sobre un sistema de archivos completamente aislado en memoria. No realiza ninguna operación de I/O real, no establece conexiones de red y no puede afectar a ningún sistema, archivo o proceso real.
>
> Las técnicas demostradas por este simulador — travesía de sistema de archivos, detección de archivos sensibles, auto-replicación — están documentadas en la literatura de ciberseguridad disponible públicamente y se presentan aquí únicamente para ilustrar cómo funcionan dichos mecanismos a nivel conceptual.
>
> **El autor no asume ninguna responsabilidad por el uso indebido de este software, sus conceptos o cualquier obra derivada, sea cual sea la forma en que se produzca dicho uso. Al utilizar esta herramienta, aceptas usarla exclusivamente con fines lícitos, éticos y educativos. Cualquier uso malintencionado es responsabilidad exclusiva de quien lo lleve a cabo.**

---

## Contribuir

Las contribuciones, reportes de errores y solicitudes de nuevas funcionalidades son bienvenidas. Lee [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir un pull request.

```bash
# Haz fork del repo, luego:
git clone https://github.com/TU_USUARIO/Worm-CLI.git
cd Worm-CLI
git checkout -b feature/nombre-de-tu-feature
```

---

## Seguridad

Si descubres un problema de seguridad en este proyecto, sigue el proceso de divulgación responsable descrito en [SECURITY.md](SECURITY.md). No abras un issue público de GitHub para vulnerabilidades de seguridad.

---

## Licencia

Este proyecto está bajo la **Licencia MIT** — consulta el archivo [LICENSE](LICENSE) para más detalles.

---

<div align="center">

Desarrollado con Python · [`prompt_toolkit`](https://github.com/prompt-toolkit/python-prompt-toolkit) · [`rich`](https://github.com/Textualize/rich)

</div>
