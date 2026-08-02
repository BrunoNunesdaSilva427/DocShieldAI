
from __future__ import annotations

import io
import math
import random
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import img2pdf


@dataclass(frozen=True)
class Preset:
    dpi: int
    amplitude_onda: float   
    freq_onda: float        
    opacidade_textura: int  
    granulado: float        


PRESETS: dict[str, Preset] = {
    "leve":       Preset(dpi=300, amplitude_onda=8, freq_onda=20, opacidade_textura=40, granulado=28),
    "medio":      Preset(dpi=300, amplitude_onda=12, freq_onda=36, opacidade_textura=55, granulado=52),
    "agressivo":  Preset(dpi=300, amplitude_onda=14, freq_onda=48, opacidade_textura=70, granulado=68),
}

EXTENSOES_CONVERSIVEIS = (".docx", ".rtf", ".txt")


def _rasterizar(pdf_bytes: bytes, dpi: int) -> list[Image.Image]:
    pdf = pdfium.PdfDocument(pdf_bytes)
    escala = dpi / 72
    return [pdf[i].render(scale=escala).to_pil().convert("RGB") for i in range(len(pdf))]



def _ondulacao_por_linha(img: Image.Image, amplitude: float, freq: float,
                          rng: random.Random) -> Image.Image:

    arr = np.asarray(img)
    h, w = arr.shape[:2]
    fase = rng.uniform(0, 2 * math.pi)
    saida = np.empty_like(arr)
    fundo = 255
    for y in range(h):
        desloc = int(round(amplitude * math.sin(2 * math.pi * freq * y / h + fase)))
        if desloc == 0:
            saida[y] = arr[y]
        elif desloc > 0:
            saida[y, desloc:] = arr[y, : w - desloc]
            saida[y, :desloc] = fundo
        else:
            desloc = -desloc
            saida[y, : w - desloc] = arr[y, desloc:]
            saida[y, w - desloc:] = fundo
    return Image.fromarray(saida)


def _textura_ondulada(img: Image.Image, opacidade: int, rng: random.Random) -> Image.Image:

    w, h = img.size
    camada = Image.new("L", (w, h), 0)
    desenho = ImageDraw.Draw(camada)
    n_curvas = max(6, (w + h) // 220)
    for _ in range(n_curvas):
        y0 = rng.uniform(-h * 0.2, h * 1.2)
        amp = rng.uniform(h * 0.03, h * 0.09)
        freq = rng.uniform(1.0, 3.0)
        fase = rng.uniform(0, 2 * math.pi)
        largura = rng.randint(2, 4)
        passo = max(2, w // 400)
        pontos = [
            (x, y0 + amp * math.sin(2 * math.pi * freq * x / w + fase) + x * rng.uniform(-0.15, 0.15))
            for x in range(0, w, passo)
        ]
        desenho.line(pontos, fill=opacidade, width=largura)
    camada = camada.filter(ImageFilter.GaussianBlur(1.2))
    cinza = Image.new("RGB", (w, h), (120, 120, 130))
    return Image.composite(cinza, img, camada)


def _granulado(img: Image.Image, desvio: float, rng: random.Random) -> Image.Image:
    if desvio <= 0:
        return img
    arr = np.asarray(img).astype(np.float32)
    seed = rng.randint(0, 2**31 - 1)
    ruido = np.random.default_rng(seed).normal(0, desvio, arr.shape)
    return Image.fromarray(np.clip(arr + ruido, 0, 255).astype(np.uint8))


def proteger_paginas(paginas: list[Image.Image], preset: Preset,
                      semente: Optional[int] = None) -> list[Image.Image]:
    rng = random.Random(semente)
    resultado = []
    for pg in paginas:
        pg = _ondulacao_por_linha(pg, preset.amplitude_onda, preset.freq_onda, rng)
        pg = _textura_ondulada(pg, preset.opacidade_textura, rng)
        pg = _granulado(pg, preset.granulado, rng)
        pg = pg.filter(ImageFilter.SMOOTH)
        resultado.append(pg)
    return resultado




def aplicar_marca_dagua(img: Image.Image, texto: str, fonte_ttf: Optional[Path] = None,
                         opacidade: int = 38, tamanho_fonte: int = 34,
                         rng: Optional[random.Random] = None) -> Image.Image:

    rng = rng or random.Random()
    w, h = img.size
    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def carregar_fonte(tamanho: int) -> ImageFont.ImageFont:
        if fonte_ttf:
            return ImageFont.truetype(str(fonte_ttf), tamanho)
        return ImageFont.load_default(size=tamanho)

    passo_x, passo_y = 260, 150
    for y0 in range(-passo_y, h + passo_y, passo_y):
        for x0 in range(-passo_x, w + passo_x, passo_x):
            x = x0 + rng.randint(-40, 40)
            y = y0 + rng.randint(-30, 30)
            angulo = -28 + rng.uniform(-6, 6)
            escala = rng.uniform(0.9, 1.15)

            bloco = Image.new("RGBA", (400, 100), (0, 0, 0, 0))
            d = ImageDraw.Draw(bloco)
            d.text((10, 10), texto, font=carregar_fonte(int(tamanho_fonte * escala)),
                   fill=(90, 90, 100, opacidade))
            bloco = bloco.rotate(angulo, expand=True, resample=Image.BICUBIC)
            camada.alpha_composite(bloco, dest=(x, y))

    base = img.convert("RGBA")
    return Image.alpha_composite(base, camada).convert("RGB")



def paginas_para_pdf_bytes(paginas: list[Image.Image], dpi: int) -> bytes:
    buffers = []
    for pg in paginas:
        buf = io.BytesIO()
        pg.save(buf, format="JPEG", quality=88)
        buffers.append(buf.getvalue())
    return img2pdf.convert(buffers, dpi=dpi)




def proteger_pdf(pdf_bytes: bytes, nivel: str = "medio", fonte_ttf: Optional[Path] = None,
                  marca_dagua: Optional[str] = None, semente: Optional[int] = None,
                  dpi: Optional[int] = None) -> bytes:

    if nivel not in PRESETS:
        raise ValueError(f"nivel inválido: {nivel!r}. Use um de {list(PRESETS)}")
    preset = PRESETS[nivel]
    if dpi is not None:
        preset = replace(preset, dpi=dpi)

    rng = random.Random(semente)
    paginas = _rasterizar(pdf_bytes, preset.dpi)
    if marca_dagua:
        paginas = [aplicar_marca_dagua(pg, marca_dagua, fonte_ttf, rng=rng) for pg in paginas]
    paginas = proteger_paginas(paginas, preset, semente=rng.randint(0, 2**31 - 1))
    return paginas_para_pdf_bytes(paginas, preset.dpi)


def proteger(caminho_entrada: str | Path, caminho_saida: str | Path, nivel: str = "medio",
             fonte_ttf: Optional[str | Path] = None, marca_dagua: Optional[str] = None,
             semente: Optional[int] = None, dpi: Optional[int] = None) -> None:

    caminho_entrada = Path(caminho_entrada)
    fonte_ttf = Path(fonte_ttf) if fonte_ttf else None
    ext = caminho_entrada.suffix.lower()

    if ext == ".pdf":
        pdf_bytes = caminho_entrada.read_bytes()
    elif ext in EXTENSOES_CONVERSIVEIS:
        from . import conversor
        pdf_bytes = conversor.converter_para_pdf(caminho_entrada, fonte_ttf=fonte_ttf)
    else:
        raise ValueError(
            f"extensão não suportada: {ext} (use .pdf, .docx, .rtf ou .txt)"
        )

    saida_bytes = proteger_pdf(pdf_bytes, nivel=nivel, fonte_ttf=fonte_ttf,
                                marca_dagua=marca_dagua, semente=semente, dpi=dpi)
    Path(caminho_saida).write_bytes(saida_bytes)
