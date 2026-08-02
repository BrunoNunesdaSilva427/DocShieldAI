import argparse
import sys

from .nucleo import PRESETS, proteger


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m DocShieldAI.cli",
        description=(
            "DocShieldAI - aplica a proteção anti-OCR (ondulação + textura + "
            "granulado) sobre um PDF, ou converte .docx/.rtf/.txt pra PDF "
            "primeiro. Aceita trocar a fonte por qualquer .ttf e sobrepor "
            "uma marca d'água em mosaico."
        ),
    )
    parser.add_argument("entrada", help="arquivo .pdf, .docx, .rtf ou .txt")
    parser.add_argument("saida", help="PDF de saída (protegido)")
    parser.add_argument("--nivel", choices=list(PRESETS), default="medio")
    parser.add_argument("--fonte", default=None,
                         help="caminho de um .ttf pra trocar a fonte (ex.: fontes/alarm_clock.ttf); "
                              "só se aplica a entrada .docx/.rtf/.txt, mas também é usada na marca d'água")
    parser.add_argument("--marca-dagua", default=None,
                         help="texto a repetir em mosaico sobre as páginas (ex.: 'USO PESSOAL')")
    parser.add_argument("--semente", type=int, default=None, help="semente aleatória (reprodutibilidade)")
    parser.add_argument("--dpi", type=int, default=None, help="sobrescreve o DPI do preset escolhido")
    parser.add_argument("--leitor", action="store_true",
                         help="após gerar, abre o PDF de saída e narra o texto da entrada original "
                              "(acessibilidade — requer pyttsx3)")
    parser.add_argument("--voz", default=None,
                         help="nome/id parcial da voz do sistema a usar com --leitor (ex.: 'Maria')")
    parser.add_argument("--taxa-fala", type=int, default=175,
                         help="velocidade da narração em palavras/min, usado com --leitor (padrão: 175)")
    args = parser.parse_args(argv)

    proteger(
        args.entrada,
        args.saida,
        nivel=args.nivel,
        fonte_ttf=args.fonte,
        marca_dagua=args.marca_dagua,
        semente=args.semente,
        dpi=args.dpi,
    )
    print(f"OK: '{args.saida}' gerado (nível={args.nivel}).")

    if args.leitor:
        from .leitor import LeitorNarrado
        print("Abrindo PDF de saída e iniciando narração da entrada original...")
        LeitorNarrado(
            args.saida, args.entrada,
            taxa_fala=args.taxa_fala, voz=args.voz,
        ).narrar(bloqueante=True)


if __name__ == "__main__":
    sys.exit(main())