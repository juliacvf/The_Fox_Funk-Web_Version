# Telas e navegação do jogo, entrada de controles e regras da partida e dos resultados.

import pygame
import constantes as c
import elementos
import random
import unicodedata
from recursos_web import musica_terminou
from funcoes import carregar_musica
from funcoes import tocar_musica_menu
from funcoes import normalizar_nome
from funcoes import texto_com_contorno
from funcoes import texto_com_icone

# comandos do controle
from pygame._sdl2 import controller as sdl_controle


# Centraliza conexão, identificação e leitura dos controles, encaminhando ações à tela ativa.
# Evita comandos duplicados e exige soltar o analógico ao trocar de tela.
class GerenciadorControles:
    # usa o mapeamento do próprio controle
    ZONA_ENTRADA = 0.50
    ZONA_SAIDA = 0.28
    ATRASO_REPETICAO = 330
    INTERVALO_REPETICAO = 150

    # Inicializa os módulos de controle e registra os dispositivos já conectados.
    def __init__(self):
        self.dispositivos = {}
        self.tela_ativa = None
        self.proxima_busca = 0

        pygame.joystick.init()
        sdl_controle.init()

        if hasattr(sdl_controle, 'set_eventstate'):
            sdl_controle.set_eventstate(True)

        for indice in range(sdl_controle.get_count()):
            self.conectar(indice)

    # Associa um controle compatível a um jogador livre e guarda o estado inicial de botões e eixos.
    def conectar(self, indice):
        if not sdl_controle.is_controller(indice):
            return
        joystick = pygame.joystick.Joystick(indice)
        joystick.init()
        identificador = joystick.get_instance_id()
        if identificador in self.dispositivos:
            return
        ocupados = {d['jogador'] for d in self.dispositivos.values()}
        jogador = next((n for n in (1, 2) if n not in ocupados), None)
        if jogador is None:
            return
        controle = sdl_controle.Controller.from_joystick(joystick)
        eixos = {eixo: controle.get_axis(eixo) / 32767.0 for eixo in (
            pygame.CONTROLLER_AXIS_LEFTX, pygame.CONTROLLER_AXIS_LEFTY,
            pygame.CONTROLLER_AXIS_TRIGGERLEFT, pygame.CONTROLLER_AXIS_TRIGGERRIGHT,
        )}
        self.dispositivos[identificador] = {
            'controle': controle, 'joystick': joystick, 'jogador': jogador,
            'botoes': {b for b in self.acoes_botoes() if controle.get_button(b)},
            'eixos': eixos,
            'gatilhos': {e for e in (pygame.CONTROLLER_AXIS_TRIGGERLEFT,
                                    pygame.CONTROLLER_AXIS_TRIGGERRIGHT)
                         if eixos[e] >= self.ZONA_ENTRADA},
            'navegacao': None, 'proxima_repeticao': 0,
            'aguardar_neutro': True,
        }

    # Remove o dispositivo pelo identificador e libera seus recursos de controle e joystick.
    def desconectar(self, identificador):
        dados = self.dispositivos.pop(identificador, None)
        if dados is not None:
            dados['controle'].quit()
            dados['joystick'].quit()

    # Detecta a mudança de tela e reinicia a navegação para não reaproveitar comandos ainda pressionados.
    def ativar_tela(self, tela):
        if self.tela_ativa is tela:
            return
        self.tela_ativa = tela
        for dados in self.dispositivos.values():
            dados['navegacao'] = None
            dados['proxima_repeticao'] = 0
            # espera soltar o analógico ao mudar de tela
            dados['aguardar_neutro'] = True

    # Relaciona os botões físicos do Pygame aos nomes de ações usados pelas telas.
    @staticmethod
    def acoes_botoes():
        return {
            pygame.CONTROLLER_BUTTON_A: 'a',
            pygame.CONTROLLER_BUTTON_B: 'b',
            pygame.CONTROLLER_BUTTON_X: 'x',
            pygame.CONTROLLER_BUTTON_Y: 'y',
            pygame.CONTROLLER_BUTTON_DPAD_UP: 'cima',
            pygame.CONTROLLER_BUTTON_DPAD_DOWN: 'baixo',
            pygame.CONTROLLER_BUTTON_DPAD_LEFT: 'esquerda',
            pygame.CONTROLLER_BUTTON_DPAD_RIGHT: 'direita',
            pygame.CONTROLLER_BUTTON_LEFTSHOULDER: 'lb',
            pygame.CONTROLLER_BUTTON_RIGHTSHOULDER: 'rb',
            pygame.CONTROLLER_BUTTON_START: 'start',
            pygame.CONTROLLER_BUTTON_BACK: 'voltar',
        }

    # Envia a ação somente na passagem de solto para pressionado e libera o estado ao soltar.
    def ler_botao(self, dados, botao, pressionado, tela):
        if not pressionado:
            dados['botoes'].discard(botao)
            liberar = getattr(tela, '_liberar_selecao_neutra', None)
            if liberar is not None:
                liberar()
        elif botao not in dados['botoes']:
            dados['botoes'].add(botao)
            acao = self.acoes_botoes().get(botao)
            if acao is not None:
                tela._comando_controle(acao, dados['jogador'])

    # Converte o eixo do gatilho em uma única ativação de poder por aperto.
    # Usa limiares diferentes para apertar e soltar, evitando disparos por pequenas oscilações.
    def ler_gatilho(self, dados, eixo, valor, tela):
        dados['eixos'][eixo] = valor
        if valor <= self.ZONA_SAIDA:
            dados['gatilhos'].discard(eixo)
        elif valor >= self.ZONA_ENTRADA and eixo not in dados['gatilhos']:
            dados['gatilhos'].add(eixo)
            tela._comando_controle('poder', dados['jogador'])

    # Trata conexão, remoção e eventos de entrada; retorna se o evento pertence ao controle.
    def evento(self, event, tela):
        self.ativar_tela(tela)
        if event.type == pygame.CONTROLLERDEVICEADDED:
            self.conectar(event.device_index)
            return True
        if event.type == pygame.CONTROLLERDEVICEREMOVED:
            self.desconectar(event.instance_id)
            return True
        if event.type == pygame.CONTROLLERDEVICEREMAPPED:
            return True
        if event.type not in (pygame.CONTROLLERBUTTONDOWN,
                              pygame.CONTROLLERBUTTONUP,
                              pygame.CONTROLLERAXISMOTION):
            return False

        dados = self.dispositivos.get(event.instance_id)
        if dados is None:
            return True
        if event.type in (pygame.CONTROLLERBUTTONDOWN, pygame.CONTROLLERBUTTONUP):
            self.ler_botao(dados, event.button, event.type == pygame.CONTROLLERBUTTONDOWN, tela)
            return True

        valor = event.value / 32767.0
        dados['eixos'][event.axis] = valor
        if event.axis in (pygame.CONTROLLER_AXIS_TRIGGERLEFT,
                          pygame.CONTROLLER_AXIS_TRIGGERRIGHT):
            self.ler_gatilho(dados, event.axis, valor, tela)
        return True

    # Consulta os dispositivos a cada quadro e repete a navegação quando o analógico fica inclinado.
    # Durante a partida, as notas dependem dos botões; o analógico não repete comandos de jogo.
    def atualizar(self, tela):
        self.ativar_tela(tela)
        # lê os botões a cada frame sem repetir os comandos recebidos por evento
        pygame.event.pump()
        agora = pygame.time.get_ticks()
        if agora >= self.proxima_busca:
            for indice in range(sdl_controle.get_count()):
                self.conectar(indice)
            self.proxima_busca = agora + 1000
        for dados in list(self.dispositivos.values()):
            if not dados['controle'].attached():
                self.desconectar(dados['joystick'].get_instance_id())
                continue
            for botao in self.acoes_botoes():
                self.ler_botao(dados, botao, dados['controle'].get_button(botao), tela)
            for gatilho in (pygame.CONTROLLER_AXIS_TRIGGERLEFT,
                             pygame.CONTROLLER_AXIS_TRIGGERRIGHT):
                self.ler_gatilho(dados, gatilho, dados['controle'].get_axis(gatilho) / 32767.0, tela)
            # permite continuar navegando com o analógico segurado
            x = dados['controle'].get_axis(pygame.CONTROLLER_AXIS_LEFTX) / 32767.0
            y = dados['controle'].get_axis(pygame.CONTROLLER_AXIS_LEFTY) / 32767.0
            if dados['aguardar_neutro']:
                if max(abs(x), abs(y)) <= self.ZONA_SAIDA:
                    dados['aguardar_neutro'] = False
                continue
            if isinstance(tela, Tela_Jogo):
                continue
            limite = self.ZONA_SAIDA if dados['navegacao'] else self.ZONA_ENTRADA
            if max(abs(x), abs(y)) < limite:
                dados['navegacao'] = None
                continue
            if abs(x) > abs(y):
                acao = 'direita' if x > 0 else 'esquerda'
            else:
                acao = 'baixo' if y > 0 else 'cima'
            mudou = acao != dados['navegacao']
            if mudou or agora >= dados['proxima_repeticao']:
                tela._comando_controle(acao, dados['jogador'])
                dados['navegacao'] = acao
                dados['proxima_repeticao'] = agora + (self.ATRASO_REPETICAO if mudou else self.INTERVALO_REPETICAO)

_gerenciador_controles = None


# Reúne os recursos de controle compartilhados pelas telas: entrada, jogador do teclado e indicação do filtro.
class TelaComControle:
    # Reutiliza o gerenciador compartilhado e inicializa foco, seleção e recursos de indicação.
    def _iniciar_controle(self):
        global _gerenciador_controles
        if _gerenciador_controles is None or not sdl_controle.get_init():
            _gerenciador_controles = GerenciadorControles()
        self._controles = _gerenciador_controles
        self._foco_controle = 0
        self._jogador_selecao = 1
        self._aviso_controle = ''
        self._aviso_ate = 0
        self._fonte_controle = pygame.font.Font(c.FONTE_PADRAO, 17)

    # Entrega o evento ao gerenciador e informa se ele já foi tratado como entrada de controle.
    def _evento_controle(self, event):
        return self._controles.evento(event, self)

    # Atualiza a leitura contínua dos controles para esta tela.
    def _atualizar_controle(self):
        self._controles.atualizar(self)

    # Com um único controle, destina o teclado ao jogador que ficou sem dispositivo.
    # Nos demais casos, mantém o jogador indicado pelo conjunto de teclas usado.
    def _jogador_teclado(self, jogador_padrao):
        dispositivos = list(self._controles.dispositivos.values())
        if len(dispositivos) == 1:
            # o teclado fica com o jogador que está sem controle
            return 3 - dispositivos[0]['jogador']
        return jogador_padrao

    # Registra um aviso temporário e seu prazo; não desenha a antiga faixa de mensagens.
    def _avisar_controle(self, mensagem):
        self._aviso_controle = mensagem
        self._aviso_ate = pygame.time.get_ticks() + 4500

    # Desenha apenas o X ao lado do filtro de músicas quando existe um controle conectado.
    def _desenhar_controle(self, window):
        if isinstance(self, Tela_Musicas) and self._controles.dispositivos:
            imagem = self._fonte_controle.render('X', True, c.COR_TEXTO)
            rect = imagem.get_rect(midleft=(self.rect_ordenacao.right + 8, self.rect_ordenacao.centery))
            window.blit(imagem, rect)


# Apresenta o menu inicial, suas animações e os caminhos para músicas e instruções.
class Tela_Inicial(TelaComControle):
    # Retoma a música do menu e reinicia o estado visual da logo ao voltar a esta tela.
    def ao_entrar(self):
        tocar_musica_menu()
        self.indice_logo = 0

    # Carrega fundo, logo, textos, sons e sprites decorativos do menu inicial.
    def __init__(self):
        self.click = pygame.mixer.Sound("efeitos/efeito_006.ogg")

        self.fundo = pygame.image.load("sprites/fundo_menu.png")
        logo = pygame.image.load("sprites/logo_paleta_jogo.png").convert_alpha()

        # Remove as margens transparentes antes de ajustar a logo ao menu.
        logo = logo.subsurface(logo.get_bounding_rect(min_alpha=64)).copy()
        escala = min(560 / logo.get_width(), 330 / logo.get_height())
        self.logo = pygame.transform.smoothscale(logo, (round(logo.get_width() * escala), round(logo.get_height() * escala)))

        # Prepara os tamanhos da logo para o pulso.
        self.logos_pulso = [self.logo]

        for i in range(1, 9):
            escala = 1 + 0.04 * i / 8
            tamanho = (round(self.logo.get_width() * escala), round(self.logo.get_height() * escala))
            self.logos_pulso.append(pygame.transform.smoothscale(self.logo, tamanho))

        self.intervalo_pulso = 60000 / 110
        self.duracao_pulso = 220
        self.indice_logo = 0

        self.fonte_mensagens = pygame.font.Font(c.FONTE_MENSAGENS, 20)
        mensagens = [
            'Para jogar - teclado: espaço / controle: A',
            'Instruções - teclado: I / controle: X',
        ]
        self.textos_atalhos = [
            self.fonte_mensagens.render(mensagem, True, (0, 0, 0))
            for mensagem in mensagens
        ]

        # Centraliza a composição inteira: logo, respiro e as duas linhas.
        espaco_logo = 30
        espaco_linhas = 6
        altura_bloco = self.logo.get_height() + espaco_logo + sum(texto.get_height() for texto in self.textos_atalhos) + espaco_linhas
        topo_bloco = (c.ALTURA_TELA - altura_bloco) // 2
        self.posicao_logo = self.logo.get_rect(midtop=(c.LARGURA_TELA // 2, topo_bloco))

        self.posicoes_atalhos = []
        y = self.posicao_logo.bottom + espaco_logo

        for texto in self.textos_atalhos:
            posicao = texto.get_rect(midtop=(c.LARGURA_TELA // 2, y))
            self.posicoes_atalhos.append(posicao)
            y = posicao.bottom + espaco_linhas

        self.abrir_jogo = False
        self.abrir_instrucoes = False
        self.reiniciar_patas = False

        self.todos = pygame.sprite.Group()

        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))

        self.criar_patas()

        self._iniciar_controle()

    # Substitui os rastros de pegadas para recomeçar sua animação no menu.
    def criar_patas(self):
        for sprite in self.todos.sprites():
            if isinstance(sprite, elementos.Pata):
                sprite.kill()

        self.todos.add(elementos.Pata(900, 600, 50))
        self.todos.add(elementos.Pata(300, 800, -50))
        self.todos.add(elementos.Pata(1180, 250, -200))

    # Desenha o fundo, as folhas, as pegadas, a logo e os atalhos do menu.
    def desenha(self, window):
        window.fill(c.COR_FUNDO)
        window.blit(self.fundo, (0, 0))
        pygame.draw.rect(window, c.COR_CREME_CLARO, (0, 0, c.LARGURA_TELA, c.ALTURA_TELA), 5)

        self.todos.draw(window)

        logo = self.logos_pulso[self.indice_logo]
        posicao = logo.get_rect(center=self.posicao_logo.center)
        window.blit(logo, posicao)

        for texto, posicao in zip(self.textos_atalhos, self.posicoes_atalhos):
            window.blit(texto, posicao)

    # Atualiza as animações, pulsa a logo no ritmo e abre a tela solicitada pelo jogador.
    def atualiza(self, jogo):
        self._atualizar_controle()

        if self.reiniciar_patas:
            self.criar_patas()
            self.reiniciar_patas = False

        self.todos.update()

        # Aumenta na batida e retorna suavemente ao tamanho original.
        tempo = pygame.mixer.music.get_pos()
        self.indice_logo = 0

        if tempo >= 0:
            tempo_batida = tempo % self.intervalo_pulso

            if tempo_batida < self.duracao_pulso:
                progresso = tempo_batida / self.duracao_pulso
                self.indice_logo = round((len(self.logos_pulso) - 1) * (1 - progresso) ** 2)

        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        if self.abrir_jogo:
            self.abrir_jogo = False
            self.abrir_instrucoes = False
            self.reiniciar_patas = True
            jogo.tela_atual = Tela_Musicas(tela_anterior=self)

        elif self.abrir_instrucoes:
            self.abrir_instrucoes = False
            self.reiniciar_patas = True
            jogo.tela_atual = Tela_Instrucoes(self)

    # Recebe o controle ou os atalhos de teclado para jogar e consultar instruções.
    def tratar_eventos(self, event):
        if self._evento_controle(event):
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.click.play()
                self.abrir_jogo = True
            elif event.key == pygame.K_i:
                self.click.play()
                self.abrir_instrucoes = True

    # Usa A para abrir as músicas e X para abrir as instruções.
    def _comando_controle(self, acao, jogador):
        if acao == 'a':
            self.click.play()
            self.abrir_jogo = True
        elif acao == 'x':
            self.click.play()
            self.abrir_instrucoes = True


# Organiza e exibe as regras e os comandos, permitindo retornar à tela anterior.
class Tela_Instrucoes(TelaComControle):
    # Prepara a tela de ajuda, suas fontes e áreas de desenho, guardando a tela de retorno.
    def __init__(self, tela_anterior=None):
        self.click = pygame.mixer.Sound("efeitos/efeito_006.ogg")
        self.tela_anterior = tela_anterior
        self.voltar_tela = False
        self.titulo = pygame.font.Font(c.FONTE_TITULOS, 28)
        self.fonte_botoes = pygame.font.Font(c.FONTE_PADRAO, 23)
        self.voltar = pygame.Rect(30, 25, 130, 40)
        self.fundo = pygame.image.load('sprites/fundo_instrucoes.png')
        self.fundo = pygame.transform.smoothscale(self.fundo, (c.LARGURA_TELA, c.ALTURA_TELA))

        # Mesmo preenchimento, texto e borda das caixas dos nomes.
        self.caixa = pygame.Rect(0, 0, 880, 440)
        self.caixa.center = (c.LARGURA_TELA // 2, c.ALTURA_TELA // 2)
        self.cabecalho = pygame.Rect(self.caixa.x, self.caixa.y, self.caixa.width, 56)
        self.rodape = pygame.Rect(self.caixa.x, self.caixa.bottom - 52, self.caixa.width, 52)
        self.textos = []
        self.divisorias = []
        # Ajusta pela altura real da fonte do projeto, mantendo tudo na caixa.
        for tamanho in (19, 18, 17, 16):
            self.fonte = pygame.font.Font(c.FONTE_PADRAO, tamanho)
            self.fonte_secoes = pygame.font.Font(c.FONTE_PADRAO, tamanho + 2)
            self.textos.clear()
            self.divisorias.clear()
            fim_textos = self.preparar_instrucoes()
            if fim_textos <= self.rodape.top - 12:
                break

        self._iniciar_controle()

    # Quebra o texto sem cortar palavras, armazena as linhas renderizadas e retorna o próximo y livre.
    def adicionar_texto(self, mensagem, fonte, x, y, largura, cor=None):
        if cor is None:
            cor = c.COR_TEXTO
        # Quebra as frases pela largura real da fonte, sem cortar palavras.
        linhas = []
        linha = ''
        for palavra in mensagem.split():
            tentativa = f'{linha} {palavra}'.strip()
            if linha and fonte.size(tentativa)[0] > largura:
                linhas.append(linha)
                linha = palavra
            else:
                linha = tentativa
        if linha:
            linhas.append(linha)

        altura_linha = max(21, fonte.get_linesize() + 2)
        for linha in linhas:
            imagem = fonte.render(linha, True, cor)
            self.textos.append((imagem, imagem.get_rect(midtop=(x + largura // 2, y))))
            y += altura_linha
        return y

    # Acrescenta um título sublinhado e seus parágrafos e retorna o próximo y livre.
    def adicionar_secao(self, titulo, paragrafos, x, y, largura):
        y = self.adicionar_texto(titulo, self.fonte_secoes, x, y, largura) + 6
        # Um sublinhado curto, com a largura do título e centralizado com ele.
        rect_titulo = self.textos[-1][1]
        self.divisorias.append(((rect_titulo.left, rect_titulo.bottom + 2), (rect_titulo.right, rect_titulo.bottom + 2), 2))
        for paragrafo in paragrafos:
            y = self.adicionar_texto(paragrafo, self.fonte, x, y, largura, c.COR_TEXTO_SUAVE) + 4
        return y

    # Distribui as regras, os comandos e as explicações de poderes nas colunas de instruções.
    def preparar_instrucoes(self):
        margem = 24
        x = self.caixa.left + margem
        largura = self.caixa.width - 2 * margem
        y = self.cabecalho.bottom + 12
        y = self.adicionar_texto('Escolham a música, os personagens e os nomes dos jogadores.', self.fonte, x, y, largura)
        y = self.adicionar_texto('Pronto: A no controle; E ou Enter no teclado!', self.fonte, x, y + 2, largura)

        limites = (self.caixa.left + 3, self.caixa.right - 3)
        self.divisorias.append(((limites[0], y + 9), (limites[1], y + 9), 1))
        topo = y + 23
        espaco = 36
        largura_coluna = (largura - espaco) // 2
        x_direita = x + largura_coluna + espaco
        teclas = [pygame.key.name(tecla).upper() for tecla in (pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d)]

        y_controles = self.adicionar_secao('Controles', [
            f'Teclado: J1 = {"/".join(teclas)}; J2 = setas.',
            'Controle: Y/cima, X/esquerda, A/baixo e B/direita.',
            'O direcional também acerta as notas.',
            'Com 1 controle, o teclado fica com o outro jogador.',
            'Apertem a direção quando a nota chegar à seta.'
        ], x, topo, largura_coluna)
        y_pontuacao = self.adicionar_secao('Pontuação', [
            'Acerto perfeito: 5 pontos.',
            'Acerto bom: 3 pontos.',
            'Erro: perde 10 pontos de poder.'
        ], x_direita, topo, largura_coluna)

        topo_poder = y_controles + 15
        y_poder = self.adicionar_secao('Poder especial', [
            'Barra cheia: E (J1) ou Enter (J2).',
            'Controle: LT/RT. Modo misto: E ou Enter.'
        ], x, topo_poder, largura_coluna)
        # Mantém o objetivo perto da pontuação, sem o grande vazio entre eles.
        topo_objetivo = y_pontuacao + 20
        y_objetivo = self.adicionar_secao('Objetivo', [
            'Vence quem tiver mais pontos no fim da música!'
        ], x_direita, topo_objetivo, largura_coluna)

        fim = max(y_poder, y_objetivo)
        self.divisorias.append(((self.caixa.centerx, topo), (self.caixa.centerx, self.rodape.top - 12), 1))
        rodape = self.rodape.top
        self.divisorias.append(((limites[0], rodape), (limites[1], rodape), 1))
        inicio_rodape = len(self.textos)
        self.adicionar_texto('Esc ou Start encerra a partida.', self.fonte, x, rodape, largura)
        textos_rodape = self.textos[inicio_rodape:]
        bloco = textos_rodape[0][1].unionall([rect for _, rect in textos_rodape])
        deslocamento = self.rodape.centery - bloco.centery
        for _, rect in textos_rodape:
            rect.move_ip(0, deslocamento)
        return fim

    # Desenha o painel de instruções, os textos preparados e o botão de voltar.
    def desenha(self, window):
        window.fill(c.COR_FUNDO)
        window.blit(self.fundo, (0, 0))
        pygame.draw.rect(window, c.COR_CREME_CLARO, (0, 0, c.LARGURA_TELA, c.ALTURA_TELA), 5)

        pygame.draw.rect(window, c.COR_CAIXA, self.caixa)
        pygame.draw.rect(window, c.COR_BORDA_CAIXAS, self.caixa, 3)
        pygame.draw.line(window, c.COR_BORDA_CAIXAS,
                         (self.caixa.left, self.cabecalho.bottom),
                         (self.caixa.right - 1, self.cabecalho.bottom), 3)

        titulo = self.titulo.render('Como jogar', True, c.COR_TITULO)
        window.blit(titulo, titulo.get_rect(center=self.cabecalho.center))

        for inicio, fim, espessura in self.divisorias:
            pygame.draw.line(window, c.COR_BORDA_CAIXAS, inicio, fim, espessura)
        for imagem, posicao in self.textos:
            window.blit(imagem, posicao)

        cor_botao = c.COR_BOTAO_HOVER if self.voltar.collidepoint(pygame.mouse.get_pos()) else c.COR_BOTAO
        pygame.draw.rect(window, cor_botao, self.voltar)
        pygame.draw.rect(window, c.COR_BORDA_ESCURA, self.voltar, 2)
        texto = self.fonte_botoes.render('Voltar', True, c.COR_TEXTO)
        window.blit(texto, texto.get_rect(center=self.voltar.center))

        self._desenhar_controle(window)


    # Recebe os eventos de controle e o clique no botão de retorno.
    def tratar_eventos(self, event):
        if self._evento_controle(event):
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.voltar.collidepoint(event.pos):
                self.click.play()
                self.voltar_tela = True

    # Atualiza os controles e o cursor e executa o retorno solicitado.
    def atualiza(self, jogo):
        self._atualizar_controle()
        pode_clicar = self.voltar.collidepoint(pygame.mouse.get_pos())
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if pode_clicar else pygame.SYSTEM_CURSOR_ARROW)

        if self.voltar_tela:
            self.voltar_tela = False
            jogo.tela_atual = self.tela_anterior if self.tela_anterior is not None else Tela_Inicial()

    # Interpreta A ou B como solicitação para voltar à tela anterior.
    def _comando_controle(self, acao, jogador):
        if acao in ('a', 'b', 'start', 'voltar'):
            self.click.play()
            self.voltar_tela = True


# Cuida do catálogo, da ordenação, da rolagem e da prévia de áudio da música escolhida.
# Encaminha a seleção para os personagens e preserva os dados da sessão nas revanches.
class Tela_Musicas(TelaComControle):
    # Reinicia o estado da prévia e retoma o áudio do menu ao entrar novamente na seleção.
    def ao_entrar(self):
        tocar_musica_menu()
        self.previa_atual = None
        self.arraste_barra = None

    # Carrega o catálogo e prepara os painéis, a ordenação e a rolagem da lista.
    # Em cada música, duracao está em segundos e inicio representa a fase da batida em milissegundos.
    def __init__(self, sessao=None, tela_anterior=None):
        self.click = pygame.mixer.Sound("efeitos/efeito_006.ogg")
        self.passar = pygame.mixer.Sound("efeitos/efeito_002.ogg")
        self.sessao = sessao
        self.tela_anterior = tela_anterior
        self.voltar_tela = False
        self.voltar = pygame.Rect(30, 25, 130, 40)
        self.titulo = pygame.font.Font(c.FONTE_TITULOS, 40)

        mensagem_titulo = "Selecione a MÚSICA"
        self.imagem_titulo = self.titulo.render(mensagem_titulo, True, c.COR_BORDA_CAIXAS)
        titulo_destaque = self.titulo.render(mensagem_titulo, True, c.COR_TITULO)

        inicio_destaque = self.titulo.size("Selecione a")[0] + self.titulo.size(" ")[0] // 2
        area_destaque = pygame.Rect(inicio_destaque, 0, self.imagem_titulo.get_width() - inicio_destaque, self.imagem_titulo.get_height())
        self.imagem_titulo.fill((0, 0, 0, 0), area_destaque)
        self.imagem_titulo.blit(titulo_destaque, area_destaque, area_destaque)
        self.rect_titulo = self.imagem_titulo.get_rect(center=(350, 80))
        self.rect_faixa_titulo = self.rect_titulo.inflate(36, 20)

        self.musicas = pygame.font.Font(c.FONTE_PADRAO, 27)
        self.artistas = pygame.font.Font(c.FONTE_PADRAO, 20)
        self.informacoes = pygame.font.Font(c.FONTE_MENSAGENS, 20)
        self.fonte_simbolos = pygame.font.Font(c.FONTE_SIMBOLOS, 20)

        self.fonte_ordenacao = pygame.font.Font(c.FONTE_PADRAO, 20)
        self.rect_ordenacao = pygame.Rect(601, self.rect_titulo.centery - 18, 36, 36)
        self.menu_ordenacao_aberto = False
        self.ordenacao = 'dificuldade'
        self.opcoes_ordenacao = [('dificuldade', 'Dificuldade (BPM)'), ('artista', 'Artista (A–Z)'), ('nome', 'Música (A–Z)')]
        self.rect_menu_ordenacao = pygame.Rect(self.rect_ordenacao.right - 220, self.rect_ordenacao.bottom + 8, 220, 154)
        self.rects_opcoes_ordenacao = [
            pygame.Rect(self.rect_menu_ordenacao.x + 6, self.rect_menu_ordenacao.y + 34 + 38 * i, 208, 36)
            for i in range(len(self.opcoes_ordenacao))
        ]

        vinil = pygame.image.load('sprites/vinil.png').convert_alpha()
        self.vinil = pygame.transform.scale(vinil, (round(vinil.get_width() * 390 / vinil.get_height()), 390))
        self.rect_vinil = self.vinil.get_rect(center=(950, 390))

        self.proximo = pygame.font.Font(c.FONTE_PADRAO, 23)
        self.rect_proximo = pygame.Rect(1100, 630, 130, 40)

        self.lista_musicas = [
            # ★☆☆☆☆
            {"nome": "24K Magic", "artista": "Bruno Mars", "bpm": 107, "dificuldade": "★☆☆☆☆", "duracao": 226.6, "inicio": 13, "link": "musicas/faixa_028.ogg"},
            {"nome": "Cheia de Manias", "artista": "Raça Negra", "bpm": 100, "dificuldade": "★☆☆☆☆", "duracao": 240, "inicio": 206, "link": "musicas/faixa_084.ogg"},
            {"nome": "Chora, Me Liga", "artista": "João Bosco e Vinícius", "bpm": 98, "dificuldade": "★☆☆☆☆", "duracao": 181.1, "inicio": 551, "link": "musicas/faixa_052.ogg"},
            {"nome": "Deixa Acontecer", "artista": "Grupo Revelação", "bpm": 93, "dificuldade": "★☆☆☆☆", "duracao": 240, "inicio": 538, "link": "musicas/faixa_044.ogg"},
            {"nome": "Detroit Rock City", "artista": "KISS", "bpm": 91, "dificuldade": "★☆☆☆☆", "duracao": 222.0, "inicio": 373, "link": "musicas/faixa_056.ogg"},
            {"nome": "Espresso", "artista": "Sabrina Carpenter", "bpm": 104, "dificuldade": "★☆☆☆☆", "duracao": 200.7, "inicio": 245, "link": "musicas/faixa_089.ogg"},
            {"nome": "Hey There Delilah", "artista": "Plain White T's", "bpm": 104, "dificuldade": "★☆☆☆☆", "duracao": 236.5, "inicio": 66, "link": "musicas/faixa_077.ogg"},
            {"nome": "Iris", "artista": "Goo Goo Dolls", "bpm": 103, "dificuldade": "★☆☆☆☆", "duracao": 240, "inicio": 2, "link": "musicas/faixa_039.ogg"},
            {"nome": "It's Time (Grazi)", "artista": "Imagine Dragons", "bpm": 105, "dificuldade": "★☆☆☆☆", "duracao": 233.5, "inicio": 280, "link": "musicas/faixa_049.ogg"},
            {"nome": "Meu Erro", "artista": "Os Paralamas do Sucesso", "bpm": 104, "dificuldade": "★☆☆☆☆", "duracao": 208.7, "inicio": 490, "link": "musicas/faixa_065.ogg"},
            {"nome": "Play", "artista": "Alan Walker", "bpm": 102, "dificuldade": "★☆☆☆☆", "duracao": 168.1, "inicio": 284, "link": "musicas/faixa_014.ogg"},
            {"nome": "Só Por Uma Noite", "artista": "Charlie Brown Jr.", "bpm": 109, "dificuldade": "★☆☆☆☆", "duracao": 203.1, "inicio": 20, "link": "musicas/faixa_031.ogg"},
            {"nome": "The Kids Aren't Alright", "artista": "The Offspring", "bpm": 100, "dificuldade": "★☆☆☆☆", "duracao": 179.7, "inicio": 410, "link": "musicas/faixa_098.ogg"},
            {"nome": "Vícios & Virtudes (Acústico MTV)", "artista": "Charlie Brown Jr.", "bpm": 93, "dificuldade": "★☆☆☆☆", "duracao": 190.0, "inicio": 346, "link": "musicas/faixa_032.ogg"},
            {"nome": "Watermelon Sugar", "artista": "Harry Styles", "bpm": 95.5, "dificuldade": "★☆☆☆☆", "duracao": 177.1, "inicio": 22, "link": "musicas/faixa_047.ogg"},
            {"nome": "Everybody (Backstreet's Back)", "artista": "Backstreet Boys", "bpm": 108.037, "dificuldade": "★☆☆☆☆", "duracao": 230.1, "inicio": 221, "link": "musicas/faixa_018.ogg"},
            {"nome": "I Love Rock 'N Roll", "artista": "Joan Jett & the Blackhearts", "bpm": 92.769, "dificuldade": "★☆☆☆☆", "duracao": 178.1, "inicio": 313, "link": "musicas/faixa_051.ogg"},
            {"nome": "Teto de Vidro", "artista": "Pitty", "bpm": 95.988, "dificuldade": "★☆☆☆☆", "duracao": 212.7, "inicio": 387, "link": "musicas/faixa_076.ogg"},

            # ★★☆☆☆
            {"nome": "Bad Romance", "artista": "Lady Gaga", "bpm": 119, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 267, "link": "musicas/faixa_019.ogg"},
            {"nome": "Beatriz", "artista": "2ZDinizz", "bpm": 120, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 387, "link": "musicas/faixa_010.ogg"},
            {"nome": "Billie Jean", "artista": "Michael Jackson", "bpm": 117, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 227, "link": "musicas/faixa_066.ogg"},
            {"nome": "Champanhe e Água Benta", "artista": "Charlie Brown Jr.", "bpm": 115, "dificuldade": "★★☆☆☆", "duracao": 151.4, "inicio": 300, "link": "musicas/faixa_030.ogg"},
            {"nome": "Heaven Can Wait", "artista": "Michael Jackson", "bpm": 117, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 448, "link": "musicas/faixa_069.ogg"},
            {"nome": "Just Dance", "artista": "Lady Gaga", "bpm": 119, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 448, "link": "musicas/faixa_053.ogg"},
            {"nome": "O Que É, O Que É?", "artista": "Gonzaguinha", "bpm": 112, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 353, "link": "musicas/faixa_073.ogg"},
            {"nome": "Off the Wall", "artista": "Michael Jackson", "bpm": 119, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 62, "link": "musicas/faixa_067.ogg"},
            {"nome": "Paparazzi", "artista": "Lady Gaga", "bpm": 115, "dificuldade": "★★☆☆☆", "duracao": 208.4, "inicio": 325, "link": "musicas/faixa_057.ogg"},
            {"nome": "Poker Face", "artista": "Lady Gaga", "bpm": 119, "dificuldade": "★★☆☆☆", "duracao": 213.8, "inicio": 466, "link": "musicas/faixa_058.ogg"},
            {"nome": "The Way It Is", "artista": "Bruce Hornsby and the Range", "bpm": 111, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 355, "link": "musicas/faixa_101.ogg"},
            {"nome": "Thriller", "artista": "Michael Jackson", "bpm": 118, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 178, "link": "musicas/faixa_068.ogg"},
            {"nome": "Uptown Funk", "artista": "Bruno Mars", "bpm": 115, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 437, "link": "musicas/faixa_061.ogg"},
            {"nome": "Dancin (KRONO Remix)", "artista": "Aaron Smith", "bpm": 119.997, "dificuldade": "★★☆☆☆", "duracao": 198.1, "inicio": 240, "link": "musicas/faixa_013.ogg"},
            {"nome": "It's My Life", "artista": "Bon Jovi", "bpm": 119.982, "dificuldade": "★★☆☆☆", "duracao": 224.6, "inicio": 116, "link": "musicas/faixa_023.ogg"},
            {"nome": "Should I Stay or Should I Go", "artista": "The Clash", "bpm": 113.681, "dificuldade": "★★☆☆☆", "duracao": 193.4, "inicio": 302, "link": "musicas/faixa_096.ogg"},
            {"nome": "Smells Like Teen Spirit", "artista": "Nirvana", "bpm": 116.103, "dificuldade": "★★☆☆☆", "duracao": 240, "inicio": 146, "link": "musicas/faixa_070.ogg"},

            # ★★★☆☆
            {"nome": "Alô Ambev", "artista": "Zé Neto e Cristiano", "bpm": 122, "dificuldade": "★★★☆☆", "duracao": 169.5, "inicio": 479, "link": "musicas/faixa_108.ogg"},
            {"nome": "Baby", "artista": "Justin Bieber", "bpm": 130, "dificuldade": "★★★☆☆", "duracao": 193.4, "inicio": 270, "link": "musicas/faixa_054.ogg"},
            {"nome": "Believer", "artista": "Imagine Dragons", "bpm": 125, "dificuldade": "★★★☆☆", "duracao": 202.6, "inicio": 14, "link": "musicas/faixa_048.ogg"},
            {"nome": "Blue", "artista": "Eiffel 65", "bpm": 128, "dificuldade": "★★★☆☆", "duracao": 240, "inicio": 447, "link": "musicas/faixa_034.ogg"},
            {"nome": "Bourgeois Jouissent (Luís)", "artista": "Felhur x Andro", "bpm": 125, "dificuldade": "★★★☆☆", "duracao": 130.6, "inicio": 26, "link": "musicas/faixa_037.ogg"},
            {"nome": "Burn the Witch (Dani)", "artista": "Queens of the Stone Age", "bpm": 122, "dificuldade": "★★★☆☆", "duracao": 218.3, "inicio": 300, "link": "musicas/faixa_081.ogg"},
            {"nome": "Cry for you", "artista": "September", "bpm": 130, "dificuldade": "★★★☆☆", "duracao": 213.7, "inicio": 221, "link": "musicas/faixa_091.ogg"},
            {"nome": "Descer Pra BC", "artista": "Brenno e Matheus", "bpm": 124, "dificuldade": "★★★☆☆", "duracao": 172.1, "inicio": 337, "link": "musicas/faixa_026.ogg"},
            {"nome": "Don't Stop the Music", "artista": "Rihanna", "bpm": 123, "dificuldade": "★★★☆☆", "duracao": 233.3, "inicio": 383, "link": "musicas/faixa_086.ogg"},
            {"nome": "Manchild", "artista": "Sabrina Carpenter", "bpm": 123, "dificuldade": "★★★☆☆", "duracao": 213.8, "inicio": 444, "link": "musicas/faixa_090.ogg"},
            {"nome": "More Than You Know", "artista": "Axwell Λ Ingrosso", "bpm": 123, "dificuldade": "★★★☆☆", "duracao": 203.1, "inicio": 213, "link": "musicas/faixa_017.ogg"},
            {"nome": "O Nosso Amor a Gente Inventa", "artista": "Cazuza", "bpm": 122, "dificuldade": "★★★☆☆", "duracao": 213.1, "inicio": 193, "link": "musicas/faixa_072.ogg"},
            {"nome": "Only Girl", "artista": "Rihanna", "bpm": 126, "dificuldade": "★★★☆☆", "duracao": 240, "inicio": 177, "link": "musicas/faixa_087.ogg"},
            {"nome": "Sweet Child O' Mine", "artista": "Guns N' Roses", "bpm": 124, "dificuldade": "★★★☆☆", "duracao": 240, "inicio": 314, "link": "musicas/faixa_045.ogg"},
            {"nome": "Telephone", "artista": "Lady Gaga ft. Beyoncé", "bpm": 122, "dificuldade": "★★★☆☆", "duracao": 220.4, "inicio": 375, "link": "musicas/faixa_059.ogg"},
            {"nome": "The Fate Of Ophelia", "artista": "Taylor Swift", "bpm": 124, "dificuldade": "★★★☆☆", "duracao": 226.3, "inicio": 14, "link": "musicas/faixa_093.ogg"},
            {"nome": "What Does The Fox Say", "artista": "Ylvis", "bpm": 128, "dificuldade": "★★★☆☆", "duracao": 224.8, "inicio": 255, "link": "musicas/faixa_107.ogg"},
            {"nome": "You Give Love A Bad Name", "artista": "Bon Jovi", "bpm": 123, "dificuldade": "★★★☆☆", "duracao": 224.4, "inicio": 277, "link": "musicas/faixa_025.ogg"},
            {"nome": "You Shook Me All Night Long", "artista": "AC/DC", "bpm": 128, "dificuldade": "★★★☆☆", "duracao": 208.2, "inicio": 442, "link": "musicas/faixa_012.ogg"},
            {"nome": "Livin' on a Prayer", "artista": "Bon Jovi", "bpm": 121.976, "dificuldade": "★★★☆☆", "duracao": 240, "inicio": 269, "link": "musicas/faixa_024.ogg"},
            {"nome": "Moves Like Jagger", "artista": "Maroon 5 ft. Christina Aguilera", "bpm": 127.976, "dificuldade": "★★★☆☆", "duracao": 201.0, "inicio": 221, "link": "musicas/faixa_062.ogg"},

            # ★★★★☆
            {"nome": "Backyard Boy", "artista": "Claire Rosinkranz", "bpm": 138, "dificuldade": "★★★★☆", "duracao": 129.0, "inicio": 261, "link": "musicas/faixa_033.ogg"},
            {"nome": "Exagerado", "artista": "Cazuza", "bpm": 136, "dificuldade": "★★★★☆", "duracao": 223.7, "inicio": 273, "link": "musicas/faixa_035.ogg"},
            {"nome": "Gangnam Style", "artista": "PSY", "bpm": 132, "dificuldade": "★★★★☆", "duracao": 226.2, "inicio": 165, "link": "musicas/faixa_075.ogg"},
            {"nome": "Infinita Highway", "artista": "Engenheiros do Hawaii", "bpm": 140, "dificuldade": "★★★★☆", "duracao": 240, "inicio": 345, "link": "musicas/faixa_050.ogg"},
            {"nome": "L'Amour Toujours", "artista": "Gigi D'Agostino", "bpm": 139, "dificuldade": "★★★★☆", "duracao": 240, "inicio": 185, "link": "musicas/faixa_038.ogg"},
            {"nome": "Mulher de Fases", "artista": "Raimundos", "bpm": 132, "dificuldade": "★★★★☆", "duracao": 213.5, "inicio": 454, "link": "musicas/faixa_083.ogg"},
            {"nome": "Não Quero Dinheiro", "artista": "Tim Maia", "bpm": 138, "dificuldade": "★★★★☆", "duracao": 153.9, "inicio": 22, "link": "musicas/faixa_071.ogg"},
            {"nome": "Radio", "artista": "Bershy", "bpm": 132, "dificuldade": "★★★★☆", "duracao": 197.2, "inicio": 78, "link": "musicas/faixa_082.ogg"},
            {"nome": "Thunderstruck", "artista": "AC/DC", "bpm": 133, "dificuldade": "★★★★☆", "duracao": 240, "inicio": 340, "link": "musicas/faixa_011.ogg"},
            {"nome": "Vou Deixar", "artista": "Skank", "bpm": 136, "dificuldade": "★★★★☆", "duracao": 230.5, "inicio": 17, "link": "musicas/faixa_092.ogg"},
            {"nome": "You're Gonna Go Far, Kid", "artista": "The Offspring", "bpm": 131, "dificuldade": "★★★★☆", "duracao": 172.2, "inicio": 159, "link": "musicas/faixa_100.ogg"},
            {"nome": "The Unforgiven (Diego)", "artista": "Metalica", "bpm": 139, "dificuldade": "★★★★☆", "duracao": 240, "inicio": 250, "link": "musicas/faixa_064.ogg"},
            {"nome": "Hot N Cold", "artista": "Katy Perry", "bpm": 131.991, "dificuldade": "★★★★☆", "duracao": 221.3, "inicio": 67, "link": "musicas/faixa_055.ogg"},
            {"nome": "Whisky a Go-Go", "artista": "Roupa Nova", "bpm": 134.888, "dificuldade": "★★★★☆", "duracao": 240, "inicio": 92, "link": "musicas/faixa_106.ogg"},

            # ★★★★★
            {"nome": "A Melhor Banda de Todos os Tempos", "artista": "Titãs", "bpm": 166, "dificuldade": "★★★★★", "duracao": 185.7, "inicio": 52, "link": "musicas/faixa_103.ogg"},
            {"nome": "Aggressive Girl (Bárbara)", "artista": "OTMGirls", "bpm": 196, "dificuldade": "★★★★★", "duracao": 187.5, "inicio": 178, "link": "musicas/faixa_074.ogg"},
            {"nome": "American Idiot", "artista": "Green Day", "bpm": 186, "dificuldade": "★★★★★", "duracao": 174.8, "inicio": 9, "link": "musicas/faixa_041.ogg"},
            {"nome": "Anna Júlia", "artista": "Los Hermanos", "bpm": 148, "dificuldade": "★★★★★", "duracao": 211.4, "inicio": 278, "link": "musicas/faixa_015.ogg"},
            {"nome": "As It Was (Eliza)", "artista": "Harry Styles", "bpm": 174, "dificuldade": "★★★★★", "duracao": 163.5, "inicio": 131, "link": "musicas/faixa_046.ogg"},
            {"nome": "Basket Case", "artista": "Green Day", "bpm": 169, "dificuldade": "★★★★★", "duracao": 194.4, "inicio": 77, "link": "musicas/faixa_042.ogg"},
            {"nome": "Blinding Lights", "artista": "The Weeknd", "bpm": 171, "dificuldade": "★★★★★", "duracao": 203.2, "inicio": 28, "link": "musicas/faixa_102.ogg"},
            {"nome": "Girlfriend", "artista": "Avril Lavigne", "bpm": 164, "dificuldade": "★★★★★", "duracao": 227.4, "inicio": 355, "link": "musicas/faixa_016.ogg"},
            {"nome": "Human Nature", "artista": "Madonna", "bpm": 185, "dificuldade": "★★★★★", "duracao": 240, "inicio": 68, "link": "musicas/faixa_060.ogg"},
            {"nome": "Irreplaceable", "artista": "Beyoncé", "bpm": 176, "dificuldade": "★★★★★", "duracao": 240, "inicio": 152, "link": "musicas/faixa_020.ogg"},
            {"nome": "Kitty Kat", "artista": "Beyoncé", "bpm": 158, "dificuldade": "★★★★★", "duracao": 57.7, "inicio": 163, "link": "musicas/faixa_021.ogg"},
            {"nome": "Natasha", "artista": "Capital Inicial", "bpm": 150, "dificuldade": "★★★★★", "duracao": 195.2, "inicio": 188, "link": "musicas/faixa_029.ogg"},
            {"nome": "Ok, But This Is the Last Time", "artista": "The Offspring", "bpm": 148, "dificuldade": "★★★★★", "duracao": 206.6, "inicio": 70, "link": "musicas/faixa_097.ogg"},
            {"nome": "P do Pecado", "artista": "Menos É Mais", "bpm": 167, "dificuldade": "★★★★★", "duracao": 191.7, "inicio": 287, "link": "musicas/faixa_043.ogg"},
            {"nome": "Passa Mal", "artista": "Marília Mendonça", "bpm": 148, "dificuldade": "★★★★★", "duracao": 155.0, "inicio": 215, "link": "musicas/faixa_063.ogg"},
            {"nome": "Proibida Pra Mim (Grazon)", "artista": "Charlie Brown Jr.", "bpm": 164, "dificuldade": "★★★★★", "duracao": 167.9, "inicio": 160, "link": "musicas/faixa_078.ogg"},
            {"nome": "Quarta Cadeira", "artista": "Matheus e Kauan", "bpm": 158, "dificuldade": "★★★★★", "duracao": 210.7, "inicio": 149, "link": "musicas/faixa_079.ogg"},
            {"nome": "Ring the Alarm", "artista": "Beyoncé", "bpm": 171, "dificuldade": "★★★★★", "duracao": 207.4, "inicio": 96, "link": "musicas/faixa_022.ogg"},
            {"nome": "Sonífera Ilha", "artista": "Titãs", "bpm": 159, "dificuldade": "★★★★★", "duracao": 170.8, "inicio": 20, "link": "musicas/faixa_104.ogg"},
            {"nome": "Tá Vendo Aquela Lua", "artista": "Exaltasamba", "bpm": 164, "dificuldade": "★★★★★", "duracao": 205.7, "inicio": 43, "link": "musicas/faixa_036.ogg"},
            {"nome": "Te Amar Demais", "artista": "Sodré", "bpm": 152, "dificuldade": "★★★★★", "duracao": 132.0, "inicio": 178, "link": "musicas/faixa_094.ogg"},
            {"nome": "Truth in Fiction", "artista": "The Offspring", "bpm": 160, "dificuldade": "★★★★★", "duracao": 120.4, "inicio": 324, "link": "musicas/faixa_099.ogg"},
            {"nome": "Umbrella", "artista": "Rihanna", "bpm": 174, "dificuldade": "★★★★★", "duracao": 240, "inicio": 251, "link": "musicas/faixa_088.ogg"},
            {"nome": "Vem Ser Minha", "artista": "Charlie Brown Jr.", "bpm": 149, "dificuldade": "★★★★★", "duracao": 240, "inicio": 373, "link": "musicas/faixa_105.ogg"},
            {"nome": "Coffee (Gabriel)", "artista": "Good Kid", "bpm": 180, "dificuldade": "★★★★★", "duracao": 132.5, "inicio": 65, "link": "musicas/faixa_040.ogg"},
            {"nome": "Helter Skelter (Miranda)", "artista": "The Beatles", "bpm": 168, "dificuldade": "★★★★★", "duracao": 240, "inicio": 130, "link": "musicas/faixa_095.ogg"},
            {"nome": "Bye Bye Bye", "artista": "*NSYNC", "bpm": 172.552, "dificuldade": "★★★★★", "duracao": 202.8, "inicio": 165, "link": "musicas/faixa_112.ogg"},
            {"nome": "Can't Stop", "artista": "Red Hot Chili Peppers", "bpm": 182.698, "dificuldade": "★★★★★", "duracao": 240, "inicio": 64, "link": "musicas/faixa_085.ogg"},
            {"nome": "Oops!... I Did It Again", "artista": "Britney Spears", "bpm": 190.099, "dificuldade": "★★★★★", "duracao": 210.6, "inicio": 173, "link": "musicas/faixa_027.ogg"},
            {"nome": "Que País É Este", "artista": "Legião Urbana", "bpm": 145.471, "dificuldade": "★★★★★", "duracao": 178.7, "inicio": 34, "link": "musicas/faixa_080.ogg"},
            
        ]

        self.retangulos = []
        self.separadores = []
        self.rolagem = 0
        self.rolagem_maxima = 0
        self.arraste_barra = None

        self.selecionada = None
        self.previa_atual = None
        self.prox_tela = False
        self.tela_personagens = None
        self.ordenar_musicas(self.ordenacao)

        self.fundo = pygame.image.load("sprites/fundo_musicas.png")

        self._iniciar_controle()

    # Reorganiza o catálogo pelo critério escolhido, preserva a música selecionada e refaz as posições.
    def ordenar_musicas(self, criterio):
        musica_selecionada = self.lista_musicas[self.selecionada] if self.selecionada is not None else None
        self.ordenacao = criterio

        if criterio == 'dificuldade':
            self.lista_musicas.sort(key=lambda musica: (self._grupo_musica(musica)[0], musica.get('bpm') is None, musica.get('bpm') or 0, self._texto_ordenacao(musica.get('nome'))))
        else:
            self.lista_musicas.sort(key=lambda musica: (self._grupo_musica(musica)[0], self._texto_ordenacao(musica.get(criterio)), self._texto_ordenacao(musica.get('nome'))))

        self.selecionada = next((i for i, musica in enumerate(self.lista_musicas) if musica is musica_selecionada), None)
        self._montar_lista()
        self.rolagem = 0
        self.arraste_barra = None

    # Remove acentos, espaços nas pontas e diferenças de maiúsculas para comparar os nomes.
    def _texto_ordenacao(self, texto):
        texto = unicodedata.normalize('NFD', texto or '')
        return ''.join(letra for letra in texto if not unicodedata.combining(letra)).strip().casefold()

    # Determina a ordem e o título do agrupamento por dificuldade ou faixa de letras.
    def _grupo_musica(self, musica):
        if self.ordenacao == 'dificuldade':
            nivel = (musica.get('dificuldade') or '').count('★')
            titulo = f'Dificuldade {nivel}' if nivel else 'Sem dificuldade'
            return nivel or 6, titulo

        texto = self._texto_ordenacao(musica.get(self.ordenacao))
        letra = texto[:1].upper()
        categoria = 'Artistas' if self.ordenacao == 'artista' else 'Músicas'

        if letra.isdigit():
            return 0, f'{categoria}: 0 - 9'

        for ordem, (inicio, fim) in enumerate([('A', 'G'), ('H', 'N'), ('O', 'T'), ('U', 'Z')], start=1):
            if inicio <= letra <= fim:
                return ordem, f'{categoria}: {inicio} - {fim}'

        return 5, f'{categoria}: outros'

    # Calcula os retângulos de músicas e separadores e a distância máxima de rolagem.
    def _montar_lista(self):
        self.retangulos = []
        self.separadores = []
        grupo_anterior = None
        y = 140

        for i, musica in enumerate(self.lista_musicas):
            grupo = self._grupo_musica(musica)

            if grupo != grupo_anterior:
                if i > 0:
                    y += 10

                self.separadores.append({'titulo': grupo[1], 'rect': pygame.Rect(100, y, 500, 32), 'quantidade': 0})
                grupo_anterior = grupo
                y += 42

            self.separadores[-1]['quantidade'] += 1
            self.retangulos.append(pygame.Rect(100, y, 500, 60))
            y += 70

        self.rolagem_maxima = max(0, self.retangulos[-1].bottom - c.ALTURA_TELA + 30) if self.retangulos else 0

    # Retorna o trilho e a alça proporcionais à quantidade de conteúdo e à posição atual.
    def _barra_rolagem(self):
        trilho = pygame.Rect(615, 140, 8, c.ALTURA_TELA - 170)
        altura_total = trilho.height + self.rolagem_maxima
        altura_barra = min(trilho.height, max(20, int(trilho.height ** 2 / altura_total)))
        proporcao = self.rolagem / self.rolagem_maxima if self.rolagem_maxima else 0
        y_barra = trilho.y + round(proporcao * (trilho.height - altura_barra))
        return trilho, pygame.Rect(trilho.x, y_barra, trilho.width, altura_barra)

    # Converte o movimento vertical do mouse sobre a alça em uma posição de rolagem válida.
    def _arrastar_barra(self, y_mouse):
        trilho, barra = self._barra_rolagem()
        percurso = trilho.height - barra.height
        if percurso > 0:
            proporcao = (y_mouse - self.arraste_barra - trilho.top) / percurso
            self.rolagem = round(max(0, min(1, proporcao)) * self.rolagem_maxima)

    # Desenha os títulos dos grupos e a quantidade de músicas, descontando a rolagem.
    def desenhar_separadores(self, window):
        for separador in self.separadores:
            rect = separador['rect'].move(0, -self.rolagem)

            pygame.draw.rect(window, c.COR_FUNDO_SELECIONADO, rect)
            pygame.draw.rect(window, c.COR_BORDA_ESCURA, rect, 1)

            titulo = self.fonte_ordenacao.render(separador['titulo'], True, c.COR_TEXTO)
            window.blit(titulo, titulo.get_rect(midleft=(rect.x + 12, rect.centery)))

            quantidade = separador['quantidade']
            mensagem = f'{quantidade} música' if quantidade == 1 else f'{quantidade} músicas'
            texto = self.artistas.render(mensagem, True, c.COR_TEXTO_SUAVE)
            window.blit(texto, texto.get_rect(midright=(rect.right - 12, rect.centery)))

    # Desenha o funil e, quando aberto, o menu com o critério ativo e a opção em foco.
    def desenhar_ordenacao(self, window):
        pos_mouse = pygame.mouse.get_pos()
        em_foco = self.menu_ordenacao_aberto or self.rect_ordenacao.collidepoint(pos_mouse)
        cor_funil = (169, 112, 205) if em_foco else (132, 81, 166)
        x, y = self.rect_ordenacao.topleft
        pontos = [(x + 7, y + 8), (x + 29, y + 8), (x + 21, y + 18), (x + 21, y + 27), (x + 15, y + 30), (x + 15, y + 18)]
        pygame.draw.lines(window, cor_funil, True, pontos, 3)

        if not self.menu_ordenacao_aberto:
            return

        pygame.draw.rect(window, c.COR_CAIXA, self.rect_menu_ordenacao, border_radius=8)
        pygame.draw.rect(window, c.COR_BORDA_ESCURA, self.rect_menu_ordenacao, 1, border_radius=8)
        titulo = self.fonte_ordenacao.render('Ordenar por', True, c.COR_TEXTO_SUAVE)
        window.blit(titulo, (self.rect_menu_ordenacao.x + 12, self.rect_menu_ordenacao.y + 8))

        for indice, ((criterio, rotulo), rect) in enumerate(zip(self.opcoes_ordenacao, self.rects_opcoes_ordenacao)):
            ativo = criterio == self.ordenacao
            foco_controle = bool(self._controles.dispositivos) and indice == self._foco_controle
            if ativo or foco_controle or rect.collidepoint(pos_mouse):
                cor = c.COR_FUNDO_SELECIONADO if ativo else c.COR_BOTAO_HOVER
                pygame.draw.rect(window, cor, rect, border_radius=5)
            if ativo:
                pygame.draw.circle(window, c.COR_FOCO, (rect.x + 11, rect.centery), 3)

            texto = self.fonte_ordenacao.render(rotulo, True, c.COR_TEXTO)
            window.blit(texto, texto.get_rect(midleft=(rect.x + 23, rect.centery)))

    # Exibe a lista recortada à área de rolagem, os dados da faixa e os botões de navegação.
    def desenha(self, window):
        window.fill(c.COR_FUNDO)
        window.blit(self.fundo, (0, 0))

        pygame.draw.rect(window, c.COR_CAIXA, self.rect_faixa_titulo)
        pygame.draw.rect(window, c.COR_BORDA_ESCURA, self.rect_faixa_titulo, 2)
        window.blit(self.imagem_titulo, self.rect_titulo)

        pygame.draw.rect(window, c.COR_CREME_CLARO, (0, 0, c.LARGURA_TELA, c.ALTURA_TELA), 5)

        window.blit(self.vinil, self.rect_vinil)

        cor_voltar = c.COR_BOTAO_HOVER if self.voltar.collidepoint(pygame.mouse.get_pos()) else c.COR_BOTAO
        pygame.draw.rect(window, cor_voltar, self.voltar)
        pygame.draw.rect(window, c.COR_BORDA_ESCURA, self.voltar, 2)
        texto_voltar = self.proximo.render('Voltar', True, c.COR_TEXTO)
        window.blit(texto_voltar, texto_voltar.get_rect(center=self.voltar.center))

        botao_habilitado = self.musica_pronta()
        mouse_no_proximo = botao_habilitado and self.rect_proximo.collidepoint(pygame.mouse.get_pos())

        if botao_habilitado:
            cor_botao = c.COR_BOTAO_HOVER if mouse_no_proximo else c.COR_BOTAO
            cor_borda = c.COR_BORDA_ESCURA
            cor_texto = c.COR_TEXTO
        else:
            cor_botao = c.COR_BOTAO_DESABILITADO
            cor_borda = c.COR_BORDA_DESABILITADA
            cor_texto = c.COR_TEXTO_DESABILITADO

        pygame.draw.rect(window, cor_botao, self.rect_proximo)
        pygame.draw.rect(window, cor_borda, self.rect_proximo, 2)

        proximo = self.proximo.render("Próximo", True, cor_texto)
        window.blit(proximo, proximo.get_rect(center=self.rect_proximo.center))

        area_lista = pygame.Rect(0, 140, c.LARGURA_TELA, c.ALTURA_TELA - 140)
        pos_mouse = pygame.mouse.get_pos()
        mouse_na_lista = not self.menu_ordenacao_aberto and area_lista.collidepoint(pos_mouse)
        cor_hover = tuple((base + destaque) // 2 for base, destaque in zip(c.COR_CAIXA, c.COR_FUNDO_SELECIONADO))
        window.set_clip(area_lista)
        self.desenhar_separadores(window)

        for i in range(len(self.retangulos)):
            retangulo = self.retangulos[i].move(0, -self.rolagem)
            musica = self.lista_musicas[i]
            selecionada = i == self.selecionada
            em_foco = mouse_na_lista and retangulo.collidepoint(pos_mouse)

            cor_fundo = c.COR_FUNDO_SELECIONADO if selecionada else cor_hover if em_foco else c.COR_CAIXA
            pygame.draw.rect(window, cor_fundo, retangulo)

            if selecionada:
                pygame.draw.rect(window, c.COR_FOCO, (retangulo.x + 4, retangulo.y + 4, 6, retangulo.height - 8))

                bpm = self.informacoes.render(f"BPM: {musica['bpm']}", True, c.COR_TEXTO)
                dificuldade = texto_com_icone(self.informacoes, self.fonte_simbolos, 'Dificuldade:', musica['dificuldade'], c.COR_TEXTO)

                centro_painel = self.rect_vinil.x + round(self.rect_vinil.width * 0.603)
                rect_bpm = bpm.get_rect(center=(centro_painel, self.rect_vinil.centery - 20))
                rect_dificuldade = dificuldade.get_rect(center=(centro_painel, self.rect_vinil.centery + 20))

                window.blit(bpm, rect_bpm)
                window.blit(dificuldade, rect_dificuldade)

            cor_borda = c.COR_FOCO if selecionada else c.COR_BORDA_CAIXAS if em_foco else c.COR_BORDA_ESCURA
            espessura = 4 if selecionada else 2
            pygame.draw.rect(window, cor_borda, retangulo, espessura)

            nome = self.musicas.render(musica["nome"], True, c.COR_TEXTO_SELECIONADO if selecionada else c.COR_TEXTO)
            artista = self.artistas.render(musica["artista"], True, c.COR_TEXTO_SUAVE)

            window.blit(nome, (retangulo.x + 20, retangulo.y + 10))
            window.blit(artista, (retangulo.x + 20, retangulo.y + 34))

        window.set_clip(None)

        if self.rolagem_maxima > 0:
            trilho, barra = self._barra_rolagem()
            pygame.draw.rect(window, c.COR_FUNDO_SELECIONADO, trilho)
            pygame.draw.rect(window, c.COR_BORDA_ESCURA, trilho, 1)
            pygame.draw.rect(window, c.COR_FOCO, barra)

        window.set_clip(None)
        self.desenhar_ordenacao(window)
        self._desenhar_controle(window)

    # Trata seleção, filtro e rolagem por mouse e teclado, encaminhando os eventos de controle.
    def tratar_eventos(self, event):
        if self._evento_controle(event):
            return

        if event.type == pygame.WINDOWFOCUSLOST or (event.type == pygame.MOUSEBUTTONUP and event.button == 1):
            self.arraste_barra = None

        if event.type == pygame.MOUSEMOTION and self.arraste_barra is not None:
            if event.buttons[0]:
                self._arrastar_barra(event.pos[1])
            else:
                self.arraste_barra = None
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_ordenacao.collidepoint(event.pos):
                self.menu_ordenacao_aberto = not self.menu_ordenacao_aberto
                self.click.play()
                return

            if self.menu_ordenacao_aberto:
                for (criterio, _), rect in zip(self.opcoes_ordenacao, self.rects_opcoes_ordenacao):
                    if rect.collidepoint(event.pos):
                        self.ordenar_musicas(criterio)
                        break

                self.menu_ordenacao_aberto = False
                self.click.play()
                return

        if self.menu_ordenacao_aberto:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.menu_ordenacao_aberto = False
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rolagem_maxima > 0:
            trilho, barra = self._barra_rolagem()
            if trilho.inflate(12, 0).collidepoint(event.pos):
                self.arraste_barra = event.pos[1] - barra.top if barra.inflate(12, 0).collidepoint(event.pos) else barra.height // 2
                self._arrastar_barra(event.pos[1])
                return

        if event.type == pygame.MOUSEWHEEL:
            self.rolagem -= event.y * 40
            self.rolagem = max(0, min(self.rolagem, self.rolagem_maxima))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.voltar.collidepoint(event.pos):
                self.click.play()
                self.voltar_tela = True
                return

            area_lista = pygame.Rect(0, 140, c.LARGURA_TELA, c.ALTURA_TELA - 140)

            if area_lista.collidepoint(event.pos):
                for i in range(len(self.retangulos)):
                    retangulo = self.retangulos[i].move(0, -self.rolagem)

                    if retangulo.collidepoint(event.pos):
                        self.selecionada = i
                        self.click.play()
                        break

            if self.rect_proximo.collidepoint(event.pos) and self.musica_pronta():
                self.click.play()
                self.prox_tela = True

        if event.type == pygame.KEYDOWN and self.lista_musicas:
            if event.key == pygame.K_DOWN or event.key == pygame.K_UP:
                self.passar.play()

                if self.selecionada is None:
                    self.selecionada = 0
                elif event.key == pygame.K_DOWN:
                    self.selecionada = min(self.selecionada + 1, len(self.lista_musicas) - 1)
                elif event.key == pygame.K_UP:
                    self.selecionada = max(0, self.selecionada - 1)

                retangulo = self.retangulos[self.selecionada]

                if retangulo.top - self.rolagem < 140:
                    self.rolagem = retangulo.top - 140
                elif retangulo.bottom - self.rolagem > c.ALTURA_TELA - 30:
                    self.rolagem = retangulo.bottom - (c.ALTURA_TELA - 30)

                self.rolagem = max(0, min(self.rolagem, self.rolagem_maxima))

    # Atualiza os controles, as transições e a prévia da faixa, evitando recarregar o mesmo áudio.
    def atualiza(self, jogo):
        self._atualizar_controle()

        if self.voltar_tela:
            self.voltar_tela = False
            self.prox_tela = False
            if self.previa_atual is not None:
                pygame.mixer.music.stop()
            self.previa_atual = None
            jogo.tela_atual = self.tela_anterior if self.tela_anterior is not None else Tela_Inicial()
            return

        pos_mouse = pygame.mouse.get_pos()
        pode_clicar = self.voltar.collidepoint(pos_mouse)
        if self.rolagem_maxima > 0:
            trilho, _ = self._barra_rolagem()
            pode_clicar = pode_clicar or self.arraste_barra is not None or trilho.inflate(12, 0).collidepoint(pos_mouse)
        area_lista = pygame.Rect(0, 140, c.LARGURA_TELA, c.ALTURA_TELA - 140)

        if area_lista.collidepoint(pos_mouse):
            for retangulo in self.retangulos:
                retangulo_tela = retangulo.move(0, -self.rolagem)

                if retangulo_tela.collidepoint(pos_mouse):
                    pode_clicar = True
                    break

        if self.rect_proximo.collidepoint(pos_mouse):
            pode_clicar = self.musica_pronta()

        if self.menu_ordenacao_aberto:
            pode_clicar = any(rect.collidepoint(pos_mouse) for rect in self.rects_opcoes_ordenacao)

        if self.rect_ordenacao.collidepoint(pos_mouse):
            pode_clicar = True

        if pode_clicar:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        if self.prox_tela and self.musica_pronta():
            pygame.mixer.music.stop()
            self.previa_atual = None
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            musica = self.lista_musicas[self.selecionada]

            if self.tela_personagens is None:
                self.tela_personagens = Tela_Personagens(musica, self.sessao, self)
            else:
                self.tela_personagens.musica = musica

            jogo.tela_atual = self.tela_personagens
            self.prox_tela = False
            return

        # Só carrega outra prévia quando a música selecionada muda.
        musica = self.lista_musicas[self.selecionada] if self.selecionada is not None else None
        link = musica.get('link') if musica is not None else None

        if link != self.previa_atual:
            pygame.mixer.music.stop()
            self.previa_atual = link

            if link:
                try:
                    carregar_musica(link)
                    inicio = 30 if (musica.get('duracao') or 0) > 30 else 0
                    pygame.mixer.music.play(start=inicio)
                except (pygame.error, OSError):
                    self._avisar_controle('Não foi possível tocar a prévia. Confira o arquivo da música.')
                    tocar_musica_menu()
            else:
                tocar_musica_menu()
        elif link and musica_terminou(link):
            # A prévia terminou: mantém o menu com música, sem reiniciá-la a cada frame.
            tocar_musica_menu()

    # Verifica se BPM, duração, início e caminho do áudio têm os dados mínimos para iniciar a partida.
    def musica_pronta(self):
        if self.selecionada is None:
            return False

        musica = self.lista_musicas[self.selecionada]

        for campo in ('bpm', 'duracao'):
            valor = musica.get(campo)
            if not isinstance(valor, (int, float)) or valor <= 0:
                return False

        inicio = musica.get('inicio')
        return isinstance(inicio, (int, float)) and inicio >= 0 and isinstance(musica.get('link'), str) and bool(musica['link'].strip())

    # Move a seleção sem sair da lista e ajusta a rolagem para manter a faixa visível.
    def _mover_musica_controle(self, passo):
        if not self.lista_musicas:
            return

        if self.selecionada is None:
            self.selecionada = 0
        else:
            self.selecionada = max(0, min(self.selecionada + passo, len(self.lista_musicas) - 1))

        retangulo = self.retangulos[self.selecionada]

        if retangulo.top - self.rolagem < 140:
            self.rolagem = retangulo.top - 140
        elif retangulo.bottom - self.rolagem > c.ALTURA_TELA - 30:
            self.rolagem = retangulo.bottom - (c.ALTURA_TELA - 30)

        self.rolagem = max(0, min(self.rolagem, self.rolagem_maxima))
        self.passar.play()
        self._aviso_ate = 0

    # Traduz as ações do controle em seleção, abertura do filtro, confirmação ou retorno.
    def _comando_controle(self, acao, jogador):
        if acao == 'x':
            self.menu_ordenacao_aberto = not self.menu_ordenacao_aberto
            self._foco_controle = next((i for i, (criterio, _) in enumerate(self.opcoes_ordenacao) if criterio == self.ordenacao), 0)
            self.click.play()
            return

        if self.menu_ordenacao_aberto:
            if acao in ('cima', 'baixo'):
                passo = 1 if acao == 'baixo' else -1
                self._foco_controle = (self._foco_controle + passo) % len(self.opcoes_ordenacao)
                self.passar.play()
            elif acao in ('a', 'start'):
                self.ordenar_musicas(self.opcoes_ordenacao[self._foco_controle][0])
                self.menu_ordenacao_aberto = False

                if self.selecionada is not None:
                    self._mover_musica_controle(0)
            elif acao in ('b', 'voltar'):
                self.menu_ordenacao_aberto = False
            return

        if acao in ('cima', 'baixo', 'esquerda', 'direita'):
            self._mover_musica_controle(1 if acao in ('baixo', 'direita') else -1)
        elif acao in ('a', 'start'):
            if self.selecionada is None:
                self._mover_musica_controle(0)
            elif self.musica_pronta():
                self.click.play()
                self.prox_tela = True
            else:
                self._avisar_controle('Complete BPM, duração, início e link do MP3 dessa música para jogar.')
        elif acao in ('b', 'voltar'):
            self.click.play()
            self.voltar_tela = True


# Gerencia os nomes, as skins e a confirmação dos dois jogadores antes de iniciar a partida.
class Tela_Personagens(TelaComControle):
    # Retoma a trilha do menu quando a seleção de personagens volta a ser a tela ativa.
    def ao_entrar(self):
        tocar_musica_menu()

    # Recupera a sessão e prepara nomes, skins, botões e estados de pronto dos dois jogadores.
    def __init__(self, musica, sessao=None, tela_anterior=None):
        self.click = pygame.mixer.Sound("efeitos/efeito_006.ogg")
        self.papel = pygame.mixer.Sound("efeitos/efeito_004.ogg")
        self.sessao = sessao
        self.tela_anterior = tela_anterior
        self.voltar_tela = False
        self.voltar = pygame.Rect(30, 25, 130, 40)
        self.fonte_botoes = pygame.font.Font(c.FONTE_PADRAO, 23)
        self.nomes_bloqueados = sessao is not None
        self.musica = musica

        self.fonte_musica = pygame.font.Font(c.FONTE_TITULOS, 35)
        self.fonte_artista = pygame.font.Font(c.FONTE_PADRAO, 22)
        self.nome = pygame.font.Font(c.FONTE_PADRAO, 30)
        self.status = pygame.font.Font(c.FONTE_PADRAO, 25)

        self.caixa_personagem_1 = pygame.Rect(200, 185, 350, 350)
        self.caixa_personagem_2 = pygame.Rect(730, 185, 350, 350)

        seta = pygame.image.load('sprites/seta_personagens.png')
        self.seta_dir = pygame.transform.scale(seta, (20, 20))
        self.seta_esq = pygame.transform.flip(self.seta_dir, True, False)

        self.status_1 = pygame.Rect(237.5, 590, 275, 50)
        self.status_2 = pygame.Rect(767.5, 590, 275, 50)

        self.n_1 = sessao['nomes'][0] if self.nomes_bloqueados else ''
        self.n_2 = sessao['nomes'][1] if self.nomes_bloqueados else ''
        self.editando_nome = None
        self.erro_nomes = False

        self.area_nome_1 = pygame.Rect(200, 140, 350, 45)
        self.area_nome_2 = pygame.Rect(730, 140, 350, 45)

        self.opcoes_status = [{'pronto': 'Pronto', 'cor': c.COR_PRONTO}, {'escolhendo': 'Escolhendo', 'cor': c.COR_ESCOLHENDO}]

        self.estado_1 = 1
        self.estado_2 = 1

        self.personagens = elementos.Personagem.personagens
        self.personagem_1 = sessao['personagens'][0] if self.nomes_bloqueados else 0
        self.personagem_2 = sessao['personagens'][1] if self.nomes_bloqueados else 0

        self.raposa_1 = elementos.Personagem(375, 360, True, self.personagem_1)
        self.raposa_2 = elementos.Personagem(905, 360, False, self.personagem_2)

        self.fundo = pygame.image.load("sprites/fundo_personagem.png")

        self.cores_personagens = [
            (255, 225, 193),
            (204, 234, 218),
            (224, 232, 190),
            (207, 234, 255),
            (247, 205, 190),
            (243, 209, 222),
            (224, 215, 250),
            (255, 241, 181),
            (230, 230, 245),
        ]

        self.rect_seta_esq_1 = self.seta_esq.get_rect(topleft=(210, 360))
        self.rect_seta_dir_1 = self.seta_dir.get_rect(topleft=(520, 360))
        self.rect_seta_esq_2 = self.seta_esq.get_rect(topleft=(740, 360))
        self.rect_seta_dir_2 = self.seta_dir.get_rect(topleft=(1050, 360))

        self._iniciar_controle()

    # Mostra as raposas, os campos de nome, as setas de escolha e a confirmação de cada jogador.
    def desenha(self, window):
        window.fill(c.COR_FUNDO)
        window.blit(self.fundo, (0, 0))

        cor_botao = c.COR_BOTAO_HOVER if self.voltar.collidepoint(pygame.mouse.get_pos()) else c.COR_BOTAO
        pygame.draw.rect(window, cor_botao, self.voltar)
        pygame.draw.rect(window, c.COR_BORDA_ESCURA, self.voltar, 2)
        texto_voltar = self.fonte_botoes.render('Voltar', True, c.COR_TEXTO)
        window.blit(texto_voltar, texto_voltar.get_rect(center=self.voltar.center))

        texto_musica = self.fonte_musica.render(self.musica['nome'], True, c.COR_CREME_CLARO)
        rect_musica = texto_musica.get_rect(center=(c.LARGURA_TELA // 2, 60))
        window.blit(texto_musica, rect_musica)

        texto_artista = self.fonte_artista.render(self.musica['artista'], True, c.COR_CREME_CLARO)
        rect_artista = texto_artista.get_rect(midtop=(rect_musica.centerx, rect_musica.bottom + 20))
        window.blit(texto_artista, rect_artista)

        pygame.draw.rect(window, c.COR_CREME_CLARO, (0, 0, c.LARGURA_TELA, c.ALTURA_TELA), 5)

        cor_1 = self.cores_personagens[self.personagem_1]
        cor_2 = self.cores_personagens[self.personagem_2]

        pygame.draw.rect(window, cor_1, self.caixa_personagem_1)
        pygame.draw.rect(window, c.COR_BORDA_CAIXAS, self.caixa_personagem_1, 4)
        pygame.draw.rect(window, cor_2, self.caixa_personagem_2)
        pygame.draw.rect(window, c.COR_BORDA_CAIXAS, self.caixa_personagem_2, 4)

        window.blit(self.raposa_1.image, self.raposa_1.rect)
        window.blit(self.raposa_2.image, self.raposa_2.rect)

        window.blit(self.seta_esq, self.rect_seta_esq_1)
        window.blit(self.seta_dir, self.rect_seta_dir_1)
        window.blit(self.seta_esq, self.rect_seta_esq_2)
        window.blit(self.seta_dir, self.rect_seta_dir_2)

        pos_mouse = pygame.mouse.get_pos()
        cor_hover = tuple((base + destaque) // 2 for base, destaque in zip(c.COR_CAIXA, c.COR_FUNDO_SELECIONADO))
        for retangulo, estado in [(self.status_1, self.estado_1), (self.status_2, self.estado_2)]:
            dados = self.opcoes_status[estado]

            if estado == 0:
                mensagem = dados['pronto']
            else:
                mensagem = dados['escolhendo']

            cor_fundo = cor_hover if retangulo.collidepoint(pos_mouse) else c.COR_CAIXA
            pygame.draw.rect(window, cor_fundo, retangulo)
            pygame.draw.rect(window, c.COR_BORDA_CAIXAS, retangulo, 3)

            texto = self.status.render(mensagem, True, dados['cor'])
            rect_texto = texto.get_rect(center=retangulo.center)
            window.blit(texto, rect_texto)

        for jogador, area in [(1, self.area_nome_1), (2, self.area_nome_2)]:
            editando = self.editando_nome == jogador
            estado = self.estado_1 if jogador == 1 else self.estado_2
            em_foco = not self.nomes_bloqueados and estado == 1 and area.collidepoint(pos_mouse)
            cor_fundo = c.COR_FUNDO_SELECIONADO if editando else cor_hover if em_foco else c.COR_CAIXA
            pygame.draw.rect(window, cor_fundo, area)
            pygame.draw.rect(window, c.COR_BORDA_CAIXAS, area, 3)

        texto_1 = self.n_1
        texto_2 = self.n_2

        if self.editando_nome == 1:
            texto_1 += '|'
        elif not texto_1:
            texto_1 = 'Jogador 1'

        if self.editando_nome == 2:
            texto_2 += '|'
        elif not texto_2:
            texto_2 = 'Jogador 2'

        nome_1 = self.nome.render(texto_1, True, c.COR_TEXTO)
        window.blit(nome_1, (self.caixa_personagem_1.centerx - nome_1.get_width() / 2, 155))

        nome_2 = self.nome.render(texto_2, True, c.COR_TEXTO)
        window.blit(nome_2, (self.caixa_personagem_2.centerx - nome_2.get_width() / 2, 155))

        if self.erro_nomes:
            aviso = self.status.render('Os jogadores precisam usar nomes diferentes!', True, c.COR_ERRO)
            window.blit(aviso, aviso.get_rect(center=(c.LARGURA_TELA // 2, 680)))

        self._desenhar_controle(window)


    # Trata cliques, edição de nomes e comandos de escolha, respeitando jogadores já prontos.
    def tratar_eventos(self, event):
        if self._evento_controle(event):
            return
        if self._teclado_personagens(event):
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.voltar.collidepoint(event.pos):
                self.click.play()
                self.voltar_tela = True
                return

            if not self.nomes_bloqueados and self.estado_1 == 1 and self.area_nome_1.collidepoint(event.pos):
                self.editando_nome = 1
            elif not self.nomes_bloqueados and self.estado_2 == 1 and self.area_nome_2.collidepoint(event.pos):
                self.editando_nome = 2
            else:
                self.editando_nome = None

            if self.status_1.collidepoint(event.pos):
                self._acao_personagem('a', 1)
            elif self.status_2.collidepoint(event.pos):
                self._acao_personagem('a', 2)

            if self.estado_1 == 1 and self.rect_seta_esq_1.collidepoint(event.pos):
                self.personagem_1 = (self.personagem_1 - 1) % len(self.personagens)
                self.raposa_1 = elementos.Personagem(375, 360, True, self.personagem_1)
                self.papel.play()

            elif self.estado_1 == 1 and self.rect_seta_dir_1.collidepoint(event.pos):
                self.personagem_1 = (self.personagem_1 + 1) % len(self.personagens)
                self.raposa_1 = elementos.Personagem(375, 360, True, self.personagem_1)
                self.papel.play()

            elif self.estado_2 == 1 and self.rect_seta_esq_2.collidepoint(event.pos):
                self.personagem_2 = (self.personagem_2 - 1) % len(self.personagens)
                self.raposa_2 = elementos.Personagem(905, 360, False, self.personagem_2)
                self.papel.play()

            elif self.estado_2 == 1 and self.rect_seta_dir_2.collidepoint(event.pos):
                self.personagem_2 = (self.personagem_2 + 1) % len(self.personagens)
                self.raposa_2 = elementos.Personagem(905, 360, False, self.personagem_2)
                self.papel.play()

        if event.type == pygame.KEYDOWN and not self.nomes_bloqueados and self.editando_nome is not None:
            estado = self.estado_1 if self.editando_nome == 1 else self.estado_2
            if estado == 0:
                self.editando_nome = None
                return
            if event.key == pygame.K_RETURN:
                self.editando_nome = None

            elif event.key == pygame.K_BACKSPACE:
                if self.editando_nome == 1:
                    self.n_1 = self.n_1[:-1]
                else:
                    self.n_2 = self.n_2[:-1]

            elif event.unicode.isprintable():
                if self.editando_nome == 1:
                    if len(self.n_1) < 12:
                        self.n_1 += event.unicode
                else:
                    if len(self.n_2) < 12:
                        self.n_2 += event.unicode

    # Anima as raposas, valida nomes diferentes e inicia a partida somente com os dois prontos.
    def atualiza(self, jogo):
        self._liberar_selecao_neutra()
        self._atualizar_controle()
        if self.voltar_tela:
            self.voltar_tela = False
            self.estado_1 = 1
            self.estado_2 = 1
            self.editando_nome = None
            if self.tela_anterior is not None:
                jogo.tela_atual = self.tela_anterior
            else:
                tela_musicas = Tela_Musicas(self.sessao)
                tela_musicas.tela_personagens = self
                self.tela_anterior = tela_musicas
                for i, musica in enumerate(tela_musicas.lista_musicas):
                    if musica == self.musica:
                        tela_musicas.selecionada = i
                        tela_musicas.rolagem = max(0, min(tela_musicas.retangulos[i].top - 140, tela_musicas.rolagem_maxima))
                        break
                jogo.tela_atual = tela_musicas
            return

        self.raposa_1.update()
        self.raposa_2.update()

        pos_mouse = pygame.mouse.get_pos()
        nome_1 = ' '.join(self.n_1.split()) or 'Jogador 1'
        nome_2 = ' '.join(self.n_2.split()) or 'Jogador 2'

        self.erro_nomes = normalizar_nome(nome_1) == normalizar_nome(nome_2)

        areas = [
            self.voltar,
            self.status_1, self.status_2,
        ]

        for estado, esquerda, direita, nome in [
            (self.estado_1, self.rect_seta_esq_1, self.rect_seta_dir_1, self.area_nome_1),
            (self.estado_2, self.rect_seta_esq_2, self.rect_seta_dir_2, self.area_nome_2),
        ]:
            if estado == 1:
                areas.extend([esquerda, direita])
                if not self.nomes_bloqueados:
                    areas.append(nome)

        if any(area.collidepoint(pos_mouse) for area in areas):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        if self.estado_1 == 0 and self.estado_2 == 0:
            if self.erro_nomes:
                self.estado_1 = self.estado_2 = 1
                return

            jogo.tela_atual = Tela_Jogo(nome_1, nome_2, self.personagem_1, self.personagem_2, self.musica, self.sessao)

    # Encaminha a escolha ao jogador correto e permite alternar entre os dois com LB/RB.
    # Após essa troca, espera soltar os comandos para evitar uma confirmação involuntária.
    def _comando_controle(self, acao, jogador):
        assinatura = tuple(sorted(((identificador, dados['jogador']) for identificador, dados in self._controles.dispositivos.items())))
        if assinatura != getattr(self, '_assinatura_selecao', None):
            self._assinatura_selecao = assinatura
            self._jogador_selecao = jogador
            self._aguardar_selecao_neutra = False
        if len(self._controles.dispositivos) == 1:
            dados = next(iter(self._controles.dispositivos.values()))
            if acao in ('lb', 'rb'):
                novo_jogador = 1 if acao == 'lb' else 2
                if novo_jogador != self._jogador_selecao:
                    self._jogador_selecao = novo_jogador
                    self.editando_nome = None
                    # espera soltar antes de escolher o outro personagem
                    self._aguardar_selecao_neutra = True
                    dados['aguardar_neutro'] = True
                    dados['navegacao'] = None
                    dados['proxima_repeticao'] = 0
                    self.click.play()
                return
            if getattr(self, '_aguardar_selecao_neutra', False):
                if not self._selecao_em_neutro(dados):
                    return
                self._aguardar_selecao_neutra = False
            jogador = self._jogador_selecao
        else:
            # cada controle escolhe apenas seu jogador
            if acao in ('lb', 'rb'):
                return
            self._jogador_selecao = jogador
        self._acao_personagem(acao, jogador)

    # Verifica se os botões de seleção estão soltos e o analógico voltou à zona neutra.
    def _selecao_em_neutro(self, dados):
        controle = dados['controle']
        botoes = (
            pygame.CONTROLLER_BUTTON_A, pygame.CONTROLLER_BUTTON_B,
            pygame.CONTROLLER_BUTTON_START,
            pygame.CONTROLLER_BUTTON_DPAD_UP, pygame.CONTROLLER_BUTTON_DPAD_DOWN,
            pygame.CONTROLLER_BUTTON_DPAD_LEFT, pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
        )
        analogico_neutro = max(abs(controle.get_axis(eixo)) for eixo in (
            pygame.CONTROLLER_AXIS_LEFTX, pygame.CONTROLLER_AXIS_LEFTY,
        )) <= self._controles.ZONA_SAIDA * 32767
        return analogico_neutro and not any(controle.get_button(b) for b in botoes)

    # Libera a seleção após a troca de jogador quando o único controle estiver em repouso.
    def _liberar_selecao_neutra(self):
        if len(self._controles.dispositivos) == 1 and getattr(self, '_aguardar_selecao_neutra', False):
            dados = next(iter(self._controles.dispositivos.values()))
            if self._selecao_em_neutro(dados):
                self._aguardar_selecao_neutra = False

    # Aplica a ação de trocar skin, confirmar pronto, cancelar ou voltar para o jogador indicado.
    def _acao_personagem(self, acao, jogador):
        estado = self.estado_1 if jogador == 1 else self.estado_2
        if acao in ('a', 'start'):
            self.editando_nome = None
            if jogador == 1:
                self.estado_1 = 1 - estado
            else:
                self.estado_2 = 1 - estado
            self.click.play()
        elif acao in ('b', 'voltar'):
            if self.editando_nome is not None:
                self.editando_nome = None
                return
            estado = self.estado_1 if jogador == 1 else self.estado_2
            if estado == 0:
                if jogador == 1:
                    self.estado_1 = 1
                else:
                    self.estado_2 = 1
            else:
                self.voltar_tela = True
            self.click.play()
        elif acao in ('cima', 'baixo', 'esquerda', 'direita') and self.personagens and estado == 1:
            passo = 1 if acao in ('baixo', 'direita') else -1
            if jogador == 1:
                self.personagem_1 = (self.personagem_1 + passo) % len(self.personagens)
                self.raposa_1 = elementos.Personagem(375, 360, True, self.personagem_1)
                self.estado_1 = 1
            else:
                self.personagem_2 = (self.personagem_2 + passo) % len(self.personagens)
                self.raposa_2 = elementos.Personagem(905, 360, False, self.personagem_2)
                self.estado_2 = 1
            self.papel.play()

    # Converte as teclas de seleção em ações e deixa a digitação livre enquanto um nome é editado.
    def _teclado_personagens(self, event):
        if event.type != pygame.KEYDOWN or self.editando_nome is not None:
            return False
        direcoes = {
            pygame.K_w: (1, 'cima'), pygame.K_s: (1, 'baixo'),
            pygame.K_a: (1, 'esquerda'), pygame.K_d: (1, 'direita'),
            pygame.K_UP: (2, 'cima'), pygame.K_DOWN: (2, 'baixo'),
            pygame.K_LEFT: (2, 'esquerda'), pygame.K_RIGHT: (2, 'direita'),
        }
        if event.key in direcoes:
            jogador, acao = direcoes[event.key]
            self._acao_personagem(acao, self._jogador_teclado(jogador))
            return True
        if event.key in (pygame.K_e, pygame.K_RETURN):
            jogador = 1 if event.key == pygame.K_e else 2
            self._acao_personagem('a', self._jogador_teclado(jogador))
            return True
        if event.key == pygame.K_ESCAPE:
            self.editando_nome = None
            self.voltar_tela = True
            return True
        return False


# Executa a disputa: sincroniza notas com a música, avalia acertos e administra pontos e poderes.
# Também controla a contagem inicial, a dificuldade adaptativa e a transição para o resultado.
class Tela_Jogo(TelaComControle):
    # Monta os tabuleiros, as raposas, os grupos de notas e efeitos e os estados de pontuação.
    # Prepara a sincronização pelo BPM e converte a duração da faixa para milissegundos.
    def __init__(self, nome_1, nome_2, personagem_1, personagem_2, musica, sessao=None):
        self.fundo = pygame.image.load('sprites/fundo_jogo.png').convert()
        self.fundo = pygame.transform.smoothscale(self.fundo, (c.LARGURA_TELA, c.ALTURA_TELA))
        self.pip = pygame.mixer.Sound("efeitos/efeito_005.ogg")
        self.apito = pygame.mixer.Sound("efeitos/efeito_001.ogg")
        self.powerup = pygame.mixer.Sound("efeitos/efeito_007.ogg")
        self.musica = musica

        if sessao is None:
            sessao = {'nomes': (nome_1.strip() or 'Jogador 1', nome_2.strip() or 'Jogador 2'), 'vencedores': set()}

        self.sessao = sessao
        self.sessao['personagens'] = (personagem_1, personagem_2)
        self.nome_1, self.nome_2 = self.sessao['nomes']

        if normalizar_nome(self.nome_1) == normalizar_nome(self.nome_2):
            raise ValueError('Os jogadores precisam usar nomes diferentes!')

        self.personagem_1 = personagem_1
        self.personagem_2 = personagem_2
        self.fim_jogo = False

        self.encerrando = False
        self.inicio_fim = 0
        self.tempo_fim = 2500
        self.inicio_musica = None
        self.inicio_notas = float(self.musica['inicio'])
        self.duracao = float(self.musica['duracao']) * 1000
        self.ultima_batida = -1

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        carregar_musica(self.musica['link'])

        self.fonte_nome = pygame.font.Font(c.FONTE_PADRAO, 25)
        self.fonte_pontos = pygame.font.Font(c.FONTE_PADRAO, 20)
        self.fonte_contagem = pygame.font.Font(c.FONTE_TITULOS, 60)

        self.contagem = ["Preparados?", "3", "2", "1", "Vai!"]
        self.etapa_contagem = 0
        self.contando = True

        self.pontos_j1 = elementos.Pontos(350, 130)
        self.pontos_j2 = elementos.Pontos(930, 130)

        self.caixas_nomes = []
        for nome, barra, direita in [(self.nome_1, self.pontos_j1, False), (self.nome_2, self.pontos_j2, True)]:
            texto = self.fonte_nome.render(nome, True, c.COR_TITULO)
            caixa = pygame.Rect(barra.rect.left, 82, max(140, texto.get_width() + 24), 30)

            if direita:
                caixa.right = barra.rect.right

            imagem = pygame.Surface(caixa.size)
            imagem.fill(c.COR_CAIXA)
            pygame.draw.rect(imagem, c.COR_MADEIRA, imagem.get_rect(), 4)
            pygame.draw.rect(imagem, c.COR_MADEIRA_ESCURA, imagem.get_rect(), 1)
            pygame.draw.line(imagem, c.COR_MADEIRA_CLARA, (1, 1), (caixa.width - 2, 1))
            imagem.blit(texto, texto.get_rect(center=imagem.get_rect().center))
            self.caixas_nomes.append((imagem, caixa))

        self.placar = pygame.image.load('sprites/placar.png').convert_alpha()
        self.placar = pygame.transform.scale(self.placar, (250, 65))

        self.todos = pygame.sprite.Group()
        self.setas_1 = pygame.sprite.Group()
        self.setas_2 = pygame.sprite.Group()
        self.notas_1 = pygame.sprite.Group()
        self.notas_2 = pygame.sprite.Group()
        self.tinta = pygame.sprite.Group()
        self.control = pygame.sprite.Group()
        self.mensagens = pygame.sprite.Group()
        self.aceleracao = pygame.sprite.Group()
        self.notas_pendentes = []

        self.raposa_1 = elementos.Personagem(270, 630, True, self.personagem_1)
        self.raposa_2 = elementos.Personagem(1010, 630, False, self.personagem_2)

        self.todos.add(self.raposa_1, self.raposa_2)
        self.todos.add(elementos.Tabuleiro(350, 360))
        self.todos.add(elementos.Tabuleiro(930, 360))
        self.todos.add(self.pontos_j1)
        self.todos.add(self.pontos_j2)
        self.todos.add(elementos.Musica())

        distancia = 700 / (self.musica['duracao'] * 60)
        self.todos.add(elementos.Notinha(290, 30, distancia))

        self.todos.add(elementos.Luz(350, 225, c.CORES_DIRECOES['cima'], 0))
        self.todos.add(elementos.Luz(350, 495, c.CORES_DIRECOES['baixo'], 0))
        self.todos.add(elementos.Luz(215, 360, c.CORES_DIRECOES['esquerda'], 90))
        self.todos.add(elementos.Luz(485, 360, c.CORES_DIRECOES['direita'], 90))
        self.todos.add(elementos.Luz(930, 225, c.CORES_DIRECOES['cima'], 0))
        self.todos.add(elementos.Luz(930, 495, c.CORES_DIRECOES['baixo'], 0))
        self.todos.add(elementos.Luz(796, 360, c.CORES_DIRECOES['esquerda'], 90))
        self.todos.add(elementos.Luz(1065, 360, c.CORES_DIRECOES['direita'], 90))

        self.setas_2.add(elementos.Setas(350, 298, 90))
        self.setas_2.add(elementos.Setas(350, 422, 270))
        self.setas_2.add(elementos.Setas(288, 360, 180))
        self.setas_2.add(elementos.Setas(412, 360, 0))

        self.setas_1.add(elementos.Setas(930, 298, 90))
        self.setas_1.add(elementos.Setas(930, 422, 270))
        self.setas_1.add(elementos.Setas(868, 360, 180))
        self.setas_1.add(elementos.Setas(992, 360, 0))

        self.lado = 0
        self.intervalo = 60 * 60 / float(self.musica['bpm'])
        self.contador = 0
        self.distancia = 148
        self.velocidade = c.VELOCIDADE_NOTA
        self.tempo_viagem = self.distancia / self.velocidade
        self.tempo = 0
        self.batida_alvo = self.intervalo

        while self.batida_alvo < self.tempo_viagem:
            self.batida_alvo += self.intervalo

        self.tem_poder_1 = None
        self.tem_poder_2 = None

        # Dificuldade adaptativa.
        self.chance_notas = 85
        self.acertos = 0
        self.erros = 0
        self.intervalo_dificuldade = 10000
        self.ultima_avaliacao = self.inicio_notas

        self._iniciar_controle()

    # Desenha a partida, incluindo notas, efeitos, pontuações, barras e contagem de preparação.
    def desenha(self, window):
        window.fill(c.COR_FUNDO)
        window.blit(self.fundo, (0, 0))
        pygame.draw.rect(window, c.COR_CREME_CLARO, (0, 0, c.LARGURA_TELA, c.ALTURA_TELA), 5)

        rect_placar = self.placar.get_rect(midtop=(window.get_width() // 2, 45))
        window.blit(self.placar, rect_placar)

        self.todos.draw(window)
        self.setas_1.draw(window)
        self.setas_2.draw(window)
        self.notas_1.draw(window)
        self.notas_2.draw(window)
        self.tinta.draw(window)
        self.mensagens.draw(window)

        for imagem, caixa in self.caixas_nomes:
            window.blit(imagem, caixa)

        p1 = self.fonte_pontos.render(f'{self.pontos_j1.pontos}', True, c.COR_TEXTO)
        rect_p1 = p1.get_rect(center=(rect_placar.left + rect_placar.width // 4 + 5, rect_placar.centery))
        window.blit(p1, rect_p1)

        p2 = self.fonte_pontos.render(f'{self.pontos_j2.pontos}', True, c.COR_TEXTO)
        rect_p2 = p2.get_rect(center=(rect_placar.left + 3 * rect_placar.width // 4 - 5, rect_placar.centery))
        window.blit(p2, rect_p2)

        if self.contando or self.encerrando:
            largura, altura = window.get_size()

            fundo = pygame.transform.smoothscale(window, (max(1, largura // 10), max(1, altura // 10)))
            fundo = pygame.transform.smoothscale(fundo, (largura, altura))
            window.blit(fundo, (0, 0))

            camada = pygame.Surface((largura, altura), pygame.SRCALPHA)
            camada.fill((*c.COR_FUNDO, 100))
            window.blit(camada, (0, 0))

            if self.contando:
                progresso = self.contador / self.intervalo
                mensagem = self.contagem[self.etapa_contagem]
                ultima_etapa = self.etapa_contagem == len(self.contagem) - 1

                intensidade = 0.45 if ultima_etapa else 0.30
                escala = 1 + intensidade * (1 - progresso) ** 3
                opacidade = int(255 * max(0, min(1, (0.9 - progresso) / 0.25)))
                cor = c.COR_CONTAGEM_VAI if ultima_etapa else c.COR_TITULO
            else:
                tempo_fim = pygame.time.get_ticks() - self.inicio_fim
                progresso = min(1, tempo_fim / 350)
                mensagem = "Fim da música!"

                escala = 1 + 0.25 * (1 - progresso) ** 3
                opacidade = int(255 * max(0, min(1, tempo_fim / 150, (self.tempo_fim - tempo_fim) / 350)))
                cor = c.COR_TITULO

            texto = self.fonte_contagem.render(mensagem, True, cor)
            sombra = self.fonte_contagem.render(mensagem, True, c.COR_SOMBRA_AVISO)

            tamanho = (max(1, int(texto.get_width() * escala)), max(1, int(texto.get_height() * escala)))
            texto = pygame.transform.smoothscale(texto, tamanho)
            sombra = pygame.transform.smoothscale(sombra, tamanho)

            texto.set_alpha(opacidade)
            sombra.set_alpha(int(opacidade * 0.18))

            rect_texto = texto.get_rect(center=(largura // 2, altura // 2))
            window.blit(sombra, rect_texto.move(3, 5))
            window.blit(texto, rect_texto)

        self._desenhar_controle(window)

    # Avança a contagem e, depois, usa a posição do áudio para agendar notas e marcar as batidas.
    # Atualiza efeitos, penaliza notas perdidas e encerra a partida ao atingir a duração configurada.
    def atualiza(self, jogo):
        self._atualizar_controle()
        self._preparar_poderes()

        if self.fim_jogo:
            pygame.mixer.music.stop()
            jogo.tela_atual = Tela_Podium(self.nome_1, self.nome_2, self.personagem_1, self.personagem_2, self.pontos_j1.pontos, self.pontos_j2.pontos, self.sessao)
            return

        if self.encerrando:
            if pygame.time.get_ticks() - self.inicio_fim >= self.tempo_fim:
                self.fim_jogo = True
            return

        self.setas_1.update()
        self.setas_2.update()
        self.tinta.update()
        self.control.update()
        self.aceleracao.update()
        self.mensagens.update()

        if self.contando:
            self.contador += 1

            if self.contador >= self.intervalo:
                self.contador -= self.intervalo

                for seta in self.setas_1:
                    seta.animar()
                for seta in self.setas_2:
                    seta.animar()

                self.etapa_contagem += 1

                if 0 < self.etapa_contagem < len(self.contagem):
                    self.pip.play()

                if self.etapa_contagem == len(self.contagem):
                    self.contando = False
                    self.contador = 0
                    pygame.mixer.music.play()
                    self.inicio_musica = pygame.time.get_ticks()
            return

        tempo_musica = pygame.mixer.music.get_pos()

        if tempo_musica < 0:
            tempo_musica = pygame.time.get_ticks() - self.inicio_musica

        if tempo_musica >= self.duracao:
            pygame.mixer.music.stop()
            self.apito.play()
            self.encerrando = True
            self.inicio_fim = pygame.time.get_ticks()
            return

        # Converte os milissegundos em frames a partir do início das notas.
        self.tempo = (tempo_musica - self.inicio_notas) * 60 / 1000

        if tempo_musica >= self.inicio_notas:
            self.contador = self.tempo % self.intervalo
            batida_atual = int(self.tempo // self.intervalo)

            if batida_atual > self.ultima_batida:
                self.ultima_batida = batida_atual
                self.todos.add(elementos.Margem(cor=c.COR_TITULO))
                self._pulsar_poderes()

                for seta in self.setas_1:
                    seta.animar()
                for seta in self.setas_2:
                    seta.animar()

        self.todos.update()

        if tempo_musica >= self.inicio_notas:
            while self.tempo >= self.batida_alvo - self.tempo_viagem:
                if random.randint(1, 100) <= self.chance_notas:
                    self._agendar_notas(random.choice([1, 2, 3, 4]), tempo_musica)

                self.batida_alvo += self.intervalo

            self._soltar_notas(tempo_musica)

        self.notas_1.update(tempo_musica)
        self.notas_2.update(tempo_musica)

        for notinha in self.notas_1:
            if notinha.distancia >= 168:
                notinha.kill()
                self.erros += 1

                if not self.pontos_j2.poder == 100:
                    self.pontos_j2.poder = max(0, self.pontos_j2.poder - 10)
                    self.todos.add(elementos.Mensagem("ERROU :[", 880, 630, c.COR_ERRO))

        for notinha in self.notas_2:
            if notinha.distancia >= 168:
                notinha.kill()
                self.erros += 1

                if not self.pontos_j1.poder == 100:
                    self.pontos_j1.poder = max(0, self.pontos_j1.poder - 10)
                    self.todos.add(elementos.Mensagem("ERROU :[", 400, 630, c.COR_ERRO))

        self._ajustar_dificuldade(tempo_musica)

    # Agenda a mesma direção para os dois jogadores com um horário comum de chegada.
    # Considera se a aceleração estará ativa no lançamento para definir a velocidade de cada nota.
    def _agendar_notas(self, lado, tempo_musica):
        chegada = self.inicio_notas + self.batida_alvo * 1000 / 60
        inicio_rapido = chegada - self.distancia / (self.velocidade * 3) * 1000 / 60
        atraso = max(0, inicio_rapido - tempo_musica)

        for jogador in (1, 2):
            acelerado = any(efeito.jogador_alvo == jogador and efeito.ativo(atraso) for efeito in self.aceleracao)
            velocidade = self.velocidade * (3 if acelerado else 1)
            self.notas_pendentes.append((jogador, lado, chegada, velocidade))

    # Cria as notas pendentes quando chega o instante de lançamento calculado pela velocidade.
    # O grupo notas_2 pertence ao jogador 1; notas_1 pertence ao jogador 2.
    def _soltar_notas(self, tempo_musica):
        for dados in self.notas_pendentes[:]:
            jogador, lado, chegada, velocidade = dados
            inicio = chegada - self.distancia / velocidade * 1000 / 60

            if tempo_musica < inicio:
                continue

            x = 350 if jogador == 1 else 930
            posicoes = {1: (x, 150, 90), 2: (x + 210, 360, 0), 3: (x, 570, 270), 4: (x - 210, 360, 180)}
            x, y, angulo = posicoes[lado]
            direcao = ('cima', 'direita', 'baixo', 'esquerda')[lado - 1]

            nota = elementos.Notas(x, y, angulo, c.CORES_DIRECOES[direcao], lado, velocidade, chegada)
            nota.update(tempo_musica)
            grupo = self.notas_2 if jogador == 1 else self.notas_1
            grupo.add(nota)
            self.notas_pendentes.remove(dados)

    # Reavalia periodicamente a proporção de acertos e ajusta a chance de novas notas dentro dos limites.
    def _ajustar_dificuldade(self, tempo_musica):
        if tempo_musica - self.ultima_avaliacao < self.intervalo_dificuldade:
            return

        total = self.acertos + self.erros

        if total > 0:
            media = self.acertos / total * 100

            if media >= 80:
                self.chance_notas = min(90, self.chance_notas + 5)
            elif media <= 50:
                self.chance_notas = max(75, self.chance_notas - 5)

        self.acertos = 0
        self.erros = 0
        self.ultima_avaliacao = tempo_musica

    # Compara a direção e a posição da nota para distinguir acertos bons e perfeitos.
    # Concede pontos e carga de poder, remove a nota acertada e cria o efeito visual correspondente.
    def verifica_direcao(self, jogador, colisoes, x_mensagem, direcao):
        for seta, nota in colisoes.items():
            for notinha in nota:
                if notinha.lado == direcao:
                    if 143 < notinha.distancia < 153:
                        jogador.pontos += 5
                        self.acertos += 1
                        jogador.poder = min(100, jogador.poder + 5)
                        self.todos.add(elementos.Mensagem("PERFEITO!", x_mensagem, 630, c.COR_ACERTO_PERFEITO))
                        notinha.kill()
                        self.todos.add(elementos.Splash(notinha.x, notinha.y, notinha.cor))

                    elif 128 < notinha.distancia < 168:
                        jogador.pontos += 3
                        self.acertos += 1
                        jogador.poder = min(100, jogador.poder + 3)
                        self.todos.add(elementos.Mensagem("BOM :]", x_mensagem, 630, c.COR_ACERTO_BOM))
                        notinha.kill()
                        self.todos.add(elementos.Splash(notinha.x, notinha.y, notinha.cor))

            seta.escala = 0.8

    # Recebe direções, ativação de poder e encerramento, usando a mesma lógica para teclado e controle.
    def tratar_eventos(self, event):
        if self._evento_controle(event):
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._encerrar_partida()
            return

        direcoes = {
            pygame.K_w: (1, 1), pygame.K_d: (1, 2), pygame.K_s: (1, 3), pygame.K_a: (1, 4),
            pygame.K_UP: (2, 1), pygame.K_RIGHT: (2, 2),
            pygame.K_DOWN: (2, 3), pygame.K_LEFT: (2, 4),
        }

        if event.key in direcoes:
            jogador_padrao, direcao = direcoes[event.key]
            self._apertar_direcao(self._jogador_teclado(jogador_padrao), direcao)
        elif event.key in (pygame.K_e, pygame.K_RETURN):
            jogador_padrao = 1 if event.key == pygame.K_e else 2
            self._ativar_poder(self._jogador_teclado(jogador_padrao))

    # Interrompe a música e sinaliza que a partida deve seguir para o pódio.
    def _encerrar_partida(self):
        pygame.mixer.music.stop()
        self.fim_jogo = True

    # Aplica a inversão de controles, identifica o tabuleiro do jogador e verifica os acertos.
    # Depois de pontuar, confere se a barra liberou um novo poder.
    def _apertar_direcao(self, jogador, direcao):
        if self.contando or self.encerrando or self.fim_jogo:
            return

        # Inverte a direção do jogador no teclado e no controle.
        if any(getattr(efeito, 'jogador_alvo', None) == jogador for efeito in self.control):
            direcao = {1: 3, 2: 4, 3: 1, 4: 2}[direcao]

        # O grupo _2 fica à esquerda e pertence ao jogador 1.
        if jogador == 1:
            pontos, setas, notas, x = self.pontos_j1, self.setas_2, self.notas_2, 400
        else:
            pontos, setas, notas, x = self.pontos_j2, self.setas_1, self.notas_1, 880

        colisoes = pygame.sprite.groupcollide(setas, notas, False, False)
        self.verifica_direcao(pontos, colisoes, x, direcao)
        self._preparar_poderes()

    # Ao atingir 100 de carga, sorteia um dos quatro poderes para cada jogador e cria seu ícone.
    # Não troca o poder enquanto ele já estiver guardado.
    def _preparar_poderes(self):
        if self.contando or self.encerrando or self.fim_jogo:
            return

        for jogador, x in ((1, 350), (2, 930)):
            pontos = getattr(self, f'pontos_j{jogador}')

            if pontos.poder == 100 and getattr(self, f'tem_poder_{jogador}') is None:
                poder = random.randint(1, 4)
                setattr(self, f'tem_poder_{jogador}', poder)
                imagem = elementos.Icone(x, 100, poder)
                setattr(self, f'imagem_poder{jogador}', imagem)
                self.todos.add(imagem)
                self.powerup.play()

    # Lança o poder guardado pelo jogador, esvazia sua barra e remove o ícone de disponibilidade.
    def _ativar_poder(self, jogador):
        if self.contando or self.encerrando or self.fim_jogo:
            return

        self._preparar_poderes()
        poder = getattr(self, f'tem_poder_{jogador}')

        if poder is None:
            return

        x = 270 if jogador == 1 else 1010
        self.todos.add(elementos.Bola_de_poder(x, 630, self, jogador, poder))
        setattr(self, f'tem_poder_{jogador}', None)
        getattr(self, f'pontos_j{jogador}').poder = 0
        imagem = getattr(self, f'imagem_poder{jogador}', None)

        if imagem is not None:
            imagem.kill()

    # Relaciona os botões do controle às direções, ao uso do poder e ao encerramento da partida.
    def _comando_controle(self, acao, jogador):
        direcoes = {'y': 1, 'cima': 1, 'b': 2, 'direita': 2, 'a': 3, 'baixo': 3, 'x': 4, 'esquerda': 4}

        if acao in direcoes:
            self._apertar_direcao(jogador, direcoes[acao])
        elif acao == 'poder':
            self._ativar_poder(jogador)
        elif acao in ('start', 'voltar'):
            self._encerrar_partida()

    # Cria o pulso visual na batida para os jogadores que têm um poder disponível.
    def _pulsar_poderes(self):
        if self.tem_poder_1 is not None:
            self.todos.add(elementos.Pulso(350, 360, cor=c.PISCA_PODER, duracao=400))

        if self.tem_poder_2 is not None:
            self.todos.add(elementos.Pulso(930, 360, cor=c.PISCA_PODER, duracao=400))


# Apresenta o resultado da partida, anima vencedor e perdedor e registra a rodada na sessão.
class Tela_Podium(TelaComControle):
    # Define o resultado e as animações e atualiza vitórias, rodada e elegibilidade ao ranking dos perdedores.
    # Ao completar três rodadas, prepara um novo combate para as próximas partidas.
    def __init__(self, nome_1, nome_2, personagem_1, personagem_2, pontos_1, pontos_2, sessao=None):
        carregar_musica("musicas/faixa_111.ogg")
        self.click = pygame.mixer.Sound("efeitos/efeito_006.ogg")
        self.tantantan = pygame.mixer.Sound("efeitos/efeito_009.ogg")
        self.tambor = pygame.mixer.Sound("efeitos/efeito_008.ogg")
        self.voltar_menu = False
        self.empate = pontos_1 == pontos_2
        self.tambor.play()

        if sessao is None:
            sessao = {'nomes': (nome_1.strip() or 'Jogador 1', nome_2.strip() or 'Jogador 2'), 'vencedores': set()}

        self.sessao = sessao
        self.sessao['personagens'] = (personagem_1, personagem_2)
        nome_1, nome_2 = self.sessao['nomes']
        self.pode_entrar_piores = True

        combate = self.sessao.setdefault('combate', {'rodada': 0, 'vitorias': [0, 0], 'ultimo_vencedor': None})

        self.fundo = pygame.image.load("sprites/fundo_podio.png")

        if combate['rodada'] == 3:
            combate = {'rodada': 0, 'vitorias': [0, 0], 'ultimo_vencedor': None}
            self.sessao['combate'] = combate

        vencedor_anterior = combate['ultimo_vencedor']
        vencedor = None

        if not self.empate:
            vencedor = 0 if pontos_1 > pontos_2 else 1
            perdedor = 1 - vencedor

            self.sessao['vencedores'].add(vencedor)
            self.pode_entrar_piores = perdedor not in self.sessao['vencedores']
            combate['vitorias'][vencedor] += 1

        combate['rodada'] += 1
        combate['ultimo_vencedor'] = vencedor

        self.sessao['resultado_partida'] = {
            'rodada': combate['rodada'],
            'vencedor': vencedor,
            'vencedor_anterior': vencedor_anterior,
            'vitorias': tuple(combate['vitorias']),
        }

        self.anunciando = True
        self.duracao_anuncio = 2500

        self.titulo = pygame.font.Font(c.FONTE_TITULOS, 40)
        self.fonte_anuncio = pygame.font.Font(c.FONTE_TITULOS, 60)
        self.proximo = pygame.font.Font(c.FONTE_PADRAO, 23)
        self.fonte_nome = pygame.font.Font(c.FONTE_PADRAO, 28)
        self.fonte_pontos = pygame.font.Font(c.FONTE_PADRAO, 26)

        self.menu = pygame.Rect(1100, 630, 130, 40)

        raposa_1 = elementos.Personagem(0, 0, True, personagem_1)
        raposa_2 = elementos.Personagem(0, 0, False, personagem_2)

        cor_nome_jogador_1 = (205, 110, 120)  # Rosa mais escuro no pódio.
        jogador_1 = (nome_1 or "Jogador 1", pontos_1, raposa_1, cor_nome_jogador_1)
        jogador_2 = (nome_2 or "Jogador 2", pontos_2, raposa_2, c.COR_NOME_JOGADOR_2_PODIO)

        if pontos_1 <= pontos_2:
            self.jogadores = [jogador_1, jogador_2]
        else:
            self.jogadores = [jogador_2, jogador_1]

        for posicao, jogador in enumerate(self.jogadores):
            nome, pontos, raposa, cor = jogador

            # A raposa da esquerda olha para a direita e vice-versa.
            raposa.flip = posicao == 0

            if not self.empate:
                pasta = raposa.dados_personagem["pasta_comemoracao"] if posicao == 1 else raposa.dados_personagem["pasta_chorando"]
                raposa.frames = [pygame.image.load(f"sprites/{pasta}/{pasta}_{i}.png").convert_alpha() for i in range(1, 7)]

            # Aplica o primeiro frame imediatamente, já na orientação correta.
            raposa.indice = 0
            raposa.contador = 0
            centro = raposa.rect.center
            image = pygame.transform.scale_by(raposa.frames[0], 2.8)
            raposa.image = pygame.transform.flip(image, raposa.flip, False)
            raposa.rect = raposa.image.get_rect(center=centro)
            raposa.area_podio = raposa.image.get_bounding_rect()

        self.inicio_anuncio = pygame.time.get_ticks()


        self.todos = pygame.sprite.Group()
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))
        self.todos.add(elementos.Folha(self))

        self._iniciar_controle()

    # Exibe o anúncio e, depois, o pódio com nomes, pontuações e raposas de vitória ou derrota.
    def desenha(self, window):
        window.fill(c.COR_FUNDO)
        window.blit(self.fundo, (0, 0))
        self.todos.draw(window)

        if not self.anunciando:
            titulo = self.titulo.render("Empate!" if self.empate else "E o vencedor é...", True, c.COR_TITULO)
            window.blit(titulo, (640 - titulo.get_width() // 2, 60))

        altura_esquerda = 360 if self.empate else 240

        for x, altura, jogador in [(300, altura_esquerda, self.jogadores[0]), (730, 360, self.jogadores[1])]:
            nome, pontos, raposa, cor = jogador
            y = 720 - altura

            pygame.draw.rect(window, c.COR_MADEIRA, (x + 15, y + 20, 220, altura - 20))
            pygame.draw.rect(window, c.COR_MADEIRA_ESCURA, (x + 227, y + 20, 8, altura - 20))
            pygame.draw.rect(window, c.COR_MADEIRA_CLARA, (x, y, 250, 20))
            pygame.draw.rect(window, c.COR_MADEIRA_ESCURA, (x, y, 250, 20), 2)

            area = raposa.area_podio
            x_raposa = x + 125 - area.x - area.width // 2
            y_raposa = y - area.y - area.height
            window.blit(raposa.image, (x_raposa, y_raposa))

            texto_nome = texto_com_contorno(self.fonte_nome, nome, cor)
            window.blit(texto_nome, (x + 125 - texto_nome.get_width() // 2, y_raposa + area.y - texto_nome.get_height() - 10))

            resultado = "Empate" if self.empate else ("Vencedor" if x == 730 else "Perdedor")
            texto_resultado = self.proximo.render(resultado, True, c.COR_TEXTO_PODIO)
            window.blit(texto_resultado, (x + 125 - texto_resultado.get_width() // 2, y + 40))

            texto_pontos = self.fonte_pontos.render(str(pontos), True, c.COR_TEXTO_PODIO)
            window.blit(texto_pontos, (x + 125 - texto_pontos.get_width() // 2, y + 80))

        pygame.draw.rect(window, c.COR_CREME_CLARO, (0, 0, c.LARGURA_TELA, c.ALTURA_TELA), 5)

        mouse_no_menu = not self.anunciando and self.menu.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(window, c.COR_BOTAO_HOVER if mouse_no_menu else c.COR_BOTAO, self.menu)
        pygame.draw.rect(window, c.COR_BORDA_ESCURA, self.menu, 2)

        menu = self.proximo.render("Próximo", True, c.COR_TEXTO)
        window.blit(menu, (1165 - menu.get_width() // 2, 650 - menu.get_height() // 2))

        if self.anunciando:
            largura, altura = window.get_size()
            tempo = pygame.time.get_ticks() - self.inicio_anuncio

            fundo = pygame.transform.smoothscale(window, (max(1, largura // 10), max(1, altura // 10)))
            fundo = pygame.transform.smoothscale(fundo, (largura, altura))
            window.blit(fundo, (0, 0))

            camada = pygame.Surface((largura, altura), pygame.SRCALPHA)
            camada.fill((*c.COR_FUNDO, 100))
            window.blit(camada, (0, 0))

            mensagem = "Empate!" if self.empate else "E o vencedor é..."
            texto = self.fonte_anuncio.render(mensagem, True, c.COR_TITULO)
            sombra = self.fonte_anuncio.render(mensagem, True, c.COR_SOMBRA_AVISO)

            progresso = min(1, tempo / 350)
            escala = 1 + 0.30 * (1 - progresso) ** 3

            tamanho = (max(1, int(texto.get_width() * escala)), max(1, int(texto.get_height() * escala)))
            texto = pygame.transform.smoothscale(texto, tamanho)
            sombra = pygame.transform.smoothscale(sombra, tamanho)

            opacidade = int(255 * max(0, min(1, (self.duracao_anuncio - tempo) / 400)))
            texto.set_alpha(opacidade)
            sombra.set_alpha(int(opacidade * 0.18))

            rect_texto = texto.get_rect(center=(largura // 2, altura // 2))
            window.blit(sombra, rect_texto.move(3, 5))
            window.blit(texto, rect_texto)

        self._desenhar_controle(window)


    # Recebe o controle e o clique para avançar após a apresentação do resultado.
    def tratar_eventos(self, event):
        if self._evento_controle(event):
            return

        if self.anunciando:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu.collidepoint(event.pos):
                self.click.play()
                self.voltar_menu = True

    # Atualiza a espera do anúncio e as animações e abre o ranking quando o avanço é confirmado.
    def atualiza(self, jogo):
        self._atualizar_controle()
        self.todos.update()
        if self.anunciando:
            self.anunciando = pygame.time.get_ticks() - self.inicio_anuncio < self.duracao_anuncio

            if self.anunciando:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return

            self.tantantan.play()
            pygame.mixer.music.play()

        if self.voltar_menu:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            jogo.tela_atual = Tela_Ranking(self.jogadores, self.sessao, self.pode_entrar_piores)
            return

        for nome, pontos, raposa, cor in self.jogadores:
            raposa.update()

        if self.menu.collidepoint(pygame.mouse.get_pos()):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    # Permite avançar com A ou Start quando o anúncio do resultado já terminou.
    def _comando_controle(self, acao, jogador):
        if not self.anunciando and acao in ('a', 'start'):
            self.click.play()
            self.voltar_menu = True


# Atualiza e exibe os rankings persistidos em arquivos, respeitando empates e resultados por nome.
# Mostra o balanço das rodadas e oferece revanche ou retorno ao menu.
class Tela_Ranking(TelaComControle):
    # Lê os arquivos de ranking, incorpora o resultado quando fornecido e salva as listas atualizadas.
    # Prepara as mensagens de desempenho, revanche e melhor de três com base na sessão.
    def __init__(self, jogadores=None, sessao=None, pode_entrar_piores=True):
        carregar_musica("musicas/faixa_110.ogg")
        pygame.mixer.music.play(-1)
        
        self.click = pygame.mixer.Sound("efeitos/efeito_006.ogg")
        self.sessao = sessao
        self.nome_vencedor = jogadores[1][0] if jogadores is not None else ''
        self.nome_perdedor = jogadores[0][0] if jogadores is not None else ''

        self.voltar_menu = False
        self.voltar_selecao = False
        self.mensagem_melhores = []
        self.mensagem_piores = []
        self.mensagem_empate = []
        self.mensagens_combate = []
        self.sugestao_melhor_tres = []
        self.placar_combate = ''

        self.fonte_titulo_ranking = pygame.font.Font(c.FONTE_TITULOS, 35)
        self.fonte_emojis = pygame.font.Font(c.FONTE_SIMBOLOS, 25)
        self.placares = pygame.font.Font(c.FONTE_PADRAO, 27)
        self.fonte_feedback = pygame.font.Font(c.FONTE_PADRAO, 26)
        self.proximo = pygame.font.Font(c.FONTE_PADRAO, 23)

        self.melhores = pygame.Rect(200, 160, 400, 400)
        self.piores = pygame.Rect(680, 160, 400, 400)
        self.area_melhores = pygame.Rect(210, 200, 380, 340)
        self.area_piores = pygame.Rect(690, 200, 380, 340)

        self.altura_linha = max(32, self.placares.get_linesize())
        self.rolagem_melhores = 0
        self.rolagem_piores = 0

        x_botoes = (c.LARGURA_TELA - 340) // 2
        self.revanche = pygame.Rect(x_botoes, 630, 160, 40)
        self.menu = pygame.Rect(x_botoes + 180, 630, 160, 40)

        self.fundo = pygame.image.load("sprites/fundo_ranking.png")

        try:
            with open('ranking/melhores.txt', 'r', encoding='utf-8') as arquivo:
                self.ranking_melhores = [linha for linha in arquivo.read().splitlines() if linha.strip()]
        except FileNotFoundError:
            self.ranking_melhores = []

        try:
            with open('ranking/piores.txt', 'r', encoding='utf-8') as arquivo:
                self.ranking_piores = [linha for linha in arquivo.read().splitlines() if linha.strip()]
        except FileNotFoundError:
            self.ranking_piores = []

        self.ranking_melhores = self.limitar_ranking(self.ranking_melhores, True)
        self.ranking_piores = self.limitar_ranking(self.ranking_piores, False)

        resultado = self.sessao.get('resultado_partida') if self.sessao is not None else None

        if jogadores is not None:
            nome_1, pontos_1, raposa, cor = jogadores[0]
            nome_2, pontos_2, raposa, cor = jogadores[1]

            if pontos_1 == pontos_2:
                self.registrar_resultado(self.ranking_melhores, nome_1, pontos_1, True)
                self.registrar_resultado(self.ranking_melhores, nome_2, pontos_2, True)
            else:
                self.registrar_resultado(self.ranking_melhores, nome_2, pontos_2, True)

                if pode_entrar_piores:
                    self.registrar_resultado(self.ranking_piores, nome_1, pontos_1, False)

        self.ranking_melhores = self.limitar_ranking(self.ranking_melhores, True)
        self.ranking_piores = self.limitar_ranking(self.ranking_piores, False)

        if jogadores is not None:
            if pontos_1 == pontos_2:
                posicao_1 = self.posicao_no_ranking(self.ranking_melhores, nome_1)
                posicao_2 = self.posicao_no_ranking(self.ranking_melhores, nome_2)

                if posicao_1 is not None and posicao_1 == posicao_2:
                    self.mensagem_empate = ['Empataram, mas garantiram juntos', f'o {posicao_1}º lugar no ranking dos vencedores!', 'Dividam a glória!']

                elif posicao_1 is not None and posicao_2 is not None:
                    self.mensagem_empate = ['Empataram nesta partida!', f'{nome_1}: {posicao_1}º lugar!', f'{nome_2}: {posicao_2}º lugar!', 'Os melhores resultados de cada um foram mantidos!']

                elif posicao_1 is not None:
                    self.mensagem_empate = ['Empataram nesta partida!', f'{nome_1}: {posicao_1}º lugar nos vencedores!', f'{nome_2} ficou fora do ranking!', 'Cada nome mantém seu melhor resultado!']

                elif posicao_2 is not None:
                    self.mensagem_empate = ['Empataram nesta partida!', f'{nome_2}: {posicao_2}º lugar nos vencedores!', f'{nome_1} ficou fora do ranking!', 'Cada nome mantém seu melhor resultado!']

                else:
                    self.mensagem_empate = ['Nem decidiram quem joga melhor,', 'nem entraram no ranking dos vencedores!', 'Vamos melhorar os dois, né!']

            else:
                posicao_vencedor = self.posicao_no_ranking(self.ranking_melhores, nome_2)
                posicao_perdedor = self.posicao_no_ranking(self.ranking_piores, nome_1)

                if posicao_vencedor is not None:
                    self.mensagem_melhores = ['Parabéns, você entrou no', 'ranking dos vencedores!']
                else:
                    self.mensagem_melhores = ['Ganhou, mas não entrou no', 'ranking dos vencedores!', 'Vamos querer mais', 'na próxima, né!']

                if pode_entrar_piores:
                    if posicao_perdedor is not None:
                        self.mensagem_piores = ['Você foi tão ruim que', 'entrou no ranking dos', 'perdedores, melhore!']
                    else:
                        self.mensagem_piores = ['Você foi mal, mas nem tanto!', 'Se contente em não ter', 'entrado no ranking', 'dos perdedores!']
                else:
                    self.mensagem_piores = ['Você já venceu uma partida', 'e não concorre ao ranking', 'dos perdedores nesta revanche!']

                if resultado is not None and resultado['rodada'] == 2:
                    if not pode_entrar_piores:
                        self.mensagem_piores = ['Decaiu, hein! Sorte sua', 'ter uma vitória para evitar', 'uma nova entrada no', 'ranking dos perdedores!']

                    if resultado['vencedor_anterior'] is not None and resultado['vencedor'] != resultado['vencedor_anterior']:
                        if posicao_vencedor is not None:
                            self.mensagem_melhores = ['Perdeu uma, mas amassou', 'essa! Vitória com direito', 'a ranking!']
                        else:
                            self.mensagem_melhores = ['Você buscou a sua revanche,', 'mas ainda dá para', 'fazer melhor!']

            if resultado is not None and resultado['rodada'] == 2:
                self.sugestao_melhor_tres = ['Já rolou uma revanche!', 'Bora completar a melhor de três!']

            if resultado is not None and resultado['rodada'] == 3:
                vitorias = resultado['vitorias']
                nomes = self.sessao['nomes']
                self.placar_combate = f'{nomes[0]} {vitorias[0]} x {vitorias[1]} {nomes[1]}!'

                if vitorias[0] == vitorias[1]:
                    mensagem = ['A melhor de três terminou', f'empatada em {vitorias[0]} a {vitorias[1]}!', 'Mais três para desempatar!']
                    self.mensagens_combate = [('Combate empatado!', mensagem, c.LARGURA_TELA // 2)]

                else:
                    campeao = 0 if vitorias[0] > vitorias[1] else 1
                    perdedor = 1 - campeao

                    posicao_campeao = self.posicao_no_ranking(self.ranking_melhores, nomes[campeao])
                    posicao_perdedor = self.posicao_no_ranking(self.ranking_piores, nomes[perdedor])

                    if posicao_campeao is not None:
                        positiva = ['Parabéns pela vitória', 'no combate e pela vaga', 'no ranking dos vencedores!', 'Pode comemorar!']
                    else:
                        positiva = ['Parabéns pela vitória', 'no combate!', 'Mas ficou fora do ranking!', 'Vamos querer mais na próxima!']

                    if posicao_perdedor is not None:
                        negativa = ['Perdeu o combate e ainda', 'ficou no ranking dos', 'perdedores! Vai treinar', 'para deixar de ser figurante!']

                    elif perdedor in self.sessao['vencedores']:
                        negativa = ['Nem com três para ganhar!', 'Sorte sua ter uma vitória', 'para te segurar fora do', 'ranking dos perdedores!']

                    else:
                        negativa = ['Nem uma vitória para contar!', 'Só escapou dos piores porque', 'já tinha gente passando', 'mais vergonha que você!']

                    self.mensagens_combate = [(f'{nomes[campeao]} venceu!', positiva, 400), (f'{nomes[perdedor]} perdeu!', negativa, 880)]

        if jogadores is not None:
            with open('ranking/melhores.txt', 'w', encoding='utf-8') as arquivo:
                arquivo.write('\n'.join(self.ranking_melhores))

            with open('ranking/piores.txt', 'w', encoding='utf-8') as arquivo:
                arquivo.write('\n'.join(self.ranking_piores))

        self.rolagem_maxima_melhores = max(0, len(self.ranking_melhores) * self.altura_linha - self.area_melhores.height)
        self.rolagem_maxima_piores = max(0, len(self.ranking_piores) * self.altura_linha - self.area_piores.height)

        self.exibindo_feedback = bool(self.mensagem_melhores or self.mensagem_piores or self.mensagem_empate or self.mensagens_combate)
        self.duracao_feedback = 6000
        self.inicio_feedback = pygame.time.get_ticks()

        self._iniciar_controle()

    # Insere o nome ou melhora seu registro: maior pontuação nos vencedores e menor nos perdedores.
    def registrar_resultado(self, ranking, nome, pontos, melhores):
        chave = normalizar_nome(nome)

        for indice, linha in enumerate(ranking):
            nome_salvo, pontos_salvos = linha.rsplit(' - ', 1)

            if normalizar_nome(nome_salvo) == chave:
                pontos_salvos = int(pontos_salvos)

                if (melhores and pontos > pontos_salvos) or (not melhores and pontos < pontos_salvos):
                    ranking[indice] = f'{nome_salvo} - {pontos}'

                return

        ranking.append(f"{' '.join(nome.split())} - {pontos}")

    # Procura o nome e retorna sua posição, atribuindo a mesma colocação a pontuações empatadas.
    def posicao_no_ranking(self, ranking, nome):
        pontos_anteriores = None
        posicao = 0

        for indice, linha in enumerate(ranking):
            nome_salvo, pontos = linha.rsplit(' - ', 1)
            pontos = int(pontos)

            if pontos != pontos_anteriores:
                posicao = indice + 1

            pontos_anteriores = pontos

            if normalizar_nome(nome_salvo) == normalizar_nome(nome):
                return posicao

        return None

    # Unifica nomes equivalentes, ordena os registros e mantém os dez primeiros com os empatados no corte.
    def limitar_ranking(self, ranking, melhores):
        registros = {}

        for linha in ranking:
            nome, pontos = linha.rsplit(' - ', 1)
            nome = ' '.join(nome.split())
            pontos = int(pontos)
            chave = normalizar_nome(nome)

            if chave not in registros:
                registros[chave] = (nome, pontos)

            else:
                nome_salvo, pontos_salvos = registros[chave]

                if (melhores and pontos > pontos_salvos) or (not melhores and pontos < pontos_salvos):
                    registros[chave] = (nome_salvo, pontos)

        ranking = [f'{nome} - {pontos}' for nome, pontos in registros.values()]
        ranking.sort(key=lambda linha: int(linha.rsplit(' - ', 1)[1]), reverse=melhores)

        if len(ranking) <= 10:
            return ranking

        limite = int(ranking[9].rsplit(' - ', 1)[1])

        if melhores:
            return [linha for linha in ranking if int(linha.rsplit(' - ', 1)[1]) >= limite]

        return [linha for linha in ranking if int(linha.rsplit(' - ', 1)[1]) <= limite]

    # Desenha as duas listas com rolagem e os botões; durante o feedback, sobrepõe as mensagens do resultado.
    def desenha(self, window):
        window.fill(c.COR_FUNDO)
        window.blit(self.fundo, (0, 0))

        pygame.draw.rect(window, c.COR_CREME_CLARO, (0, 0, c.LARGURA_TELA, c.ALTURA_TELA), 5)
        pygame.draw.rect(window, c.COR_CAIXA, self.melhores)
        pygame.draw.rect(window, c.COR_CAIXA, self.piores)
        pygame.draw.rect(window, c.COR_BORDA_CAIXAS, self.melhores, 4)
        pygame.draw.rect(window, c.COR_BORDA_CAIXAS, self.piores, 4)

        for botao, nome in [(self.revanche, 'Revanche'), (self.menu, 'Menu')]:
            mouse_no_botao = not self.exibindo_feedback and botao.collidepoint(pygame.mouse.get_pos())
            cor_botao = c.COR_BOTAO_HOVER if mouse_no_botao else c.COR_BOTAO
            cor_borda = c.COR_BORDA_ESCURA

            pygame.draw.rect(window, cor_botao, botao)
            pygame.draw.rect(window, cor_borda, botao, 2)

            texto = self.proximo.render(nome, True, c.COR_TEXTO)
            window.blit(texto, texto.get_rect(center=botao.center))

        melhores = texto_com_icone(self.fonte_titulo_ranking, self.fonte_emojis, 'Vencedores', '🏆', c.COR_VENCEDORES)
        piores = texto_com_icone(self.fonte_titulo_ranking, self.fonte_emojis, 'Perdedores', '👎', c.COR_PERDEDORES)

        window.blit(melhores, melhores.get_rect(midbottom=(self.melhores.centerx, self.melhores.top - 12)))
        window.blit(piores, piores.get_rect(midbottom=(self.piores.centerx, self.piores.top - 12)))

        for ranking, area, rolagem in [(self.ranking_melhores, self.area_melhores, self.rolagem_melhores), (self.ranking_piores, self.area_piores, self.rolagem_piores)]:
            clip_anterior = window.get_clip()
            window.set_clip(area)

            pontos_anteriores = None
            posicao = 0

            for indice, linha in enumerate(ranking):
                nome, pontos = linha.rsplit(' - ', 1)
                pontos = int(pontos)

                if pontos != pontos_anteriores:
                    posicao = indice + 1

                pontos_anteriores = pontos

                texto = self.placares.render(f'{posicao}° - {nome}: {pontos}', True, c.COR_TEXTO)
                window.blit(texto, texto.get_rect(midtop=(area.centerx, area.top + indice * self.altura_linha - rolagem)))

            window.set_clip(clip_anterior)

            altura_total = len(ranking) * self.altura_linha
            rolagem_maxima = max(0, altura_total - area.height)

            if rolagem_maxima > 0:
                altura_barra = max(20, int(area.height ** 2 / altura_total))
                y_barra = area.top + int(rolagem / rolagem_maxima * (area.height - altura_barra))

                pygame.draw.rect(window, c.COR_FUNDO_SELECIONADO, (area.right - 6, area.top, 6, area.height))
                pygame.draw.rect(window, c.COR_FOCO, (area.right - 6, y_barra, 6, altura_barra))

        if self.exibindo_feedback:
            largura, altura = window.get_size()
            tempo = pygame.time.get_ticks() - self.inicio_feedback

            fundo = pygame.transform.smoothscale(window, (max(1, largura // 10), max(1, altura // 10)))
            fundo = pygame.transform.smoothscale(fundo, (largura, altura))
            window.blit(fundo, (0, 0))

            camada = pygame.Surface((largura, altura), pygame.SRCALPHA)
            camada.fill((*c.COR_FUNDO, 100))
            window.blit(camada, (0, 0))

            opacidade = int(255 * max(0, min(1, (self.duracao_feedback - tempo) / 400)))

            if self.placar_combate:
                placar = self.proximo.render(self.placar_combate, True, c.COR_TITULO)
                placar.set_alpha(opacidade)
                window.blit(placar, placar.get_rect(center=(largura // 2, altura // 2 - 170)))

            if self.mensagens_combate:
                mensagens = self.mensagens_combate
            elif self.mensagem_empate:
                mensagens = [('Empate!', self.mensagem_empate, largura // 2)]
            else:
                mensagens = [(self.nome_vencedor, self.mensagem_melhores, 400), (self.nome_perdedor, self.mensagem_piores, 880)]

            for titulo, mensagem, centro in mensagens:
                texto_titulo = self.placares.render(titulo, True, c.COR_TITULO)
                texto_titulo.set_alpha(opacidade)
                window.blit(texto_titulo, texto_titulo.get_rect(center=(centro, altura // 2 - 90)))

                # Todas as mensagens começam na mesma altura, independentemente
                # da quantidade de linhas de cada jogador ou resultado.
                y = altura // 2 - 34

                for linha in mensagem:
                    texto = self.fonte_feedback.render(linha, True, c.COR_TITULO)
                    texto.set_alpha(opacidade)
                    window.blit(texto, texto.get_rect(center=(centro, y)))
                    y += 34

            y = altura // 2 + 150

            for linha in self.sugestao_melhor_tres:
                texto = self.fonte_feedback.render(linha, True, c.COR_TITULO)
                texto.set_alpha(opacidade)
                window.blit(texto, texto.get_rect(center=(largura // 2, y)))
                y += 34

        self._desenhar_controle(window)


    # Trata a rolagem dos rankings e os cliques em revanche e menu, bloqueando-os durante o feedback.
    def tratar_eventos(self, event):
        if self._evento_controle(event):
            return

        if self.exibindo_feedback:
            return

        if event.type == pygame.MOUSEWHEEL:
            if self.melhores.collidepoint(pygame.mouse.get_pos()):
                self.rolagem_melhores = max(0, min(self.rolagem_melhores - event.y * self.altura_linha, self.rolagem_maxima_melhores))
            elif self.piores.collidepoint(pygame.mouse.get_pos()):
                self.rolagem_piores = max(0, min(self.rolagem_piores - event.y * self.altura_linha, self.rolagem_maxima_piores))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu.collidepoint(event.pos):
                self.click.play()
                self.voltar_menu = True
            elif self.revanche.collidepoint(event.pos):
                self.click.play()
                self.voltar_selecao = True

    # Controla o tempo do feedback e encaminha a revanche ou o retorno ao menu quando solicitados.
    def atualiza(self, jogo):
        self._atualizar_controle()
        if self.exibindo_feedback:
            self.exibindo_feedback = pygame.time.get_ticks() - self.inicio_feedback < self.duracao_feedback

            if self.exibindo_feedback:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return

        if self.voltar_menu:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            jogo.tela_atual = Tela_Inicial()
            return

        if self.voltar_selecao:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            self.voltar_selecao = False
            jogo.tela_atual = Tela_Musicas(self.sessao, self)
            return

        if self.menu.collidepoint(pygame.mouse.get_pos()) or self.revanche.collidepoint(pygame.mouse.get_pos()):
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    # Move o foco entre botões, rola o ranking correspondente e confirma a navegação pelo controle.
    def _comando_controle(self, acao, jogador):
        if self.exibindo_feedback:
            return
        if acao in ('esquerda', 'direita'):
            self._foco_controle = 0 if acao == 'esquerda' else 1
        elif acao in ('cima', 'baixo'):
            passo = self.altura_linha * (1 if acao == 'baixo' else -1)
            if self._foco_controle == 0:
                self.rolagem_melhores = max(0, min(self.rolagem_melhores + passo, self.rolagem_maxima_melhores))
            else:
                self.rolagem_piores = max(0, min(self.rolagem_piores + passo, self.rolagem_maxima_piores))
        elif acao in ('a', 'start'):
            self.click.play()
            if self._foco_controle == 0:
                self.voltar_selecao = True
            else:
                self.voltar_menu = True
        elif acao in ('b', 'voltar'):
            self.click.play()
            self.voltar_menu = True

