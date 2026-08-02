# DocShieldAI

**Aplica uma camada de distorção visual + fonte personalizada + textura + granulado sobre um PDF (ou sobre um .docx/.rtf/.txt, convertendo antes), pra dificultar extração de texto por OCR e scraping automatizado - sem reescrever o conteúdo nem exigir senha.**

O problema que isso resolve: em contextos como avaliações de universidades públicas, materiais em PDF são frequentemente copiados/colados direto numa IA generativa, que devolve a resposta pronta. O `DocShieldAI` ataca uma fatia menor e mais específica desse problema: tornar o texto do documento ilegível pra ferramentas de extração automática (`pdftotext`, OCR clássico, scrapers), mantendo a leitura humana normal na tela ou impressa.

**Isso não é uma solução completa - ver "Segurança e limites conhecidos" abaixo antes de usar em prova real, incluindo o aviso sobre TEA/autismo e outras deficiências.**

---

## A ideia central

- **A página vira imagem, não texto.** O documento (PDF, ou docx/rtf/txt convertido primeiro) é rasterizado - cada página renderizada como bitmap - antes de qualquer outra coisa. Isso já elimina a camada de texto selecionável/copiável, que é a proteção mais confiável do projeto - tudo que vem depois é uma dificuldade *adicional* em cima disso, não a proteção principal.
- **Ondulação por linha, no estilo CAPTCHA clássico.** Cada linha horizontal da imagem é deslocada por um valor senoidal. O olho humano lê pela forma global da palavra e ignora a ondulação; OCR clássico, que segmenta caractere por caractere em colunas verticais, se confunde com o deslocamento - mas só a partir de uma certa frequência de onda (ver "Resultados medidos").
- **Textura sobreposta em baixo contraste.** Curvas onduladas aleatórias, parecidas com um watermark diagonal, atravessam a página inteira em opacidade baixa - suficiente pra quebrar os contornos que o OCR usa pra separar caractere de fundo, sem impedir leitura normal.
- **Granulado.** Ruído gaussiano leve por pixel, pra atrapalhar filtros de "limpeza" que pipelines de OCR costumam aplicar antes de reconhecer texto.
- **Fonte customizável.** Pra entradas .docx/.rtf/.txt, dá pra trocar a fonte do documento inteiro por qualquer `.ttf` que você tiver à mão antes de rasterizar - o mesmo arquivo pode ser usado na marca d'água opcional. Ver "Escolhendo uma fonte" abaixo antes de usar uma fonte decorativa.
- **Marca d'água opcional.** Texto em mosaico diagonal, baixa opacidade, repetido pela página inteira - cada instância vira mais uma "palavra candidata" competindo com o conteúdo real pra ferramentas de extração de layout.
- **Leitor narrado opcional (acessibilidade).** `--leitor` abre o PDF protegido no visualizador padrão e narra, em paralelo, o texto extraído da entrada original - sem reintroduzir texto copiável no arquivo em si. Ver "Leitor narrado" abaixo.

## Pipeline

```
 entrada                   conversor (só p/       pypdfium2                distorção                 saída
 .pdf / .docx / .rtf/.txt  docx/rtf/txt)          rasteriza                nucleo.py
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌────────────────────┐   ┌──────────────────────┐
│ texto/imagens    │──▶│ reportlab monta   │──▶│ cada página vira │──▶│ 1. marca d'água (opc)│──▶│ páginas remontadas   │
│ selecionáveis,   │   │ o PDF direto em   │   │ bitmap           │   │ 2. ondulação senoidal│   │ como JPEG via img2pdf │
│ .pdf direto pula │   │ Python, fonte     │   │                  │   │ 3. textura ondulada  │   │                       │
│ essa etapa       │   │ .ttf embutida     │   │                  │   │ 4. granulado         │   │                       │
└──────────────────┘   └──────────────────┘   └──────────────────┘   │ 5. suavização leve   │   └──────────────────────┘
                                                                       └────────────────────┘
                              │
                              ▼ (em paralelo, opcional)
                    DocShieldAI.extrator extrai o texto puro
                    da entrada -> DocShieldAI.leitor narra
                    junto com a abertura do PDF de saída
```

**Nota sobre a ordem do pipeline:** a marca d'água (quando pedida) é aplicada **antes** da ondulação/textura/granulado, não depois - por isso o texto da marca d'água também sai ondulado e granulado junto com o resto da página, em vez de ficar nítido por cima da distorção. Depois do granulado, ainda passa um filtro de suavização leve (`ImageFilter.SMOOTH`) pra amaciar o ruído antes de virar JPEG.

**Nota sobre fidelidade:** a conversão docx/rtf/txt -> PDF aqui é feita 100% em Python (`reportlab`), sem depender de LibreOffice/Word. É mais simples que um render de verdade: preserva texto, margens/tamanho de página (no caso do .docx) e alinhamento de parágrafo, mas não preserva negrito/itálico por trecho, e tabelas viram texto com "|" separando células. Como o documento vai ser rasterizado e distorcido logo em seguida, essa é uma troca razoável - se você já tem um `.pdf` pronto, pule a conversão e use ele direto.

## Resultados medidos

Testado com um PDF de uma questão de prova (texto nativo, extraível via `pypdf` antes do processamento) contra o Tesseract 5 (motor OCR de código aberto mais usado). Similaridade calculada com `difflib` entre o texto original e o texto reconhecido após cada nível de proteção:

| Nível | freq_onda | Texto copia-e-cola no PDF final | Similaridade via OCR |
|---|---|---|---|
| `leve` | 20 | vazio (rasterizado) | ~99,7% |
| `medio` | 36 | vazio (rasterizado) | ~70,2% |
| `agressivo` | 48 | vazio (rasterizado) | ~6,1% |

O parâmetro que mais pesa na queda de precisão do OCR é a **frequência da onda** (`freq_onda`), não a amplitude nem o granulado isoladamente - abaixo de uma certa frequência (por volta de 30 ciclos/página, no nosso teste) o Tesseract absorve a distorção sem perder o reconhecimento; acima disso a precisão despenca rápido. Isso bateu de forma consistente nos nossos testes, mas **é um resultado de um único documento de teste**, não uma garantia universal - o efeito real varia com fonte, tamanho de letra e densidade de texto da sua prova.

**Importante:** este teste usa OCR clássico. A expectativa inicial era que modelos de IA multimodais (que "leem" a página como imagem, não via extração de texto) fossem mais robustos a esse tipo de distorção, por terem sido treinados com grandes volumes de imagens degradadas, incluindo CAPTCHAs. Um teste manual (ver abaixo) sugere o oposto pelo menos num caso, então trate essa expectativa com cautela até haver mais testes.

**Teste manual contra ChatGPT (visão multimodal):** o PDF gerado com `python -m DocShieldAI.cli entrada.docx saida.pdf --nivel leve --marca-dagua "Bruno Nunes da Silva" --leitor` (nível `leve` - o mesmo que manteve ~99,7% de similaridade contra o Tesseract na tabela acima) foi mostrado ao ChatGPT pedindo pra ele ler o conteúdo. O resultado, registrado no print `Captura_de_tela_2026-08-01_225118.png` (repositório), foi o oposto do esperado: o modelo não conseguiu fazer uma leitura confiável, reconheceu só fragmentos soltos e incorretos de algumas linhas, e identificou a marca d'água ("Bruno Nunes da Silva") mas não o corpo do texto. Ou seja, nesse teste pontual, no nível mais fraco de proteção, a IA multimodal teve desempenho **pior** que o OCR clássico no mesmo nível - o inverso do que a frase acima presumia. É um único teste manual, sem metodologia repetida como a do Tesseract, então não deve ser lido como "X% de proteção contra IA" - mas é evidência concreta de que a suposição "IA multimodal é mais robusta" não é garantida, e pode até estar errada dependendo do modelo e da imagem.

## Como usar

**0. Instale as dependências Python:**
```bash
pip install -r requirements.txt --break-system-packages
```
Não precisa de LibreOffice, Word nem nenhum programa de escritório - a conversão `.docx`/`.rtf`/`.txt` -> PDF é feita direto em Python (`reportlab`). O leitor narrado (`--leitor`) é opcional e depende de `pyttsx3`, incluído no `requirements.txt` (usa SAPI5 no Windows, NSSpeechSynthesizer no macOS e `espeak` no Linux - `sudo apt install espeak` se necessário).

**1. Rode o CLI:**
```bash
python -m DocShieldAI.cli entrada.pdf saida.pdf --nivel medio
python -m DocShieldAI.cli entrada.docx saida.pdf --nivel medio
```

**2. Escolha o nível de proteção** (trade-off entre legibilidade e distorção):
```bash
python -m DocShieldAI.cli entrada.pdf saida_leve.pdf --nivel leve
python -m DocShieldAI.cli entrada.pdf saida_agressivo.pdf --nivel agressivo
```
Comece por `medio` e abra o resultado antes de distribuir - se estiver difícil demais de ler na tela/impressão, desça pra `leve`; se ainda estiver copiável de forma útil, suba pra `agressivo`.

**3. (Só docx/rtf/txt) Troque a fonte por qualquer `.ttf`** que você tenha baixado - solte o arquivo em `fontes/` e aponte pra ele:
```bash
python -m DocShieldAI.cli entrada.docx saida.pdf --nivel medio --fonte fontes/OrnamentalInitial.ttf
```
O nome usado para registrar a fonte no `reportlab` vem do **nome do arquivo `.ttf`** (o `stem`, com espaços trocados por `_`) - não é lido de dentro dos metadados do arquivo (tabela `name` do TrueType). Então funciona com qualquer fonte baixada, mas o nome de exibição depende de como o arquivo `.ttf` está nomeado no disco, não do nome interno que a fonte carrega. A mesma fonte é usada na marca d'água, se você pedir uma. **Antes de usar uma fonte decorativa em produção, ver "Escolhendo uma fonte" abaixo.**

**Fonte padrão sem passar `--fonte`:** se `fontes/Renaissance-Initialen 1.ttf` existir no repo, o conversor registra e usa ela automaticamente, sem precisar do flag em toda chamada. Se o arquivo não existir nesse caminho, cai em `Helvetica` (uma das 14 fontes padrão do PDF) sem quebrar - nunca usa um nome de fonte não registrado, que é o que causava o erro `Can't map determine family/bold/italic for ...` do `reportlab` em versões anteriores.

**4. (Opcional) Marca d'água em mosaico:**
```bash
python -m DocShieldAI.cli entrada.pdf saida.pdf --nivel medio --marca-dagua "USO PESSOAL - SEU NOME"
```

**5. (Opcional) Fixe a semente aleatória** pra reproduzir exatamente o mesmo padrão de ruído entre execuções:
```bash
python -m DocShieldAI.cli entrada.pdf saida.pdf --nivel medio --semente 7
```

**6. (Opcional) Sobrescreva o DPI de renderização** do preset escolhido:
```bash
python -m DocShieldAI.cli entrada.pdf saida.pdf --nivel medio --dpi 250
```
DPI mais alto preserva mais nitidez do texto original antes da distorção, mas gera um PDF maior.

**7. (Opcional) Leitor narrado**, pra acessibilidade - abre o PDF de saída no visualizador padrão do sistema e narra em voz o texto extraído da entrada original, sem reintroduzir texto copiável no arquivo:
```bash
python -m DocShieldAI.cli entrada.docx saida.pdf --nivel medio --leitor
python -m DocShieldAI.cli entrada.docx saida.pdf --nivel medio --leitor --voz "Maria" --taxa-fala 160
```
`--voz` aceita um nome/id parcial de qualquer voz já instalada no sistema operacional; `--taxa-fala` controla a velocidade em palavras por minuto (padrão: 175).

**Exemplo completo, com fonte decorativa** - trocando a fonte por `OrnamentalInitial.ttf` (ver "Escolhendo uma fonte" acima antes de usar em produção: das três fontes decorativas testadas é a mais segura pra corpo de texto, já que tem números, minúsculas e maiúsculas - ainda assim teste a acentuação (Ê, Ç, Ã) antes de distribuir):

```bash
# sem --leitor: só gera o PDF protegido com a fonte trocada
python -m DocShieldAI.cli entrada.docx saida.pdf --fonte "fontes/OrnamentalInitial.ttf"

# com --leitor: gera igual, mas já abre o PDF e narra o texto original em voz -
# útil como reforço de acessibilidade além da fonte, já que mesmo uma fonte mais
# legível como a CelticEels ainda passa pela ondulação/textura/granulado da distorção
python -m DocShieldAI.cli entrada.docx saida.pdf --fonte "fontes/OrnamentalInitial.ttf" --leitor
```

O `--leitor` não depende da fonte escolhida - ele narra o texto extraído da **entrada** (`entrada.docx`), não o que foi renderizado com a fonte decorativa no PDF de saída. Então mesmo que `OrnamentalInitial.ttf` deixe algum trecho mais difícil de ler pra alguém, a narração sai correta.

**Sobre o print no repositório:** o screenshot do `saida.pdf` que aparece no repositório foi gerado com o comando:
```bash
python -m DocShieldAI.cli entrada.docx saida.pdf --nivel leve --marca-dagua "Bruno Nunes da Silva" --leitor
```

### Uso programático (sem passar pelo CLI)

Se o PDF de saída já existe e você só quer abrir + narrar (sem gerar de novo):

```python
from DocShieldAI.leitor import LeitorNarrado

# bloqueante=True trava até a narração acabar
LeitorNarrado("saida.pdf", "entrada.docx").narrar(bloqueante=True)

# bloqueante=False roda em thread separada - útil dentro de um app
# com botão "ler em voz alta", por exemplo
leitor = LeitorNarrado("saida.pdf", "entrada.docx", taxa_fala=160, voz="Maria")
leitor.narrar(bloqueante=False)
# ...
leitor.parar()  # interrompe a narração a qualquer momento
```

Detalhes de comportamento:
- Se `--voz`/`voz=` não encontrar nenhuma correspondência entre as vozes instaladas, cai silenciosamente na voz padrão do sistema, sem avisar.
- No Linux, se o `espeak` não estiver instalado, `narrar()` levanta erro na hora de inicializar o motor `pyttsx3` (não é um aviso silencioso).
- Pra extrair só o texto, sem abrir nem narrar nada, use `DocShieldAI.extrator.ExtratorTexto.extrair("entrada.docx")` diretamente - devolve a lista de parágrafos.
- A narração junta **todos** os parágrafos numa única string (`". ".join(...)`) e manda num só `say()` + `runAndWait()`, em vez de enfileirar um `say()` por parágrafo - enfileirar é o padrão sugerido pela documentação do `pyttsx3`, mas o driver SAPI5 do Windows é pouco confiável com fila de vários itens e às vezes só fala o primeiro. Concatenar tudo numa string só evita esse bug nas três plataformas.

## Parâmetros por nível

| Nível | DPI | amplitude_onda | freq_onda | opacidade_textura | granulado |
|---|---|---|---|---|---|
| `leve` | 200 | 4 px | 20 | 40/255 | 14 |
| `medio` | 200 | 6 px | 36 | 55/255 | 26 |
| `agressivo` | 200 | 7 px | 48 | 70/255 | 34 |

## Escolhendo uma fonte

Qualquer `.ttf` funciona tecnicamente, mas fontes puramente decorativas costumam vir da categoria "letra capitular/inicial" (drop cap) e não têm o conjunto de glifos completo pra um documento inteiro. Três exemplos que passam por aqui de vez em quando, com a cobertura de glifos real (checada na fonte, não estimada):

| Fonte | Glifos | Cobertura | Recomendação |
|---|---|---|---|
| `CelticEels` | 58 | números + minúsculas + maiúsculas + poucos acentos | a mais segura das três pra corpo de texto curto; ainda assim teste acentuação (Ê, Ç, Ã) |
| `OrnamentalInitial` | 61 | maiúsculas + poucos acentos, **provavelmente sem minúsculas** | usar só em título/cabeçalho, não no corpo da prova |
| `Halftone` | 28 | conjunto bem incompleto (típico de fonte só de maiúsculas) | usar só em título/cabeçalho, não no corpo da prova |

Nenhuma das três cobre bem o bloco Latin-1 Supplement completo (`Á É Í Ó Ú Â Ê Ô Ã Õ Ç`), que o português usa bastante - se um caractere não existir na fonte, o `reportlab` desenha o `.notdef` (um quadrado vazio) ou simplesmente omite o glifo, dependendo do renderizador. **Antes de usar qualquer fonte decorativa em produção, gere um teste com o alfabeto completo que sua prova usa (maiúsculas, minúsculas, `0-9`, acentos) e abra o PDF resultado** - o mesmo aviso do nível `agressivo` vale aqui: uma fonte difícil de ler pra OCR também pode ficar difícil de ler pra humano, especialmente em corpo de texto pequeno, já que essas três foram desenhadas pra uma letra grande de abertura, não pra parágrafo corrido.

`Renaissance-Initialen 1.ttf` é a fonte padrão embutida do projeto: se ela existir em `fontes/Renaissance-Initialen 1.ttf`, o `conversor.py` registra ela automaticamente via `pdfmetrics.registerFont` mesmo sem você passar `--fonte`. Isso é diferente de simplesmente escrever o nome da fonte como string no código - uma string solta sem registro prévio faz o `reportlab` quebrar (`ValueError: Can't map determine family/bold/italic for ...`) porque ele não sabe resolver bold/itálico pra um nome que não conhece. Se o `.ttf` não estiver no caminho esperado, o fallback é `Helvetica`, sempre disponível sem registro.

**Atenção especial pra provas com números, fórmulas ou cálculos.** Se a fonte escolhida não tiver glifo pra um dígito (`0-9`) ou símbolo (`+ - * / =`), o resultado não é "um pouco difícil de ler" - é **o caractere sumir ou virar um quadrado vazio (`.notdef`)** no PDF final, pro aluno também, não só pra IA/OCR. Isso não é uma proteção a mais, é o documento ficando ilegível pro destinatário legítimo, que é exatamente o problema que a marca d'água/distorção não deveria causar. Antes de mandar pra alguém, abra o PDF gerado e confira lado a lado com o original que todo número e símbolo da prova apareceu certo - principalmente com `OrnamentalInitial`, `Halftone` e fontes parecidas de "letra capitular", cuja cobertura de glifos costuma ser pensada só pra uma letra grande decorativa, não pro alfabeto e os números inteiros. Se sobrar qualquer dúvida sobre a cobertura, use `Helvetica` (ou não passe `--fonte`, contanto que `fontes/OrnamentalInitial.ttf` não esteja no lugar do padrão) - a fonte em si contribui pouco pra proteção real (ver "Resultados medidos": quem derruba o OCR é a ondulação, não a fonte), então não vale o risco de a prova sair incompreensível.

## Leitor narrado

Pensado especificamente pro ponto de acessibilidade que a seção "Segurança e limites conhecidos" já citava: o PDF final é só imagem, o que elimina leitores de tela pra quem precisa deles. O `--leitor` cobre esse caso sem reabrir a proteção:

- `DocShieldAI.extrator.ExtratorTexto` extrai o texto puro (parágrafos) direto da **entrada original**, antes de qualquer rasterização - suporta `.pdf`, `.docx`, `.rtf` e `.txt`.
- `DocShieldAI.leitor.LeitorNarrado` abre o **PDF de saída (já protegido)** no visualizador padrão do sistema operacional e, em paralelo, narra esse texto extraído via `pyttsx3` (TTS local, offline, sem depender de serviço externo).

O texto narrado nunca é escrito de volta no PDF - ele existe só na memória do processo, então a proteção anti-scraping do arquivo em si continua intacta. Isso é uma ferramenta de apoio pra quem abre o arquivo (rodando localmente, com o próprio PDF já em mãos), não um jeito de extrair texto em lote.

## Segurança e limites conhecidos

- **Não impede um aluno de fotografar a tela ou digitar o enunciado manualmente.** Se a pessoa é o intermediário entre o documento e a IA, nenhuma proteção no arquivo em si resolve isso - esse é um problema de desenho de avaliação, não de engenharia de arquivo.
- **Não dá pra assumir que modelos de IA multimodais são mais resistentes que o OCR clássico testado aqui** (ver "Resultados medidos" acima) - um teste manual contra ChatGPT no nível `leve` teve resultado pior que o Tesseract no mesmo nível, contrariando a expectativa inicial. Os números desta seção não devem ser lidos como "X% de proteção contra IA" de forma genérica, em nenhuma direção.
- **Nível `agressivo` (e fontes decorativas mal escolhidas) comprometem legibilidade pra qualquer leitor**, incluindo pessoas com baixa visão ou dislexia - teste a saída você mesmo antes de aplicar em prova real. Use `--leitor` pra oferecer uma via de acesso alternativa sem abrir mão da proteção do arquivo.
- **Não recomendado pra pessoas com TEA/autismo ou qualquer outro tipo de deficiência, sem alternativa oferecida.** A ondulação senoidal, a textura sobreposta e o granulado são justamente o tipo de estímulo visual (padrões repetitivos, ruído, distorção de contorno) que pode causar desconforto sensorial, dificuldade de leitura ou sobrecarga em pessoas autistas, com TDAH, dislexia, discalculia ou outras condições. Isso vale pra qualquer nível de proteção, não só o `agressivo`. Se você sabe ou suspeita que algum destinatário se encaixa nesse caso, ofereça a versão sem proteção diretamente, ou gere a saída com `--leitor` para que a leitura em voz substitua a leitura visual da página distorcida.
- **Fonte decorativa sem cobertura de glifos pode deixar a prova ilegível pro próprio aluno, não só difícil pra OCR.** Se a fonte escolhida (ex.: `OrnamentalInitial`, `Halftone`) não tiver dígito ou símbolo matemático no conjunto de glifos, o caractere some ou vira um quadrado vazio no PDF final - pro destinatário legítimo também. Sempre confira a saída antes de enviar quando a prova tiver números, fórmulas ou cálculos. Ver "Escolhendo uma fonte" acima.
- **O PDF final é só imagem** - isso também elimina recursos legítimos como busca de texto (Ctrl+F) e cópia de trechos citáveis. É uma troca deliberada, não um efeito colateral escondido; o `--leitor` cobre a parte de leitura em voz, mas não devolve Ctrl+F nem seleção de texto.
- **Não é criptografia nem controle de acesso** - qualquer pessoa com o arquivo consegue abri-lo e ler normalmente; a proteção é só contra extração automatizada de texto, não contra distribuição do PDF em si. Pra isso, combine com senha (`writer.encrypt()` do pypdf, ver documentação de PDF) se fizer sentido pro seu caso.
- **Cada rodada de OCR/IA evolui** - esse tipo de proteção por ofuscação visual tende a perder eficácia com o tempo, à medida que os modelos ficam mais robustos a distorção. Trate como uma dificuldade a mais, não como uma barreira permanente.

## Estrutura do projeto

```
DocShieldAI/
├── DocShieldAI/
│   ├── __init__.py
│   ├── nucleo.py       # rasterização, ondulação, textura, granulado, marca d'água, remontagem em PDF
│   ├── conversor.py    # docx/rtf/txt -> pdf via reportlab (Python puro, sem LibreOffice/Word) + fonte .ttf embutida
│   ├── extrator.py     # extrai texto puro da entrada original (pdf/docx/rtf/txt), p/ acessibilidade
│   ├── leitor.py        # abre o PDF de saída e narra o texto extraído (pyttsx3), p/ acessibilidade
│   └── cli.py           # interface de linha de comando única
├── fontes/               # solte aqui as fontes .ttf que você baixar
├── exemplos/             # gere seus próprios exemplos com o CLI
├── requirements.txt
├── LICENSE
└── README.md
```

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt` (pypdfium2, pillow, numpy, img2pdf, python-docx, reportlab, striprtf, pyttsx3)
- Nenhum programa de escritório (Word/LibreOffice) é necessário - a conversão docx/rtf/txt -> PDF é feita direto em Python
- `--leitor` usa a engine de TTS nativa do sistema via `pyttsx3`; no Linux normalmente exige `espeak` instalado (`sudo apt install espeak`)

## Status

- [x] Rasterização do documento de entrada (remove texto copia-e-cola)
- [x] Deslocamento senoidal por linha
- [x] Textura ondulada sobreposta em baixo contraste
- [x] Granulado gaussiano
- [x] Três presets calibrados e medidos contra Tesseract 5
- [x] CLI único com controle de nível, DPI, semente, fonte custom e marca d'água
- [x] Conversão docx/rtf/txt -> PDF com troca de fonte, sem depender de LibreOffice/Word
- [x] Extração de texto puro da entrada original, pra uso em acessibilidade
- [x] Leitor narrado (`--leitor`): abre o PDF de saída e narra o texto da entrada, via TTS local
- [x] Fonte padrão embutida registrada corretamente (fallback seguro pra Helvetica se o `.ttf` não existir)
- [x] Narração corrigida pra ler o documento inteiro (concatenação numa string única, evita bug do SAPI5 no Windows)

## Direção futura

A distorção atual trata a página inteira do mesmo jeito. Uma direção natural é permitir proteger só o corpo das questões e deixar cabeçalho/identificação da prova (nome, data, número) sem distorção, facilitando organização/correção manual sem abrir mão da proteção onde importa. Isso ainda não está implementado - hoje é tudo ou nada por página.

## Sobre este projeto

Ferramenta pensada como resposta prática (e parcial) ao uso de IA generativa pra resolver avaliações copiando o enunciado direto do documento, no contexto de ensino superior público. Não substitui redesenho de avaliação nem política institucional sobre uso de IA - ver limitações acima.

**Autor:** Bruno Nunes da Silva (criador do DevSoft JARVIS AI)<br>
**Conheça o DevSoft JARVIS AI:** https://devsoft-ai.webnode.page/<br>
**Canal no YouTube:** https://www.youtube.com/@devsoftai5538

## Licença

MIT - use, modifique e distribua livremente, mantendo os créditos de autoria.
