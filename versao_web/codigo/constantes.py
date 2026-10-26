"""Dimensões, fontes e cores compartilhadas pelo jogo."""

from pathlib import Path

# Tela e sprites.
LARGURA_TELA = 1280
ALTURA_TELA = 720
FPS = 60
TAMANHO_TABULEIRO = 420
TAMANHO_SETA = 40

# None seleciona a fonte padrão do Pygame.
FONTE_PADRAO = None
FONTE_TITULOS = str(Path(__file__).resolve().parent.parent / "fontes" / "Schoolbell-Regular.ttf")
FONTE_MENSAGENS = str(Path(__file__).resolve().parent.parent / "fontes" / "Nunito-VariableFont_wght.ttf")
# Fonte incluída no projeto para emojis e estrelas, inclusive na versão de navegador.
FONTE_SIMBOLOS = str(Path(__file__).resolve().parent.parent / "fontes" / "NotoSansSymbols2-Regular.ttf")

# Fundos, molduras e textos.
COR_FUNDO = (220, 238, 255)
COR_CAIXA = (255, 249, 240)
COR_CREME_CLARO = (255, 248, 232)
COR_BORDA_ESCURA = (37, 47, 73)
COR_BORDA_CAIXAS = (65, 115, 175)
COR_TEXTO = (37, 47, 73)
COR_TEXTO_SUAVE = (81, 96, 123)
COR_TITULO = (97, 61, 179)
COR_SOMBRA_AVISO = (48, 54, 92)

# Seleção e botões.
COR_FUNDO_SELECIONADO = (220, 235, 255)
COR_TEXTO_SELECIONADO = (28, 62, 122)
COR_FOCO = (39, 87, 163)
COR_BOTAO = (255, 211, 78)
COR_BOTAO_HOVER = (255, 184, 56)
COR_BOTAO_DESABILITADO = (195, 207, 224)
COR_BORDA_DESABILITADA = (98, 115, 140)
COR_TEXTO_DESABILITADO = (67, 82, 107)

# Partida e mensagens de acerto.
COR_PODER = (45, 211, 159)
COR_ANEL_TABULEIRO = (133, 99, 245)
COR_PRONTO = (28, 107, 65)
COR_ESCOLHENDO = (39, 87, 163)
COR_CONTAGEM_VAI = (20, 115, 81)
COR_ERRO = (173, 40, 66)
COR_ACERTO_BOM = (28, 107, 65)
COR_ACERTO_PERFEITO = (103, 52, 162)

# Cores dos botões do Xbox correspondentes a cada direção.
CORES_DIRECOES = {
    "cima": (255, 211, 78),      # Y: amarelo
    "baixo": (45, 211, 159),     # A: verde
    "esquerda": (56, 166, 255),  # X: azul
    "direita": (255, 90, 107),   # B: vermelho
}

# Madeira das molduras e do pódio.
COR_MADEIRA = (112, 69, 47)
COR_MADEIRA_CLARA = (184, 137, 86)
COR_MADEIRA_ESCURA = (81, 60, 51)

# Resultados e ranking.
COR_VENCEDORES = (28, 107, 65)
COR_PERDEDORES = (196, 48, 55)
COR_NOME_JOGADOR_2_PODIO = (39, 87, 163)
COR_TEXTO_PODIO = (255, 241, 201)

PISCA_PODER = (210, 185, 245)

# Velocidade base em pixels por quadro; notas sincronizadas convertem o tempo do áudio para essa escala.
VELOCIDADE_NOTA = 1.2
