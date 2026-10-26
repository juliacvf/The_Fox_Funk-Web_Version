import sys
import pygame

_musica_carregada = None

# Padroniza espaços e maiúsculas para reconhecer o mesmo jogador e impedir nomes duplicados.
def normalizar_nome(nome):
    return ' '.join(nome.split()).casefold()


# Renderiza o texto sem contorno, mantendo o parâmetro antigo por compatibilidade com as chamadas.
def texto_com_contorno(fonte, mensagem, cor, cor_contorno=None):
    # Mantém a assinatura para compatibilidade, mas desenha texto sem contorno.
    return fonte.render(mensagem, True, cor)


# Combina o texto e um símbolo em uma superfície única, alinhando os dois verticalmente.
def texto_com_icone(fonte, fonte_icone, mensagem, icone, cor):
    texto = fonte.render(mensagem, True, cor)
    simbolo = fonte_icone.render(icone, True, cor)
    espaco = fonte_icone.size(' ')[0]
    altura = max(texto.get_height(), simbolo.get_height())
    superficie = pygame.Surface((texto.get_width() + espaco + simbolo.get_width(), altura), pygame.SRCALPHA)
    superficie.blit(texto, texto.get_rect(midleft=(0, altura // 2)))
    superficie.blit(simbolo, simbolo.get_rect(midleft=(texto.get_width() + espaco, altura // 2)))
    return superficie


# Carrega o áudio e registra o arquivo atual para que o menu possa evitar recarregamentos.
def carregar_musica(arquivo):
    global _musica_carregada
    pygame.mixer.music.load(arquivo)
    _musica_carregada = arquivo


# Inicia a trilha do menu em repetição, preservando a reprodução se ela já estiver tocando.
def tocar_musica_menu():
    if _musica_carregada == "musicas/faixa_109.ogg" and (sys.platform == "emscripten" or pygame.mixer.music.get_busy()):
        return
    carregar_musica("musicas/faixa_109.ogg")
    pygame.mixer.music.play(-1)
