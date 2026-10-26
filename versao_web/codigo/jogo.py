# Ponto de entrada: cria a janela e encaminha eventos, desenho e atualização à tela ativa.

import asyncio
import sys

import pygame
import constantes as c
import telas
from recursos_web import salvar_ranking


# Coordena a janela, a tela ativa e o ciclo principal que mantém o jogo em execução.
class Jogo:
    # Inicializa o Pygame, abre a janela e prepara o menu inicial e o relógio de quadros.
    def __init__(self):
        pygame.init()
        self.window = pygame.display.set_mode((c.LARGURA_TELA, c.ALTURA_TELA))
        pygame.display.set_caption('The Fox Funk')

        self.tela_atual = telas.Tela_Inicial()
        self.clock = pygame.time.Clock()

    # Retorna a tela que está recebendo eventos e sendo exibida pelo jogo.
    @property
    def tela_atual(self):
        return self._tela_atual

    # Substitui a tela
    #  ativa e chama ao_entrar, quando disponível, para retomar seus recursos.
    @tela_atual.setter
    def tela_atual(self, tela):
        self._tela_atual = tela
        # Uma tela reutilizada também precisa retomar seus recursos ao entrar.
        ao_entrar = getattr(tela, 'ao_entrar', None)
        if ao_entrar is not None:
            ao_entrar()


    # Processa eventos, desenha e atualiza a tela ativa a cada quadro, limitando a taxa de FPS.
    # Ao fechar a janela, encerra os recursos do Pygame.
    async def game_loop(self):
        game = True

        while game:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    game = False
                else:
                    self.tela_atual.tratar_eventos(event)

            if not game:
                break
            self.tela_atual.desenha(self.window)
            self.tela_atual.atualiza(self)
            self.clock.tick(c.FPS)
            pygame.display.update()
            salvar_ranking()
            await asyncio.sleep(0)

        if sys.platform != "emscripten":
            pygame.quit()


if __name__ == '__main__':
    jogo = Jogo()

    asyncio.run(jogo.game_loop())
