"""ImageStore: valida, normaliza (remove EXIF) e armazena imagens em disco."""
from __future__ import annotations

import io
import secrets
import shutil
from pathlib import Path

from PIL import Image

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_DIMENSION = 1600  # px no maior lado


class ImageError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ImageStore:
    def __init__(self, images_path: Path):
        self._root = images_path

    def _room_dir(self, room_code: str) -> Path:
        d = self._root / room_code
        d.mkdir(parents=True, exist_ok=True)
        return d

    def normalize(self, raw: bytes, declared_mime: str) -> tuple[bytes, str]:
        """Reorienta por EXIF, reencoda removendo metadados, limita dimensão.
        Retorna (bytes_normalizados, mime_final). Levanta ImageError se inválido."""
        if declared_mime not in ALLOWED_MIME:
            raise ImageError("bad_mime", "Formato não suportado (use JPEG, PNG ou WebP).")
        try:
            img = Image.open(io.BytesIO(raw))
            img.load()
        except Exception as exc:  # noqa: BLE001
            raise ImageError("not_image", "Arquivo não é uma imagem válida.") from exc

        # Aplica orientação EXIF e descarta todo o resto dos metadados.
        from PIL import ImageOps

        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        # Limita dimensão mantendo proporção.
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

        out = io.BytesIO()
        # Normaliza para JPEG (sem alpha) ou PNG (com alpha).
        if img.mode == "RGBA":
            img.save(out, format="PNG", optimize=True)
            mime = "image/png"
        else:
            img.save(out, format="JPEG", quality=88, optimize=True)
            mime = "image/jpeg"
        return out.getvalue(), mime

    def save(self, room_code: str, data: bytes, mime: str) -> str:
        ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[mime]
        image_id = f"{secrets.token_urlsafe(10)}.{ext}"
        path = self._room_dir(room_code) / image_id
        path.write_bytes(data)
        return image_id

    def read(self, room_code: str, image_id: str) -> bytes | None:
        # image_id é opaco e gerado por nós; valida que fica dentro do dir.
        path = (self._room_dir(room_code) / image_id).resolve()
        root = self._room_dir(room_code).resolve()
        if root not in path.parents:
            return None
        if not path.is_file():
            return None
        return path.read_bytes()

    def delete_room(self, room_code: str) -> None:
        d = self._root / room_code
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
