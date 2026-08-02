
from __future__ import annotations

import os
import platform
import subprocess
import threading
from pathlib import Path
from typing import Optional

from .extrator import ExtratorTexto


class LeitorNarrado:
    def __init__(self, caminho_pdf_saida: str | Path, caminho_entrada_original: str | Path,
                 taxa_fala: int = 175, voz: Optional[str] = None):
        self.caminho_pdf_saida = Path(caminho_pdf_saida)
        self.paragrafos = ExtratorTexto.extrair(caminho_entrada_original)
        self.taxa_fala = taxa_fala
        self.voz = voz
        self._motor = None

    def _abrir_pdf(self) -> None:
        sistema = platform.system()
        if sistema == "Windows":
            os.startfile(str(self.caminho_pdf_saida))  # noqa: S606
        elif sistema == "Darwin":
            subprocess.Popen(["open", str(self.caminho_pdf_saida)])
        else:
            subprocess.Popen(["xdg-open", str(self.caminho_pdf_saida)])

    def _preparar_motor(self):
        import pyttsx3
        motor = pyttsx3.init()
        motor.setProperty("rate", self.taxa_fala)
        if self.voz:
            for v in motor.getProperty("voices"):
                if self.voz.lower() in (v.name or "").lower() or self.voz.lower() in (v.id or "").lower():
                    motor.setProperty("voice", v.id)
                    break
        return motor

    def narrar(self, bloqueante: bool = True) -> None:

        if not self.paragrafos:
            raise RuntimeError("nenhum texto extraído da entrada original pra narrar")

        self._abrir_pdf()
        self._motor = self._preparar_motor()


        texto_completo = ". ".join(self.paragrafos)

        def _falar():
            self._motor.say(texto_completo)
            self._motor.runAndWait()

        if bloqueante:
            _falar()
        else:
            threading.Thread(target=_falar, daemon=True).start()

    def parar(self) -> None:
        if self._motor is not None:
            self._motor.stop()
