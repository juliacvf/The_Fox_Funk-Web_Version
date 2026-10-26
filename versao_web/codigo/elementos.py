# Sprites do jogo: elementos visuais, notas, personagens e efeitos dos poderes.

import pygame
import constantes as c
import random

# Monta a imagem fixa do tabuleiro, incluindo a moldura, o anel e a pata central.
class Tabuleiro(pygame.sprite.Sprite):
    # Carrega a moldura e compõe o anel e a pata central na posição informada.
    def __init__(self, x, y):
        super().__init__()

        image = pygame.image.load("sprites/tabuleiro.png") # tabuleiro como elemento pixelado em png (chat que fez)
        self.image = pygame.transform.scale(image, (c.TAMANHO_TABULEIRO, c.TAMANHO_TABULEIRO))

        centro = self.image.get_rect().center
        pygame.draw.circle(self.image, c.COR_ANEL_TABULEIRO, centro, 62, 4) #anel do centro

        pata = pygame.image.load("sprites/elemento-centro.png").convert_alpha()
        pata = pygame.transform.scale(pata, (35, 35))
        posicao_pata = pata.get_rect(center=self.image.get_rect().center)
        self.image.blit(pata, posicao_pata) # elemento central (chat que fez)

        self.rect = self.image.get_rect(center=(x, y))

        luz = pygame.Surface((40, 80), pygame.SRCALPHA)


# Representa o brilho colorido que marca uma direção no tabuleiro.
class Luz(pygame.sprite.Sprite): # estilização de luzes p/ tabuleiro
    # Cria camadas transparentes de luz e as gira para a direção escolhida.
    def __init__(self, x, y, cor, angulo):
        super().__init__()

        self.image = pygame.Surface((40, 80), pygame.SRCALPHA)

        pygame.draw.rect(self.image, (*cor, 20), (8, 0, 24, 80))
        pygame.draw.rect(self.image, (*cor, 20), (0, 8, 40, 64))
        pygame.draw.rect(self.image, (*cor, 40), (8, 8, 24, 64))
        pygame.draw.rect(self.image, (*cor, 65), (12, 16, 16, 48))
        pygame.draw.rect(self.image, (*cor, 90), (16, 24, 8, 32))

        self.image = pygame.transform.rotate(self.image, angulo)
        self.rect = self.image.get_rect(center=(x, y))


# Representa uma tecla de referência do tabuleiro, com animação de tamanho na batida e no acerto.
class Setas(pygame.sprite.Sprite):
    # Carrega e orienta a tecla, preservando a imagem original para as animações.
    def __init__(self, x, y, angulo):
        super().__init__()

        image = pygame.image.load("sprites/tecla.png")
        self.image = pygame.transform.scale(image, (c.TAMANHO_SETA, c.TAMANHO_SETA))
        self.image = pygame.transform.rotate(self.image, angulo)
        self.rect = self.image.get_rect(center = (x, y))
        #guarda como é a imagem original para quando ela for apertada
        self.original = self.image

        #variáveis
        self.angulo = angulo
        self.escala = 1.0

    # Faz a escala voltar suavemente ao tamanho normal sem deslocar o centro da tecla.
    def update(self):
        # Retorna suavemente ao tamanho normal se ela estiver menorzinha
        self.escala += (1.0 - self.escala) * 0.20

        if abs(1.0 - self.escala) < 0.001:
            self.escala = 1.0

        centro = self.rect.center

        largura = max(1, round(self.original.get_width() * self.escala))
        altura = max(1, round(self.original.get_height() * self.escala))

        self.image = pygame.transform.smoothscale(self.original, (largura, altura))
        self.rect = self.image.get_rect(center=centro)

    # Inicia o aumento da tecla para destacar a batida.
    def animar(self):
        if self.escala == 1:
            self.escala = 1.05


# Representa uma nota em movimento, com direção, velocidade e horário previsto de chegada.
class Notas(pygame.sprite.Sprite):
    # Prepara a imagem colorida e guarda origem, direção e horário de chegada da nota.
    def __init__(self, x, y, angulo, cor, lado, velocidade=None, chegada=None):
        super().__init__()

        image = pygame.image.load("sprites/seta.png").convert_alpha()
        self.image = pygame.transform.scale(image, (c.TAMANHO_SETA, c.TAMANHO_SETA))
        self.image = pygame.transform.rotate(self.image, angulo)
        self.image.fill((*cor, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.rect = self.image.get_rect(center=(x, y))

        self.cor = cor
        self.x = x
        self.y = y
        self.origem = (x, y)
        self.angulo = angulo
        self.lado = lado
        self.distancia = 0
        self.velocidade = c.VELOCIDADE_NOTA if velocidade is None else velocidade
        self.chegada = chegada

    # Calcula a posição pela distância percorrida ou pelo tempo do áudio, mantendo a chegada sincronizada.
    def update(self, tempo_musica=None):
        if self.chegada is None or tempo_musica is None:
            self.distancia += self.velocidade
        else:
            self.distancia = max(0, 148 + (tempo_musica - self.chegada) * self.velocidade * 60 / 1000)

        self.x, self.y = self.origem

        if self.angulo == 180:
            self.x += self.distancia
        if self.angulo == 0:
            self.x -= self.distancia
        if self.angulo == 90:
            self.y += self.distancia
        if self.angulo == 270:
            self.y -= self.distancia

        self.rect.center = (round(self.x), round(self.y))


# Guarda a pontuação e a carga de poder de um jogador e desenha sua barra de energia.
class Pontos(pygame.sprite.Sprite): # define pontuação e barrinha de poder
    # Posiciona a barra e inicia pontuação e carga de poder em zero.
    def __init__(self, x, y):
        super().__init__()

        image = pygame.image.load("sprites/barra-poder.png")
        self.base = pygame.transform.scale(image, (420, image.get_height()))
        self.image = self.base.copy()
        self.rect = self.image.get_rect(center = (x, y))

        self.pontos = 0
        self.poder = 0
        self.preenchimento = 0

    # Redesenha o preenchimento da barra conforme a porcentagem de poder atual.
    def update(self): # atualiza desenho da barrinha de poder de acordo com a situação
        largura_interior = 420
        self.preenchimento = int(largura_interior * self.poder / 100)

        self.image = self.base.copy()
        self.image.fill(c.COR_PODER, (0, 17, self.preenchimento, 6))


# Representa uma raposa e concentra o catálogo de skins e as pastas de suas animações.
class Personagem(pygame.sprite.Sprite): # define personagens
    personagens = [
        {"nome": "Raposa Comum", "link": "sprites/raposa.png", "pasta": "raposa_normal", "pasta_comemoracao": "raposa_normal_comemorando", "pasta_chorando": "raposa_normal_chorando"},
        {"nome": "Raposa Funk", "link": "sprites/raposa.png", "pasta": "raposa_funk", "pasta_comemoracao": "raposa_funk_comemorando", "pasta_chorando": "raposa_funk_chorando"},
        {"nome": "Raposa Sertanejo", "link": "sprites/raposa.png", "pasta": "raposa_sertanejo", "pasta_comemoracao": "raposa_sertanejo_comemorando", "pasta_chorando": "raposa_sertanejo_chorando"},
        {"nome": "Raposa Rockeira", "link": "sprites/raposa.png", "pasta": "raposa_roqueira", "pasta_comemoracao": "raposa_rock_comemorando", "pasta_chorando": "raposa_rock_chorando"},
        {"nome": "Raposa Kpop", "link": "sprites/raposa.png", "pasta": "raposa_kpop", "pasta_comemoracao": "raposa_kpop_comemorando", "pasta_chorando": "raposa_kpop_chorando"},
        {"nome": "Raposa Diva", "link": "sprites/raposa.png", "pasta": "raposa_diva", "pasta_comemoracao": "raposa_diva_comemorando", "pasta_chorando": "raposa_diva_chorando"},
        {"nome": "Raposa Emo", "link": "sprites/raposa.png", "pasta": "raposa_emo", "pasta_comemoracao": "raposa_emo_comemorando", "pasta_chorando": "raposa_emo_chorando"},
        {"nome": "Raposa Samba", "link": "sprites/raposa.png", "pasta": "raposa_samba", "pasta_comemoracao": "raposa_samba_comemorando", "pasta_chorando": "raposa_samba_chorando"},
        {"nome": "Raposa Vasco", "link": "sprites/raposa.png", "pasta": "raposa_vasco", "pasta_comemoracao": "raposa_vasco_comemorando", "pasta_chorando": "raposa_vasco_chorando"},
    ]

    # Carrega a skin escolhida e seus frames, aplicando tamanho e espelhamento inicial.
    def __init__(self, x, y, flip, indice_personagem=0): # flip: atributo booleano
        super().__init__()

        # pega as informações do personagem escolhido na tela de escolha
        self.dados_personagem = self.personagens[indice_personagem]

        image = pygame.image.load(self.dados_personagem["link"]).convert_alpha()
        image = pygame.transform.scale_by(image, 2.8)  # Amplia a skin para o tamanho usado na partida.
        self.image = pygame.transform.flip(image, flip, False) # espelha imagem
        self.rect = self.image.get_rect(center=(x, y))

        # Carrega a sequência de imagens da animação.
        pasta = self.dados_personagem["pasta"]

        self.frames = [pygame.image.load(f"sprites/{pasta}/{pasta}_{i}.png").convert_alpha() for i in range(1, 7)]

        #variáveis dos frames
        self.indice = 0
        self.contador = 0
        self.flip = flip

        self.angulo = 0

    # Avança os frames da raposa e preserva centro, espelhamento e rotação durante a animação.
    def update(self):
        self.contador += 1

        if self.contador >= 8:
            self.contador = 0
            self.indice += 1

            # Acabaram os frames: reseta a animação
            if self.indice >= len(self.frames):
                self.indice = 0

            # Troca a imagem
            # Troca a imagem mantendo o espelhamento e a rotação.
            centro = self.rect.center
            image = self.frames[self.indice]
            image = pygame.transform.scale_by(image, 2.8)
            image = pygame.transform.flip(image, self.flip, False)
            self.image = pygame.transform.rotate(image, self.angulo)
            self.rect = self.image.get_rect(center=centro)

    # Alterna a orientação em 180 graus sem mudar a posição da raposa.
    def girar(self):
        centro = self.rect.center
        self.angulo = (self.angulo + 180) % 360
        self.image = pygame.transform.rotate(self.image, 180)
        self.rect = self.image.get_rect(center=centro)


# Exibe a explosão colorida de um acerto e desaparece ao concluir a animação.
class Splash(pygame.sprite.Sprite):
    # Carrega a sequência de explosão e aplica a cor da nota acertada.
    def __init__(self, x, y, cor):
        super().__init__()

         # Carrega a sequência de imagens da animação.
        self.frames = [pygame.image.load(f'sprites/explosao/explosao_{i}.png').convert_alpha() for i in range(1, 13)]
        self.image = self.frames[0]
        self.image.fill((*cor, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.rect = self.image.get_rect(center = (x, y))

        self.cor = cor
        self.indice = 0
        self.contador = 0

    # Avança a explosão e remove o sprite ao terminar a sequência.
    def update(self):
        self.contador += 1

        if self.contador >= 2:
            self.contador = 0
            self.indice += 1

            # A explosão termina após o último frame; remove o sprite do grupo.
            if self.indice >= len(self.frames):
                self.kill()
                return

            # Troca a imagem
            centro = self.rect.center
            self.image = self.frames[self.indice]
            self.image.fill((*self.cor, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.rect = self.image.get_rect(center=centro)


# Representa a faixa visual do progresso da música no topo da partida.
class Musica(pygame.sprite.Sprite):
    # Carrega e posiciona a imagem da faixa de progresso no topo da tela.
    def __init__(self):
        super().__init__()

        image = pygame.image.load("sprites/musica.png").convert_alpha()
        self.image = pygame.transform.scale(image, (700, 26))
        self.rect = self.image.get_rect(center=(640, 30))


# Exibe um texto temporário com efeito de crescimento, deslocamento e desaparecimento.
class Mensagem(pygame.sprite.Sprite):
    # Renderiza o texto e guarda posição e duração, em milissegundos, para sua animação.
    def __init__(self, texto, x, y, cor, duracao=450):
        super().__init__()
        fonte = pygame.font.Font(c.FONTE_PADRAO, 30)
        self.texto_original = fonte.render(texto, True, cor)
        self.x = x
        self.y = y
        self.inicio = pygame.time.get_ticks()
        self.duracao = duracao
        self.update()

    # Anima escala, subida e opacidade do texto e o remove ao terminar o prazo.
    def update(self, *args):
        tempo = pygame.time.get_ticks() - self.inicio

        if tempo >= self.duracao:
            self.kill()
            return

        if tempo < 100:
            escala = 0.4 + 0.85 * (tempo / 100)
        elif tempo < 200:
            escala = 1.25 - 0.25 * ((tempo - 100) / 100)
        else:
            escala = 1

        largura = max(1, int(self.texto_original.get_width() * escala))
        altura = max(1, int(self.texto_original.get_height() * escala))
        self.image = pygame.transform.scale(self.texto_original, (largura, altura))

        if tempo > 200:
            self.image.set_alpha(int(255 * (self.duracao - tempo) / (self.duracao - 200)))

        self.rect = self.image.get_rect(center=(self.x, self.y - int(20 * tempo / self.duracao)))


# Representa uma mancha colorida usada para atrapalhar a visão do adversário.
class Tinta(pygame.sprite.Sprite):
    # Sorteia o formato e a cor da mancha e a posiciona sobre o tabuleiro atingido.
    def __init__(self, x, y):
        super().__init__()

        self.x = x
        self.y = y
        imagem = random.randint(1, 4)
        image = pygame.image.load(f"sprites/tinta/tinta_{imagem}.png")
        self.image = pygame.transform.scale_by(image, 1.8)

        self.image.fill(
            random.choice([
                (255, 216, 61),
                (45, 211, 159),
                (56, 166, 255),
                (133, 99, 245),
            ]),
            special_flags=pygame.BLEND_RGBA_MULT,
        )

        self.rect = self.image.get_rect(center=(x, y))

        self.tamanho = 1

    # Reduz progressivamente a mancha, mantendo seu centro, até removê-la.
    def update(self):
        if self.tamanho > 0:
            self.tamanho -= 0.0000000001
            self.image = pygame.transform.scale_by(self.image, self.tamanho)
            self.rect = self.image.get_rect(center = (self.x, self.y))
        else:
            self.kill()


# Leva o poder do jogador até o adversário e aplica o efeito quando termina o trajeto.
# Os números de 1 a 4 correspondem a tinta, inversão, roubo e aceleração.
class Bola_de_poder(pygame.sprite.Sprite):
    # Carrega som e frames do projétil e guarda o jogador atacante, a tela e o tipo de poder.
    def __init__(self, x, y, tela_jogo, lado, poder):
        self.dano = pygame.mixer.Sound("efeitos/efeito_003.ogg")
        super().__init__()
        self.x = x
        self.y = y

        self.frames = [pygame.image.load(f"sprites/bola_poder/bola_poder_{i}.png").convert_alpha() for i in range(1, 7)]

        self.image = pygame.image.load("sprites/elemento-centro.png")
        self.rect = self.image.get_rect(center = (x, y))
        self.distancia = 0
        self.tela_jogo = tela_jogo
        self.lado = lado
        self.poder = poder

        fonte = pygame.font.get_default_font()
        self.mensagem = pygame.font.Font(fonte, 30)

        self.contador = 0
        self.indice = 0

    # Move e anima o projétil até aplicar o efeito ao adversário.
    # O roubo reduz pontos e carga e também cancela o poder guardado e seu ícone, mesmo com a barra cheia.
    def update(self):
        self.contador += 1

        if self.contador >= 8:
            self.contador = 0
            self.indice += 1

            # Acabaram os frames: reseta a animação
            if self.indice >= len(self.frames):
                self.indice = 0

            # Troca a imagem
            # Troca a imagem mantendo o espelhamento e a rotação.
            centro = self.rect.center
            image = self.frames[self.indice]
            self.image = image
            self.rect = self.image.get_rect(center=centro)


        if self.lado == 1:
            self.x += 3
        else:
            self.x -= 3
        self.distancia += 3
        self.rect = self.image.get_rect(center = (self.x, self.y))

        if self.distancia >= 740:
            self.dano.play()
            self.kill()
            if self.poder == 1:
                if self.lado == 1:
                    self.tela_jogo.tinta.add(Tinta(random.randint(850, 1010), random.randint(300, 440)))
                    self.tela_jogo.tinta.add(Tinta(random.randint(850, 1010), random.randint(300, 440)))
                    self.tela_jogo.tinta.add(Tinta(random.randint(850, 1010), random.randint(300, 440)))
                    self.tela_jogo.tinta.add(Tinta(random.randint(850, 1010), random.randint(300, 440)))
                    self.tela_jogo.mensagens.add(Mensagem("Tinta no seu focinho!", 930, 250, (0,0,0), duracao=2000))
                if self.lado == 2:
                    self.tela_jogo.tinta.add(Tinta(random.randint(270, 430), random.randint(300, 440)))
                    self.tela_jogo.tinta.add(Tinta(random.randint(270, 430), random.randint(300, 440)))
                    self.tela_jogo.tinta.add(Tinta(random.randint(270, 430), random.randint(300, 440)))
                    self.tela_jogo.tinta.add(Tinta(random.randint(270, 430), random.randint(300, 440)))
                    self.tela_jogo.mensagens.add(Mensagem("Tinta no seu focinho!", 350, 250, (0,0,0), duracao=2000))

            if self.poder == 2:
                self.tela_jogo.control.add(Trocar_controles(self.lado, self.tela_jogo))
                if self.lado == 1:
                    self.tela_jogo.todos.add(Mensagem("Controles invertidos uau!", 930, 250, (0,0,0), duracao=2000))
                if self.lado == 2:
                    self.tela_jogo.todos.add(Mensagem("Controles invertidos uau!", 350, 250, (0,0,0), duracao=2000))

            if self.poder == 3:
                jogador_alvo = 2 if self.lado == 1 else 1
                pontos = getattr(self.tela_jogo, f'pontos_j{jogador_alvo}')
                pontos.pontos -= 20
                pontos.poder = max(0, pontos.poder - 40)
                # O roubo também cancela o poder já sorteado com a barra cheia.
                setattr(self.tela_jogo, f'tem_poder_{jogador_alvo}', None)
                imagem = getattr(self.tela_jogo, f'imagem_poder{jogador_alvo}', None)
                if imagem is not None:
                    imagem.kill()
                    setattr(self.tela_jogo, f'imagem_poder{jogador_alvo}', None)
                x = 930 if jogador_alvo == 2 else 350
                self.tela_jogo.todos.add(Mensagem("Seu poder foi roubado por uma raposa safada!", x, 250, (0,0,0), duracao=2000))

            if self.poder == 4:
                self.tela_jogo.aceleracao.add(Acelerar_nota(self.lado))
                x = 930 if self.lado == 1 else 350
                self.tela_jogo.mensagens.add(Mensagem("VOCÊ é a velocidade!", x, 250, (0,0,0), duracao=2000))


# Mantém temporariamente a inversão dos comandos e da raposa do jogador atingido.
# Efeitos simultâneos não devem desfazer a inversão antes de o último terminar.
class Trocar_controles(pygame.sprite.Sprite):
    # inverte os comandos do adversário por 420 frames
    # Identifica o adversário e inicia a inversão, girando a raposa somente no primeiro efeito ativo.
    def __init__(self, lado, tela_jogo):
        super().__init__()
        self.timer = 0
        self.tela_jogo = tela_jogo
        self.lado = lado
        self.jogador_alvo = 2 if lado == 1 else 1
        self._encerrado = False
        # mantém a inversão até o último efeito acabar
        if not self._outro_efeito_ativo():
            self._raposa_alvo().girar()

    # Retorna a raposa do jogador que recebeu a inversão.
    def _raposa_alvo(self):
        return self.tela_jogo.raposa_2 if self.jogador_alvo == 2 else self.tela_jogo.raposa_1

    # Verifica se ainda existe outra inversão em vigor para o mesmo jogador.
    def _outro_efeito_ativo(self):
        return any((efeito is not self and getattr(efeito, 'jogador_alvo', None) == self.jogador_alvo for efeito in self.tela_jogo.control))

    # Conta os quadros de duração e encerra a inversão ao atingir o limite.
    def update(self):
        self.timer += 1
        if self.timer >= 420:
            self.kill()

    # Remove este efeito e restaura a raposa somente quando não resta outra inversão sobre ela.
    def kill(self):
        if self._encerrado:
            return
        self._encerrado = True
        super().kill()
        if not self._outro_efeito_ativo():
            self._raposa_alvo().girar()


# Exibe a imagem do poder sorteado enquanto ele está disponível para uso.
class Icone(pygame.sprite.Sprite):
    # Escolhe a imagem correspondente ao número do poder e a posiciona junto à barra.
    def __init__(self, x, y, poder):
        super().__init__()

        if poder == 1:
            self.image = pygame.image.load("sprites/power_up_tinta.png")
        if poder == 2:
            self.image = pygame.image.load("sprites/power_up_inverter.png")
        if poder == 3:
            self.image = pygame.image.load("sprites/power_up_roubar.png")
        if poder == 4:
            self.image = pygame.image.load("sprites/power_up_raio.png")

        self.rect = self.image.get_rect(center=(x, y))


# Representa o marcador que avança pela faixa de progresso da música.
class Notinha(pygame.sprite.Sprite):
    # Prepara o marcador musical com posição inicial e avanço horizontal por quadro.
    def __init__(self, x, y, distancia):
        super().__init__()

        image = pygame.image.load('sprites/notinha.png').convert_alpha()
        self.image = pygame.transform.scale(image, (32, 32))
        self.rect = self.image.get_rect(center = (x,y))
        self.distancia = distancia
        self.x = x
        self.y = y

    # Avança o marcador na faixa de progresso conforme a distância definida.
    def update(self):
        self.x += self.distancia
        self.rect = self.image.get_rect(center = (round(self.x),self.y))


# Produz as folhas decorativas que caem e são repostas continuamente.
class Folha(pygame.sprite.Sprite):
    # Sorteia uma posição acima da tela e associa a folha ao grupo decorativo da tela.
    def __init__(self, tela):
        super().__init__()

        self.x = random.randint(0, 1280)
        self.y = random.randint(-500, 0)

        self.image = pygame.image.load("sprites/folha.png")
        self.rect = self.image.get_rect(center = (self.x, self.y))

        self.tela = tela

    # Faz a folha cair e cria uma substituta quando ela sai pela parte inferior.
    def update(self):
        self.y += 1.5
        self.rect = self.image.get_rect(center = (self.x, self.y))

        if self.y > 721:
            self.kill()
            self.tela.todos.add(Folha(self.tela))


# Cria um rastro animado de pegadas, alternando os lados e apagando marcas antigas.
class Pata(pygame.sprite.Sprite):
    # Define direção do rastro, intervalo das pegadas e tempo de desaparecimento das marcas.
    def __init__(self, x, y, rotacao):
        super().__init__()

        image = pygame.image.load("sprites/pata.png").convert_alpha()
        self.original = pygame.transform.scale(image, (24, 24))

        self.posicao = pygame.Vector2(x, y)
        self.rotacao = rotacao
        self.direcao = pygame.Vector2(0, -1).rotate(-rotacao)
        self.lateral = self.direcao.rotate(90)

        self.intervalo = 600 # Tempo entre as pegadas, em ms.
        self.duracao = 6000 # Tempo até uma pegada desaparecer.
        self.passo = 30 # Distância que avança a cada pegada.
        self.separacao = 10 # Distância lateral em relação ao caminho.
        self.lado = 1

        self.pegadas = []
        self.ultima_pegada = pygame.time.get_ticks()

        self.criar_pegada(self.ultima_pegada)
        self.update()

    # Adiciona uma marca alternando o lado e avança a origem para o próximo passo.
    def criar_pegada(self, tempo):
        posicao = self.posicao + self.lateral * self.separacao * self.lado

        image = pygame.transform.flip(self.original, self.lado < 0, False)
        image = pygame.transform.rotate(image, self.rotacao)
        rect = image.get_rect(center=(round(posicao.x), round(posicao.y)))

        self.pegadas.append({'image': image, 'rect': rect, 'inicio': tempo})

        self.posicao += self.direcao * self.passo
        self.lado *= -1

    # Cria as marcas pendentes e reúne as pegadas ainda visíveis em uma imagem com transparência.
    def update(self):
        agora = pygame.time.get_ticks()

        # Cria as próximas pegadas no intervalo definido.
        while agora - self.ultima_pegada >= self.intervalo:
            self.ultima_pegada += self.intervalo
            self.criar_pegada(self.ultima_pegada)

        # Remove as pegadas que já desapareceram.
        self.pegadas = [pegada for pegada in self.pegadas if agora - pegada['inicio'] < self.duracao]

        if not self.pegadas:
            self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
            self.rect = self.image.get_rect(center=(round(self.posicao.x), round(self.posicao.y)))
            return

        # Monta uma imagem transparente contendo o rastro.
        self.rect = self.pegadas[0]['rect'].unionall([pegada['rect'] for pegada in self.pegadas])
        self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)

        for pegada in self.pegadas:
            tempo = agora - pegada['inicio']
            opacidade = int(255 * (1 - tempo / self.duracao))
            pegada['image'].set_alpha(opacidade)

            x = pegada['rect'].x - self.rect.x
            y = pegada['rect'].y - self.rect.y
            self.image.blit(pegada['image'], (x, y))


# Produz o brilho temporário da borda da tela que acompanha as batidas.
class Margem(pygame.sprite.Sprite):
    # Monta a borda com camadas de brilho e registra o tempo inicial do efeito.
    def __init__(self, cor=None, duracao=340):
        super().__init__()

        self.cor = c.COR_PODER if cor is None else cor
        self.duracao = duracao
        self.inicio = pygame.time.get_ticks()

        self.original = pygame.Surface((c.LARGURA_TELA, c.ALTURA_TELA), pygame.SRCALPHA)
        borda = self.original.get_rect().inflate(-20, -20)

        # Cria o brilho ao redor da borda.
        for distancia in range(18, 0, -1):
            opacidade = int(50 * (1 - distancia / 19) ** 2)
            cor_brilho = (*self.cor, opacidade)

            externa = borda.inflate(distancia * 2, distancia * 2)
            interna = borda.inflate(-distancia * 2, -distancia * 2)

            pygame.draw.rect(self.original, cor_brilho, externa, 2, border_radius=20 + distancia)
            pygame.draw.rect(self.original, cor_brilho, interna, 2, border_radius=max(0, 20 - distancia))

        pygame.draw.rect(self.original, (*self.cor, 255), borda, 4, border_radius=20)

        self.update()

    # Encolhe e apaga o brilho gradualmente, removendo o sprite ao acabar a duração.
    def update(self):
        tempo = pygame.time.get_ticks() - self.inicio

        if tempo >= self.duracao:
            self.kill()
            return

        progresso = tempo / self.duracao
        suavizado = 1 - (1 - progresso) ** 2

        # Encolhe um pouco enquanto desaparece.
        escala = 1 - 0.015 * suavizado
        largura = max(1, round(c.LARGURA_TELA * escala))
        altura = max(1, round(c.ALTURA_TELA * escala))

        self.image = pygame.transform.smoothscale(self.original, (largura, altura))
        self.image.set_alpha(int(255 * (1 - suavizado)))
        self.rect = self.image.get_rect(center=(c.LARGURA_TELA // 2, c.ALTURA_TELA // 2))


# Desenha uma onda circular temporária para destacar o poder disponível.
class Pulso(pygame.sprite.Sprite):
    # Prepara a superfície transparente, a cor e os limites de expansão do círculo.
    def __init__(self, x, y, cor=None, duracao=500):
        super().__init__()

        self.cor = c.COR_PODER if cor is None else cor
        self.inicio = pygame.time.get_ticks()
        self.duracao = duracao
        self.raio_inicial = 5
        self.raio_maximo = 100

        tamanho = self.raio_maximo * 2 + 2
        self.image = pygame.Surface((tamanho, tamanho), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))

        self.update()

    # Aumenta o raio e reduz a opacidade até encerrar a onda.
    def update(self):
        tempo = pygame.time.get_ticks() - self.inicio

        if tempo >= self.duracao:
            self.kill()
            return

        progresso = tempo / self.duracao

        # Cresce rapidamente e desacelera perto do final.
        crescimento = 1 - (1 - progresso) ** 2
        raio = round(self.raio_inicial + (self.raio_maximo - self.raio_inicial) * crescimento)
        opacidade = int(200 * (1 - progresso))

        self.image.fill((0, 0, 0, 0))
        pygame.draw.circle(self.image, (*self.cor, opacidade), self.image.get_rect().center, raio)


# Registra por quanto tempo as notas do adversário devem ser lançadas com velocidade maior.
class Acelerar_nota(pygame.sprite.Sprite):
    # Marca o adversário como alvo e registra início e duração da aceleração, em milissegundos.
    def __init__(self, lado, duracao=7500):
        super().__init__()
        self.jogador_alvo = 2 if lado == 1 else 1
        self.inicio = pygame.time.get_ticks()
        self.duracao = duracao

    # Informa se o efeito estará em vigor no instante atual ou após o atraso informado, em milissegundos.
    def ativo(self, atraso=0):
        return pygame.time.get_ticks() + atraso < self.inicio + self.duracao

    # Retira o efeito do grupo assim que o prazo de aceleração termina.
    def update(self):
        if not self.ativo():
            self.kill()
