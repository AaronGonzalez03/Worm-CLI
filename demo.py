"""
Automated demo script for asciinema recording.
Simulates a full Worm-CLI session with realistic typing delays.
"""
import sys
import time

from rich.console import Console
from rich.panel import Panel

from filesystem import FileSystem
from worm import WormEngine
from main import RichRenderer

console = Console(highlight=False)

SEED = 7


def slow_print(text: str, delay: float = 0.045) -> None:
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
    sys.stdout.flush()


def prompt_line(path: str, cmd: str, pause_before: float = 0.6) -> None:
    time.sleep(pause_before)
    prefix = f"\033[1;32mgusano\033[0m:\033[1;36m{path}\033[0m$ "
    sys.stdout.write(prefix)
    sys.stdout.flush()
    time.sleep(0.3)
    slow_print(cmd, delay=0.055)
    time.sleep(0.25)


def confirm_line(answer: str = "s") -> None:
    time.sleep(0.5)
    sys.stdout.write("  Decision [s/n]: ")
    sys.stdout.flush()
    time.sleep(0.4)
    slow_print(answer, delay=0.1)
    time.sleep(0.2)


def fin_line() -> None:
    time.sleep(0.4)
    sys.stdout.write("  > ")
    sys.stdout.flush()
    time.sleep(0.3)
    slow_print("Este archivo ha sido comprometido.", delay=0.05)
    time.sleep(0.3)
    sys.stdout.write("  > ")
    sys.stdout.flush()
    time.sleep(0.2)
    slow_print("FIN", delay=0.12)
    time.sleep(0.2)


def main() -> None:
    fs = FileSystem(seed=SEED)
    engine = WormEngine(fs)
    renderer = RichRenderer()

    # --- Welcome ---
    renderer.render_welcome()
    time.sleep(0.5)
    renderer.render_narration(
        f"Me activo en '{engine.current_path()}'. "
        "Espero tus instrucciones. Empieza con 'ls' para ver que hay aqui."
    )

    # --- ls ---
    prompt_line(engine.current_path(), "ls")
    result = engine.cmd_ls()
    renderer.render_ls(result.data["nodes"], result.data["path"])
    renderer.render_narration(result.narration)

    # --- scan ---
    prompt_line(engine.current_path(), "scan")
    result = engine.cmd_scan()
    renderer.render_scan_results(result.data["results"])
    renderer.render_narration(result.narration)

    # --- cd .ssh ---
    prompt_line(engine.current_path(), "cd .ssh")
    result = engine.cmd_cd(".ssh")
    renderer.render_narration(result.narration)

    # --- ls in .ssh ---
    prompt_line(engine.current_path(), "ls")
    result = engine.cmd_ls()
    renderer.render_ls(result.data["nodes"], result.data["path"])
    renderer.render_narration(result.narration)

    # --- delete id_rsa ---
    prompt_line(engine.current_path(), "delete id_rsa")
    plan = engine.plan_delete("id_rsa")
    renderer.render_narration(plan.narration)
    console.print(Panel(
        f"[bold yellow]{plan.permission_prompt}[/bold yellow]",
        title="[bold red]SOLICITUD DE PERMISO[/bold red]",
        border_style="yellow",
    ))
    confirm_line("s")
    run_result = engine.run_delete("id_rsa")
    renderer.render_narration(run_result.narration)

    # --- cd back to usuario ---
    prompt_line(engine.current_path(), "cd /home/usuario")
    result = engine.cmd_cd("/home/usuario")
    renderer.render_narration(result.narration)

    # --- edit .env if it exists, otherwise pick first sensitive file ---
    target_file = None
    for child in engine.state.current_node.children.values():
        if child.is_sensitive and not child.is_dir:
            target_file = child.name
            break
    if not target_file:
        # find any file
        for child in engine.state.current_node.children.values():
            if not child.is_dir:
                target_file = child.name
                break

    if target_file:
        prompt_line(engine.current_path(), f"edit {target_file}")
        plan = engine.plan_edit(target_file)
        renderer.render_narration(plan.narration)
        console.print(Panel(
            f"[bold yellow]{plan.permission_prompt}[/bold yellow]",
            title="[bold red]SOLICITUD DE PERMISO[/bold red]",
            border_style="yellow",
        ))
        confirm_line("s")
        console.print(Panel(
            f"Escribe el nuevo contenido para [bold yellow]{target_file}[/bold yellow].\n"
            "Termina la entrada con una linea que contenga solo [bold]FIN[/bold].",
            border_style="yellow",
        ))
        fin_line()
        run_result = engine.run_edit(target_file, "Este archivo ha sido comprometido.\n")
        renderer.render_narration(run_result.narration)

    # --- encrypt single file ---
    enc_target = None
    for child in engine.state.current_node.children.values():
        if not child.is_dir:
            enc_target = child.name
            break
    if enc_target:
        prompt_line(engine.current_path(), f"encrypt {enc_target}")
        plan = engine.plan_encrypt(enc_target)
        renderer.render_narration(plan.narration)
        console.print(Panel(
            f"[bold yellow]{plan.permission_prompt}[/bold yellow]",
            title="[bold red]SOLICITUD DE PERMISO[/bold red]",
            border_style="yellow",
        ))
        confirm_line("s")
        enc_result = engine.run_encrypt(enc_target)
        if enc_result.success and not enc_result.data.get("is_dir"):
            renderer.render_encrypt_key(enc_result.data["name"], enc_result.data["key"])
            saved_key = enc_result.data["key"]
        else:
            saved_key = None
        renderer.render_narration(enc_result.narration)

        # --- re-encrypt (double encryption) ---
        time.sleep(0.4)
        prompt_line(engine.current_path(), f"encrypt {enc_target}")
        plan2 = engine.plan_encrypt(enc_target)
        renderer.render_narration(plan2.narration)
        console.print(Panel(
            f"[bold yellow]{plan2.permission_prompt}[/bold yellow]",
            title="[bold red]SOLICITUD DE PERMISO[/bold red]",
            border_style="yellow",
        ))
        confirm_line("s")
        enc_result2 = engine.run_encrypt(enc_target)
        if enc_result2.success:
            renderer.render_encrypt_key(enc_result2.data["name"], enc_result2.data["key"])
            saved_key = enc_result2.data["key"]
        renderer.render_narration(enc_result2.narration)

        # --- decrypt ---
        if saved_key:
            time.sleep(0.4)
            prompt_line(engine.current_path(), f"decrypt {enc_target}")
            plan_d = engine.plan_decrypt(enc_target)
            renderer.render_narration(plan_d.narration)
            console.print(Panel(
                f"Introduce la clave de 32 caracteres para desencriptar [bold yellow]{enc_target}[/bold yellow]:",
                border_style="magenta",
                title="[bold magenta]DESCIFRADO[/bold magenta]",
            ))
            time.sleep(0.5)
            sys.stdout.write("  Clave: ")
            sys.stdout.flush()
            time.sleep(0.3)
            slow_print(saved_key, delay=0.03)
            time.sleep(0.2)
            dec_result = engine.run_decrypt(enc_target, saved_key)
            renderer.render_narration(dec_result.narration)

    # --- encrypt directory ---
    prompt_line(engine.current_path(), "encrypt Documentos")
    engine.cmd_cd("/home/usuario")
    plan_dir = engine.plan_encrypt("Documentos")
    renderer.render_narration(plan_dir.narration)
    console.print(Panel(
        f"[bold yellow]{plan_dir.permission_prompt}[/bold yellow]",
        title="[bold red]SOLICITUD DE PERMISO[/bold red]",
        border_style="yellow",
    ))
    confirm_line("s")
    dir_result = engine.run_encrypt("Documentos")
    if dir_result.success:
        renderer.render_encrypt_keys_dir(dir_result.data["entries"])
    renderer.render_narration(dir_result.narration)

    # --- replicate /tmp ---
    prompt_line(engine.current_path(), "replicate /tmp")
    plan = engine.plan_replicate("/tmp")
    renderer.render_narration(plan.narration)
    console.print(Panel(
        f"[bold yellow]{plan.permission_prompt}[/bold yellow]",
        title="[bold red]SOLICITUD DE PERMISO[/bold red]",
        border_style="yellow",
    ))
    confirm_line("s")
    run_result = engine.run_replicate("/tmp")
    renderer.render_narration(run_result.narration)

    # --- tree ---
    prompt_line(engine.current_path(), "tree")
    result = engine.cmd_tree()
    renderer.render_tree(result.data["root"], engine.fs)
    renderer.render_narration(result.narration)

    # --- privesc ---
    prompt_line(engine.current_path(), "privesc", pause_before=0.8)
    result = engine.cmd_privesc()
    renderer.render_privesc_results(result.data["findings"])
    renderer.render_narration(result.narration)

    # --- status ---
    prompt_line(engine.current_path(), "status")
    result = engine.cmd_status()
    renderer.render_status(result.data["state"], result.data["elapsed"])
    renderer.render_narration(result.narration)

    # --- exit ---
    prompt_line(engine.current_path(), "exit", pause_before=0.8)
    time.sleep(0.3)
    renderer.render_narration("Deteniendo simulacion. Hasta la proxima infeccion.")
    time.sleep(1.0)


if __name__ == "__main__":
    main()
