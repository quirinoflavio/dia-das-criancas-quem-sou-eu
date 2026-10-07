"""Interface ImageGenerator (plugável) + adapters Fake e Gemini."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx

GEN_TIMEOUT_SECONDS = 60.0

ADULT_PROMPT = (
    "Generate a realistic photo of this same person as an adult today, "
    "preserving their facial features, ethnicity and expression. Keep it "
    "natural and photorealistic, head-and-shoulders portrait, neutral "
    "background. Do not exaggerate aging."
)


class ImageGenError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass
class GeneratedImage:
    data: bytes
    mime: str


@runtime_checkable
class ImageGenerator(Protocol):
    async def generate_adult(self, child_image: bytes, mime: str) -> GeneratedImage:
        ...


class FakeImageGenerator:
    """Adapter de dev/testes: devolve a própria imagem (sem custo, determinístico)."""

    async def generate_adult(self, child_image: bytes, mime: str) -> GeneratedImage:
        return GeneratedImage(data=child_image, mime=mime)


class GeminiImageGenerator:
    """Adapter real para a API Gemini de geração/edição de imagem."""

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ImageGenError("IMAGE_API_KEY ausente para o provedor gemini.")
        self._api_key = api_key
        self._model = model

    async def generate_adult(self, child_image: bytes, mime: str) -> GeneratedImage:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": ADULT_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": base64.b64encode(child_image).decode(),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"responseModalities": ["IMAGE"]},
        }
        try:
            async with httpx.AsyncClient(timeout=GEN_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    url,
                    params={"key": self._api_key},
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()
        except httpx.TimeoutException as exc:
            raise ImageGenError("Tempo esgotado ao gerar a imagem.") from exc
        except httpx.HTTPError as exc:
            raise ImageGenError(f"Falha na API de imagem: {exc}") from exc

        # Procura a primeira parte com inline_data de imagem.
        try:
            parts = body["candidates"][0]["content"]["parts"]
            for part in parts:
                inline = part.get("inline_data") or part.get("inlineData")
                if inline and str(inline.get("mime_type", inline.get("mimeType", ""))).startswith("image/"):
                    data = base64.b64decode(inline["data"])
                    out_mime = inline.get("mime_type") or inline.get("mimeType")
                    return GeneratedImage(data=data, mime=out_mime)
        except (KeyError, IndexError, ValueError) as exc:
            raise ImageGenError("Resposta da API sem imagem.") from exc
        raise ImageGenError("Resposta da API sem imagem.")


def build_generator(provider: str, api_key: str, model: str) -> ImageGenerator:
    provider = (provider or "fake").lower()
    if provider == "fake":
        return FakeImageGenerator()
    if provider == "gemini":
        return GeminiImageGenerator(api_key=api_key, model=model)
    raise ImageGenError(f"Provedor de imagem desconhecido: {provider}")
