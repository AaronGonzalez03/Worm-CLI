from __future__ import annotations
import base64
import random
import secrets
import time
from dataclasses import dataclass, field

_MAGIC_PREFIX = "WORMENC1:"


def encrypt_content(content: str, key: str) -> str:
    key_bytes = key.encode()
    plain = (_MAGIC_PREFIX + content).encode()
    cipher = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(plain))
    return base64.b64encode(cipher).decode()


def decrypt_content(encrypted_b64: str, key: str) -> tuple[bool, str]:
    try:
        key_bytes = key.encode()
        cipher = base64.b64decode(encrypted_b64)
        plain = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(cipher))
        result = plain.decode()
        if result.startswith(_MAGIC_PREFIX):
            return True, result[len(_MAGIC_PREFIX):]
        return False, "Clave incorrecta — el archivo permanece encriptado."
    except Exception:
        return False, "Error al desencriptar — clave invalida o datos corruptos."


def generate_key() -> str:
    return secrets.token_hex(16)


@dataclass
class FileNode:
    name: str
    is_dir: bool
    size: int
    is_sensitive: bool
    content: str
    children: dict[str, "FileNode"] = field(default_factory=dict)
    parent: "FileNode | None" = field(default=None, repr=False)
    is_encrypted: bool = False


_SENSITIVE_FILES = {
    "passwords.txt": "# Credenciales del sistema\nadmin:S3cur3P@ss!\nroot:toor123\ndb_user:mysql_pass_2024\n",
    ".env": "DB_HOST=localhost\nDB_PASS=ultra_secret_db_pass\nSECRET_KEY=xK9mP2qR7vL4nJ8\nAPI_TOKEN=eyJhbGciOiJIUzI1NiJ9.fake\n",
    "id_rsa": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA2a2rwplBQLF29amygykEMmYz0+Vy\nVERYFAKEKEYDATAHERE1234567890abcdefghijk\n-----END RSA PRIVATE KEY-----\n",
    "token.json": '{\n  "access_token": "ya29.FakeGoogleToken_ABCDEFGHIJK",\n  "refresh_token": "1//FakeRefresh0987654321",\n  "expires_in": 3599\n}\n',
    "secret.key": "HMAC_SECRET=7f3d9a1b2c4e6f8a0b2d4e6f8a0b2d4e\nENCRYPTION_KEY=AES256-FAKE-KEY-1234567890abcdef\n",
    "credentials.json": '{\n  "client_id": "fake-client-123.apps.googleusercontent.com",\n  "client_secret": "GOCSPX-FakeSecret_XYZ789",\n  "type": "authorized_user"\n}\n',
    "private_key.pem": "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIFakeECPrivateKeyDataHere1234\nABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\n-----END EC PRIVATE KEY-----\n",
    "database.conf": "[database]\nhost = 10.0.0.5\nport = 5432\nname = produccion_db\nuser = admin\npassword = Pr0d_DB_P@ss!\n",
}

_DIR_NAMES = {
    "system": ["bin", "lib", "lib64", "share", "include", "src", "build", "dist"],
    "user": ["proyectos", "backup", "scripts", "keys", "tokens", "cache", "data", "archivos"],
    "app": ["logs", "uploads", "static", "templates", "migrations", "tests", "api", "models"],
    "hidden": [".config", ".local", ".cache", ".gnupg", ".bash_history"],
}

_LOG_LINES = [
    "2024-03-{d:02d} {h:02d}:{m:02d}:{s:02d} INFO  conexión aceptada desde 192.168.{a}.{b}",
    "2024-03-{d:02d} {h:02d}:{m:02d}:{s:02d} WARN  intento de acceso fallido usuario=root",
    "2024-03-{d:02d} {h:02d}:{m:02d}:{s:02d} ERROR disco al 94% de capacidad",
    "2024-03-{d:02d} {h:02d}:{m:02d}:{s:02d} INFO  proceso iniciado pid={pid}",
]

_NORMAL_FILES: dict[str, tuple[str, list[str]]] = {
    "logs": ("log", ["access.log", "error.log", "auth.log", "syslog", "debug.log", "app.log"]),
    "scripts": ("sh", ["setup.sh", "deploy.sh", "backup.sh", "cleanup.py", "run.sh", "install.sh"]),
    "docs": ("doc", ["README.md", "NOTES.txt", "TODO.md", "changelog.txt", "INSTALL.md"]),
    "configs": ("cfg", ["nginx.conf", "settings.json", "config.yml", "app.conf", "hosts", "fstab"]),
}
_NORMAL_WEIGHTS = [3, 2, 2, 3]


def _fake_log_content(rng: random.Random) -> str:
    lines = []
    for _ in range(rng.randint(3, 8)):
        tpl = rng.choice(_LOG_LINES)
        lines.append(tpl.format(
            d=rng.randint(1, 28), h=rng.randint(0, 23),
            m=rng.randint(0, 59), s=rng.randint(0, 59),
            a=rng.randint(1, 254), b=rng.randint(1, 254),
            pid=rng.randint(1000, 65000),
        ))
    return "\n".join(lines) + "\n"


def _fake_script_content(rng: random.Random) -> str:
    return (
        "#!/bin/bash\n"
        "# Script de mantenimiento automatico\n"
        f"# Generado: 2024-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}\n"
        f"echo 'Iniciando proceso {rng.randint(100,999)}...'\n"
        f"cd /opt/app && python3 manage.py {rng.choice(['migrate','collectstatic','runserver'])}\n"
    )


def _fake_doc_content() -> str:
    return (
        "# Documentacion del proyecto\n\n"
        "Este archivo contiene notas de configuracion y despliegue.\n"
        "Consultar con el equipo antes de modificar parametros de produccion.\n\n"
        "## Pendientes\n- Revisar backups automaticos\n- Actualizar dependencias\n"
    )


def _fake_config_content(rng: random.Random) -> str:
    pairs = [
        f"host = 127.0.0.{rng.randint(1,10)}",
        f"port = {rng.choice([80,443,8080,3000,5432,6379])}",
        f"workers = {rng.randint(2,16)}",
        f"timeout = {rng.randint(30,120)}",
        f"debug = {rng.choice(['true','false','0','1'])}",
        f"log_level = {rng.choice(['info','warn','error','debug'])}",
    ]
    return "\n".join(pairs) + "\n"


def _make_file_content(name: str, rng: random.Random) -> str:
    low = name.lower()
    if low.endswith(".log"):
        return _fake_log_content(rng)
    if low.endswith(".sh") or low.endswith(".py"):
        return _fake_script_content(rng)
    if low.endswith(".md") or low.endswith(".txt"):
        return _fake_doc_content()
    return _fake_config_content(rng)


class FileSystem:
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed if seed is not None else int(time.time()))
        self.root = self._build_skeleton()
        self._seed_sensitive_files()
        self._fill_normal_files(self.root, depth=0)

    # --- Tree construction ---

    def _make_dir(self, name: str, parent: FileNode | None = None) -> FileNode:
        return FileNode(name=name, is_dir=True, size=0, is_sensitive=False, content="", parent=parent)

    def _make_file(self, name: str, content: str, is_sensitive: bool, parent: FileNode | None = None) -> FileNode:
        return FileNode(
            name=name, is_dir=False,
            size=len(content.encode()),
            is_sensitive=is_sensitive,
            content=content,
            parent=parent,
        )

    def _attach(self, parent: FileNode, child: FileNode) -> None:
        child.parent = parent
        parent.children[child.name] = child

    def _build_skeleton(self) -> FileNode:
        root = self._make_dir("/")

        def mkd(parent: FileNode, name: str) -> FileNode:
            node = self._make_dir(name)
            self._attach(parent, node)
            return node

        home = mkd(root, "home")
        usuario = mkd(home, "usuario")
        mkd(usuario, "Documentos")
        mkd(usuario, "Descargas")
        ssh = mkd(usuario, ".ssh")
        aws = mkd(usuario, ".aws")

        etc = mkd(root, "etc")
        mkd(etc, "nginx")

        var = mkd(root, "var")
        vlog = mkd(var, "log")
        mkd(vlog, "nginx")

        mkd(root, "tmp")

        opt = mkd(root, "opt")
        app = mkd(opt, "app")
        mkd(app, "config")

        # random extra dirs
        self._expand_dir(usuario, depth=2)
        self._expand_dir(etc, depth=2)
        self._expand_dir(app, depth=2)
        self._expand_dir(root, depth=1)

        # plant .aws/credentials placeholder dir so sensitive seeder can find it
        _ = aws  # used via path resolution
        _ = ssh

        return root

    def _expand_dir(self, node: FileNode, depth: int) -> None:
        if depth >= 5:
            return
        p = max(0.0, 0.55 - 0.12 * depth)
        if self._rng.random() > p:
            return
        count = self._rng.randint(0, 3)
        all_names = [n for names in _DIR_NAMES.values() for n in names]
        existing = set(node.children.keys())
        candidates = [n for n in all_names if n not in existing]
        chosen = self._rng.sample(candidates, min(count, len(candidates)))
        for name in chosen:
            child = self._make_dir(name)
            self._attach(node, child)
            self._expand_dir(child, depth + 1)

    def _all_dirs(self, node: FileNode | None = None) -> list[FileNode]:
        node = node or self.root
        result: list[FileNode] = []
        stack = [node]
        while stack:
            n = stack.pop()
            if n.is_dir:
                result.append(n)
                stack.extend(n.children.values())
        return result

    def _seed_sensitive_files(self) -> None:
        all_dirs = self._all_dirs()
        aws_node = self.get_node("/home/usuario/.aws")
        ssh_node = self.get_node("/home/usuario/.ssh")

        for fname, content in _SENSITIVE_FILES.items():
            if fname == "credentials.json" and aws_node:
                parent = aws_node
            elif fname == "id_rsa" and ssh_node:
                parent = ssh_node
            else:
                parent = self._rng.choice(all_dirs)
            if fname not in parent.children:
                node = self._make_file(fname, content, is_sensitive=True)
                self._attach(parent, node)

    def _fill_normal_files(self, node: FileNode, depth: int) -> None:
        if not node.is_dir:
            return
        count = self._rng.randint(0, 4)
        categories = list(_NORMAL_FILES.keys())
        chosen_cats = self._rng.choices(categories, weights=_NORMAL_WEIGHTS, k=count)
        for cat in chosen_cats:
            _, names = _NORMAL_FILES[cat]
            fname = self._rng.choice(names)
            if fname in node.children:
                continue
            content = _make_file_content(fname, self._rng)
            fnode = self._make_file(fname, content, is_sensitive=False)
            self._attach(node, fnode)
        for child in list(node.children.values()):
            self._fill_normal_files(child, depth + 1)

    # --- Public API ---

    def get_path(self, node: FileNode) -> str:
        if node.parent is None:
            return "/"
        parts: list[str] = []
        cur: FileNode | None = node
        while cur is not None and cur.parent is not None:
            parts.append(cur.name)
            cur = cur.parent
        return "/" + "/".join(reversed(parts))

    def get_node(self, path: str) -> FileNode | None:
        if not path.startswith("/"):
            return None
        parts = [p for p in path.split("/") if p]
        cur = self.root
        for part in parts:
            if not cur.is_dir or part not in cur.children:
                return None
            cur = cur.children[part]
        return cur

    def list_children(self, node: FileNode) -> list[FileNode]:
        dirs = sorted([c for c in node.children.values() if c.is_dir], key=lambda n: n.name)
        files = sorted([c for c in node.children.values() if not c.is_dir], key=lambda n: n.name)
        return dirs + files

    def add_node(self, parent: FileNode, node: FileNode) -> None:
        if node.name in parent.children:
            raise ValueError(f"Ya existe '{node.name}' en este directorio")
        self._attach(parent, node)

    def remove_node(self, node: FileNode) -> None:
        if node.parent is None:
            raise ValueError("No se puede eliminar el directorio raiz")
        del node.parent.children[node.name]
        node.parent = None

    def edit_file(self, node: FileNode, new_content: str) -> None:
        node.content = new_content
        node.size = len(new_content.encode())

    def scan_sensitive(self, from_node: FileNode) -> list[tuple[FileNode, str]]:
        results: list[tuple[FileNode, str]] = []
        stack = [from_node]
        while stack:
            n = stack.pop()
            if n.is_sensitive and not n.is_dir:
                results.append((n, self.get_path(n)))
            if n.is_dir:
                stack.extend(n.children.values())
        return sorted(results, key=lambda t: t[1])
