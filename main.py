from __future__ import annotations
import sys
from typing import Iterable

from prompt_toolkit import PromptSession, prompt as pt_prompt
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich import box

from filesystem import FileSystem, FileNode
from worm import WormEngine, WormState, CommandResult


_COMMANDS = ["ls", "cd", "scan", "replicate", "delete", "edit", "encrypt", "decrypt", "tree", "status", "help", "exit"]
_PATH_COMMANDS = {"cd", "replicate", "delete", "edit", "encrypt", "decrypt"}

BANNER = r"""
 ██████╗ ██╗   ██╗███████╗ █████╗ ███╗   ██╗ ██████╗
██╔════╝ ██║   ██║██╔════╝██╔══██╗████╗  ██║██╔═══██╗
██║  ███╗██║   ██║███████╗███████║██╔██╗ ██║██║   ██║
██║   ██║██║   ██║╚════██║██╔══██║██║╚██╗██║██║   ██║
╚██████╔╝╚██████╔╝███████║██║  ██║██║ ╚████║╚██████╔╝
 ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝
        Simulador de Gusano IA  |  Uso Educativo
"""


class WormCompleter(Completer):
    def __init__(self, engine: WormEngine):
        self.engine = engine

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        text = document.text_before_cursor
        try:
            import shlex
            parts = shlex.split(text)
            trailing_space = text.endswith(" ")
        except ValueError:
            parts = text.split()
            trailing_space = text.endswith(" ")

        # complete command name
        if not parts or (len(parts) == 1 and not trailing_space):
            fragment = parts[0] if parts else ""
            for cmd in _COMMANDS:
                if cmd.startswith(fragment):
                    yield Completion(cmd, start_position=-len(fragment))
            return

        cmd = parts[0].lower()
        if cmd not in _PATH_COMMANDS:
            return

        # complete path argument
        arg = parts[1] if len(parts) > 1 else ""
        if trailing_space and len(parts) == 1:
            arg = ""
        elif trailing_space:
            return

        node = self.engine.state.current_node
        prefix = ""

        if "/" in arg:
            slash_idx = arg.rfind("/")
            prefix = arg[:slash_idx + 1]
            fragment = arg[slash_idx + 1:]
            if prefix == "/":
                dir_node = self.engine.fs.root
            else:
                resolved = self.engine._resolve(prefix.rstrip("/"))
                dir_node = resolved if resolved and resolved.is_dir else node
        else:
            fragment = arg
            dir_node = node

        for child in dir_node.children.values():
            display = child.name + ("/" if child.is_dir else "")
            if child.name.startswith(fragment):
                style = "fg:ansired bold" if child.is_sensitive else ("fg:ansicyan" if child.is_dir else "")
                completion_text = prefix + child.name + ("/" if child.is_dir else "")
                yield Completion(
                    completion_text,
                    start_position=-len(arg),
                    display=display,
                    style=style,
                )


class RichRenderer:
    def __init__(self):
        self.console = Console(highlight=False)

    def render_welcome(self) -> None:
        self.console.print(f"[bold green]{BANNER}[/bold green]")
        self.console.print(Panel(
            "[bold]Bienvenido al simulador de gusano IA.[/bold]\n\n"
            "Este programa opera sobre un [cyan]sistema de archivos completamente falso[/cyan] en memoria.\n"
            "Ningun archivo real sera modificado. El gusano te pedira permiso antes de cada accion destructiva.\n\n"
            "Escribe [bold yellow]help[/bold yellow] para ver los comandos disponibles. "
            "[bold yellow]Ctrl+D[/bold yellow] o 'exit' para salir.",
            title="[bold yellow]Simulador Educativo de Ciberseguridad[/bold yellow]",
            border_style="yellow",
        ))

    def render_narration(self, text: str) -> None:
        self.console.print(Panel(
            f"[italic]{text}[/italic]",
            title="[dim]Gusano dice[/dim]",
            border_style="bright_black",
            style="dim",
        ))

    def render_error(self, message: str) -> None:
        self.console.print(Panel(f"[bold red]{message}[/bold red]", border_style="red"))

    def render_ls(self, nodes: list[FileNode], path: str) -> None:
        t = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        t.add_column("Tipo", width=6)
        t.add_column("Nombre")
        t.add_column("Tamano", justify="right", width=10)
        t.add_column("Estado", width=12)

        for node in nodes:
            tipo = "[bold blue]DIR [/bold blue]" if node.is_dir else "FILE"
            if node.is_dir:
                nombre = f"[bold blue]{node.name}/[/bold blue]"
                estado = "-"
            elif node.is_encrypted and node.is_sensitive:
                nombre = f"[bold magenta]{node.name}[/bold magenta]"
                estado = "[bold magenta]ENC+SENS[/bold magenta]"
            elif node.is_encrypted:
                nombre = f"[bold magenta]{node.name}[/bold magenta]"
                estado = "[bold magenta]ENCRIPTADO[/bold magenta]"
            elif node.is_sensitive:
                nombre = f"[bold red]{node.name}[/bold red]"
                estado = "[bold red]SENSIBLE[/bold red]"
            else:
                nombre = node.name
                estado = "-"
            size_str = "-" if node.is_dir else f"{node.size}B"
            t.add_row(tipo, nombre, size_str, estado)

        self.console.print(Panel(t, title=f"[cyan]{path}[/cyan]", border_style="cyan"))

    def render_tree(self, root_node: FileNode, fs: FileSystem, max_depth: int = 6) -> None:
        base_path = fs.get_path(root_node)
        label = f"[bold blue]{base_path}[/bold blue]" if root_node.is_dir else root_node.name
        rich_tree = Tree(label)
        self._build_rich_tree(root_node, rich_tree, 0, max_depth)
        self.console.print(Panel(rich_tree, title="[cyan]Arbol de directorios[/cyan]", border_style="cyan"))

    def _build_rich_tree(self, node: FileNode, parent_tree: Tree, depth: int, max_depth: int) -> None:
        if depth >= max_depth:
            return
        for child in sorted(node.children.values(), key=lambda n: (not n.is_dir, n.name)):
            if child.is_dir:
                label = f"[bold blue]{child.name}/[/bold blue]"
            elif child.is_encrypted and child.is_sensitive:
                label = f"[bold magenta]{child.name} [ENC+SENS][/bold magenta]"
            elif child.is_encrypted:
                label = f"[bold magenta]{child.name} [ENC][/bold magenta]"
            elif child.is_sensitive:
                label = f"[bold red]{child.name}[/bold red]"
            else:
                label = child.name
            branch = parent_tree.add(label)
            if child.is_dir:
                self._build_rich_tree(child, branch, depth + 1, max_depth)

    def render_scan_results(self, results: list[tuple[FileNode, str]]) -> None:
        if not results:
            self.console.print(Panel(
                "[green]No se encontraron archivos sensibles en este subarbol.[/green]",
                border_style="green",
            ))
            return
        t = Table(box=box.SIMPLE, show_header=True, header_style="bold red")
        t.add_column("Ruta", style="bold red")
        t.add_column("Tamano", justify="right", width=10)
        for node, path in results:
            t.add_row(path, f"{node.size}B")
        self.console.print(Panel(
            t,
            title=f"[bold red]ARCHIVOS SENSIBLES DETECTADOS ({len(results)})[/bold red]",
            border_style="red",
        ))

    def render_status(self, state: WormState, elapsed: float) -> None:
        t = Table(box=box.SIMPLE, show_header=False)
        t.add_column("Campo", style="bold")
        t.add_column("Valor")

        t.add_row("Ubicacion actual", f"[cyan]{state.current_node.name}[/cyan]")
        t.add_row("Nodos visitados", str(len(state.visited_paths)))
        t.add_row("Archivos eliminados", f"[red]{len(state.deleted_files)}[/red]")
        t.add_row("Archivos modificados", f"[yellow]{len(state.edited_files)}[/yellow]")
        repl = ", ".join(state.replicated_at) if state.replicated_at else "ninguno"
        t.add_row("Replicado en", f"[green]{repl}[/green]")
        t.add_row("Tiempo activo", f"{int(elapsed)}s")

        if state.deleted_files:
            t.add_row("Eliminados (detalle)", "\n".join(state.deleted_files[:5]))
        if state.edited_files:
            t.add_row("Modificados (detalle)", "\n".join(state.edited_files[:5]))

        self.console.print(Panel(t, title="[bold yellow]ESTADO DEL GUSANO[/bold yellow]", border_style="yellow"))

    def render_encrypt_key(self, file_name: str, key: str) -> None:
        self.console.print(Panel(
            f"[bold white on red]  ATENCION: COPIA ESTA CLAVE AHORA — NO SE ALMACENA  [/bold white on red]\n\n"
            f"  Archivo encriptado: [bold yellow]{file_name}[/bold yellow]\n\n"
            f"  Clave de descifrado:\n\n"
            f"  [bold bright_white on dark_green]  {key}  [/bold bright_white on dark_green]\n\n"
            f"  [dim]Para recuperar el archivo: decrypt {file_name}  →  introduce esta clave[/dim]",
            title="[bold red]RANSOMWARE — CLAVE DE DESCIFRADO[/bold red]",
            border_style="red",
        ))

    def render_key_input_prompt(self, file_name: str) -> str:
        self.console.print(Panel(
            f"Introduce la clave de 32 caracteres para desencriptar [bold yellow]{file_name}[/bold yellow]:",
            border_style="magenta",
            title="[bold magenta]DESCIFRADO[/bold magenta]",
        ))
        try:
            key = pt_prompt("  Clave: ")
        except (KeyboardInterrupt, EOFError):
            key = ""
        return key.strip()

    def render_help(self) -> None:
        t = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        t.add_column("Comando", style="bold yellow", width=22)
        t.add_column("Descripcion")
        rows = [
            ("ls", "Lista el contenido del directorio actual"),
            ("cd <dir>", "Mueve el gusano a un directorio (.. para subir)"),
            ("scan", "Busca archivos sensibles desde la posicion actual (recursivo)"),
            ("tree", "Muestra el arbol de directorios desde la posicion actual"),
            ("replicate <dir>", "Planta una copia del gusano en un directorio (pide permiso)"),
            ("delete <archivo>", "Elimina un archivo del sistema simulado (pide permiso)"),
            ("edit <archivo>", "Modifica el contenido de un archivo (pide permiso)"),
            ("encrypt <archivo>", "Encripta un archivo con clave aleatoria de 128 bits (pide permiso)"),
            ("decrypt <archivo>", "Desencripta un archivo — solicita la clave generada al encriptar"),
            ("status", "Muestra el estado actual del gusano"),
            ("help", "Muestra esta ayuda"),
            ("exit", "Termina la simulacion"),
        ]
        for cmd, desc in rows:
            t.add_row(cmd, desc)
        self.console.print(Panel(t, title="[bold cyan]Comandos disponibles[/bold cyan]", border_style="cyan"))

    def render_permission_prompt(self, prompt_text: str) -> str:
        self.console.print(Panel(
            f"[bold yellow]{prompt_text}[/bold yellow]",
            title="[bold red]SOLICITUD DE PERMISO[/bold red]",
            border_style="yellow",
        ))
        try:
            answer = pt_prompt("  Decision [s/n]: ")
        except (KeyboardInterrupt, EOFError):
            answer = "n"
        return answer.strip()

    def render_file_content_prompt(self, name: str) -> str:
        self.console.print(Panel(
            f"Escribe el nuevo contenido para [bold yellow]{name}[/bold yellow].\n"
            "Termina la entrada con una linea que contenga solo [bold]FIN[/bold].",
            border_style="yellow",
        ))
        lines: list[str] = []
        try:
            while True:
                line = pt_prompt("  > ")
                if line.strip().upper() == "FIN":
                    break
                lines.append(line)
        except (KeyboardInterrupt, EOFError):
            pass
        return "\n".join(lines) + "\n" if lines else ""


class WormShell:
    def __init__(self, engine: WormEngine, renderer: RichRenderer):
        self.engine = engine
        self.renderer = renderer
        self.session: PromptSession = self._build_session()

    def _build_session(self) -> PromptSession:
        style = Style.from_dict({
            "completion-menu.completion": "bg:#1e1e2e fg:#cdd6f4",
            "completion-menu.completion.current": "bg:#313244 fg:#cba6f7 bold",
            "scrollbar.background": "bg:#313244",
            "scrollbar.button": "bg:#89b4fa",
        })
        return PromptSession(
            completer=WormCompleter(self.engine),
            complete_while_typing=True,
            history=InMemoryHistory(),
            style=style,
            bottom_toolbar=HTML(
                "<b>ls</b> | <b>cd</b> | <b>scan</b> | <b>replicate</b> | <b>delete</b> | "
                "<b>edit</b> | <b>encrypt</b> | <b>decrypt</b> | <b>tree</b> | <b>status</b> | <b>help</b> | <b>exit</b>"
            ),
            complete_in_thread=True,
        )

    def _build_prompt(self) -> HTML:
        path = self.engine.current_path()
        return HTML(f'<b><style fg="ansigreen">gusano</style></b>:<style fg="ansicyan">{path}</style>$ ')

    def run(self) -> None:
        self.renderer.render_welcome()
        self.renderer.render_narration(
            f"Me activo en '{self.engine.current_path()}'. "
            "Espero tus instrucciones. Empieza con 'ls' para ver que hay aqui."
        )
        while True:
            try:
                raw = self.session.prompt(self._build_prompt)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            raw = raw.strip()
            if not raw:
                continue
            if raw.lower() in ("exit", "quit", "salir"):
                self.renderer.render_narration("Deteniendo simulacion. Hasta la proxima infeccion.")
                break
            self._dispatch(raw)

    def _dispatch(self, raw: str) -> None:
        parts = raw.split(None, 2)
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd == "ls":
            result = self.engine.cmd_ls()
            if result.success:
                self.renderer.render_ls(result.data["nodes"], result.data["path"])
            self.renderer.render_narration(result.narration)

        elif cmd == "cd":
            if not args:
                self.renderer.render_error("Uso: cd <directorio>")
                return
            result = self.engine.cmd_cd(args[0])
            if not result.success:
                self.renderer.render_error(result.narration)
            else:
                self.renderer.render_narration(result.narration)

        elif cmd == "scan":
            result = self.engine.cmd_scan()
            self.renderer.render_scan_results(result.data["results"])
            self.renderer.render_narration(result.narration)

        elif cmd == "tree":
            result = self.engine.cmd_tree()
            self.renderer.render_tree(result.data["root"], self.engine.fs)
            self.renderer.render_narration(result.narration)

        elif cmd == "status":
            result = self.engine.cmd_status()
            self.renderer.render_status(result.data["state"], result.data["elapsed"])
            self.renderer.render_narration(result.narration)

        elif cmd == "delete":
            if not args:
                self.renderer.render_error("Uso: delete <nombre_archivo>")
                return
            plan = self.engine.plan_delete(args[0])
            self.renderer.render_narration(plan.narration)
            if not plan.success:
                return
            answer = self.renderer.render_permission_prompt(plan.permission_prompt)
            if answer.lower() in ("s", "si", "sí", "y", "yes"):
                result = self.engine.run_delete(args[0])
                self.renderer.render_narration(result.narration)
            else:
                self.renderer.render_narration("Accion cancelada por el operador. El archivo permanece intacto.")

        elif cmd == "edit":
            if not args:
                self.renderer.render_error("Uso: edit <nombre_archivo>")
                return
            plan = self.engine.plan_edit(args[0])
            self.renderer.render_narration(plan.narration)
            if not plan.success:
                return
            answer = self.renderer.render_permission_prompt(plan.permission_prompt)
            if answer.lower() in ("s", "si", "sí", "y", "yes"):
                new_content = self.renderer.render_file_content_prompt(args[0])
                if new_content:
                    result = self.engine.run_edit(args[0], new_content)
                    self.renderer.render_narration(result.narration)
                else:
                    self.renderer.render_narration("No se introdujo contenido. Operacion cancelada.")
            else:
                self.renderer.render_narration("Modificacion cancelada. El archivo permanece sin cambios.")

        elif cmd == "replicate":
            if not args:
                self.renderer.render_error("Uso: replicate <directorio_destino>")
                return
            plan = self.engine.plan_replicate(args[0])
            self.renderer.render_narration(plan.narration)
            if not plan.success:
                return
            answer = self.renderer.render_permission_prompt(plan.permission_prompt)
            if answer.lower() in ("s", "si", "sí", "y", "yes"):
                result = self.engine.run_replicate(args[0])
                self.renderer.render_narration(result.narration)
            else:
                self.renderer.render_narration("Replicacion abortada. Permanezco en mi ubicacion actual.")

        elif cmd == "encrypt":
            if not args:
                self.renderer.render_error("Uso: encrypt <nombre_archivo>")
                return
            plan = self.engine.plan_encrypt(args[0])
            self.renderer.render_narration(plan.narration)
            if not plan.success:
                return
            answer = self.renderer.render_permission_prompt(plan.permission_prompt)
            if answer.lower() in ("s", "si", "sí", "y", "yes"):
                result = self.engine.run_encrypt(args[0])
                if result.success:
                    self.renderer.render_encrypt_key(result.data["name"], result.data["key"])
                self.renderer.render_narration(result.narration)
            else:
                self.renderer.render_narration("Encriptacion cancelada. El archivo permanece intacto.")

        elif cmd == "decrypt":
            if not args:
                self.renderer.render_error("Uso: decrypt <nombre_archivo>")
                return
            plan = self.engine.plan_decrypt(args[0])
            self.renderer.render_narration(plan.narration)
            if not plan.success:
                return
            key = self.renderer.render_key_input_prompt(args[0])
            if not key:
                self.renderer.render_narration("No se introdujo ninguna clave. Operacion cancelada.")
                return
            result = self.engine.run_decrypt(args[0], key)
            if not result.success:
                self.renderer.render_error(result.narration)
            else:
                self.renderer.render_narration(result.narration)

        elif cmd == "help":
            self.renderer.render_help()

        else:
            self.renderer.render_error(f"Comando desconocido: '{cmd}'. Escribe 'help' para ver los comandos.")


def main() -> None:
    seed_arg: int | None = None
    if len(sys.argv) > 1:
        try:
            seed_arg = int(sys.argv[1])
        except ValueError:
            pass

    fs = FileSystem(seed=seed_arg)
    engine = WormEngine(fs)
    renderer = RichRenderer()
    shell = WormShell(engine, renderer)
    shell.run()


if __name__ == "__main__":
    main()
