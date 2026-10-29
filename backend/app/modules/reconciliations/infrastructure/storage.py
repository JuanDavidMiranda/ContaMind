import hashlib
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.errors import AppError


def save_private_file(reconciliation_id: uuid.UUID, source: str, filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    root = get_settings().resolved_storage_dir()
    directory = root / "reconciliations" / str(reconciliation_id)
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{source}-{uuid.uuid4().hex}{extension}"
    path = directory / stored_name
    path.write_bytes(content)
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve_private_file(relative_path: str) -> Path:
    root = get_settings().resolved_storage_dir().resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise AppError("invalid_path", "La referencia del archivo no es válida.", 400)
    if not candidate.is_file():
        raise AppError("file_missing", "El archivo guardado no está disponible.", 404)
    return candidate


def delete_private_file(relative_path: str | None) -> None:
    if not relative_path:
        return
    try:
        path = resolve_private_file(relative_path)
    except AppError:
        return
    path.unlink(missing_ok=True)


def content_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
