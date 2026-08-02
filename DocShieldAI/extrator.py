
from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

from . import conversor


class ExtratorTexto:


    @staticmethod
    def extrair(caminho_entrada: str | Path) -> list[str]:
        caminho_entrada = Path(caminho_entrada)
        ext = caminho_entrada.suffix.lower()

        if ext == ".pdf":
            return ExtratorTexto._extrair_pdf(caminho_entrada)
        if ext == ".docx":
            blocos, _, _ = conversor._ler_docx(caminho_entrada)
            return [t for t, _ in blocos if t.strip()]
        if ext == ".rtf":
            texto = conversor._rtf_para_texto(caminho_entrada)
            return [l for l in texto.splitlines() if l.strip()]
        if ext == ".txt":
            texto = caminho_entrada.read_text(encoding="utf-8", errors="ignore")
            return [l for l in texto.splitlines() if l.strip()]

        raise ValueError(f"extensão não suportada pra extração: {ext}")

    @staticmethod
    def _extrair_pdf(caminho: Path) -> list[str]:
        doc = pdfium.PdfDocument(str(caminho))
        paragrafos = []
        for i in range(len(doc)):
            pagina = doc[i]
            texto = pagina.get_textpage().get_text_range()
            paragrafos.extend(l for l in texto.splitlines() if l.strip())
        return paragrafos
