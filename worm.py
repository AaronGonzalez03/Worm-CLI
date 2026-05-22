from __future__ import annotations
import time
from dataclasses import dataclass, field
from filesystem import FileSystem, FileNode, encrypt_content, decrypt_content, generate_key


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
            return CommandResult(success=False, data={},
                                 narration=f"'{name}' es un directorio. Solo puedo encriptar archivos.",
                                 action_tag="encrypt")
        if node.is_encrypted:
            return CommandResult(success=False, data={},
                                 narration=f"'{name}' ya esta encriptado. Usa 'decrypt' con la clave original.",
                                 action_tag="encrypt")
        sensitive_label = " [SENSIBLE]" if node.is_sensitive else ""
        narr = (
            f"Tengo en la mira '{name}'{sensitive_label} ({node.size} bytes). "
            f"Voy a encriptar su contenido con una clave de 128 bits generada aleatoriamente. "
            f"La clave se mostrara UNA SOLA VEZ — si la pierdes, el archivo no puede recuperarse."
        )
        return CommandResult(
            success=True,
            data={"name": name, "node": node},
            narration=narr,
            needs_permission=True,
            permission_prompt=f"Encriptar '{name}'{sensitive_label}? La clave solo se muestra una vez. [s/n]",
            action_tag="encrypt",
        )

    def run_encrypt(self, name: str) -> CommandResult:
        node = self._resolve(name)
        if node is None or node.is_dir or node.is_encrypted:
            return CommandResult(success=False, data={},
                                 narration="Archivo no encontrado o ya encriptado.", action_tag="encrypt")
        key = generate_key()
        node.content = encrypt_content(node.content, key)
        node.is_encrypted = True
        node.size = len(node.content.encode())
        path = self.fs.get_path(node)
        narr = (
            f"Archivo '{name}' encriptado exitosamente. "
            f"Contenido reemplazado por {node.size} bytes de datos cifrados. "
            f"Sin la clave correcta, el contenido es irrecuperable."
        )
        return CommandResult(
            success=True,
            data={"name": name, "path": path, "key": key},
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
