"""Adaptações exclusivas do navegador, sem dependências no jogo original."""

import json
import sys
from pathlib import Path

import pygame

CHAVE_RANKING = "the-fox-funk-ranking-v1"
_ultimo_ranking = None
_ultima_gravacao = 0


# Troca apenas o cursor visual; alguns navegadores não oferecem todos os cursores SDL.
def configurar_navegador():
    if sys.platform != "emscripten":
        return
    import platform

    platform.window.canvas.style.imageRendering = "pixelated"
    # Neste runtime, a música usa um elemento de áudio HTML, separado do mixer SDL.
    # Consulta o estado desse elemento para não reiniciar prévias que ainda estão tocando.
    platform.window.eval("""
        window.foxMusicIsPlaying = function () {
            const mm = window.MM;
            const track = mm && mm[mm.current_trackid];
            return !!(track && track.media && !track.media.paused && !track.media.ended);
        };
        window.foxMusicEnded = function (arquivo) {
            const mm = window.MM;
            const track = mm && mm[mm.current_trackid];
            return !!(track && track.url === arquivo && track.media && track.media.ended);
        };
    """)
    pygame.mixer.music.get_busy = lambda: bool(platform.window.foxMusicIsPlaying())
    trocar_cursor = pygame.mouse.set_cursor

    def cursor_compativel(*args, **kwargs):
        # Mantém a entrada funcionando mesmo se o navegador recusar o cursor pedido.
        try:
            trocar_cursor(*args, **kwargs)
        except pygame.error:
            pass

    pygame.mouse.set_cursor = cursor_compativel
    Path("ranking").mkdir(exist_ok=True)
    try:
        salvo = platform.window.localStorage.getItem(CHAVE_RANKING)
        if salvo:
            dados = json.loads(str(salvo))
            for nome in ("melhores", "piores"):
                texto = dados.get(nome, "")
                if isinstance(texto, str):
                    Path(f"ranking/{nome}.txt").write_text(texto, encoding="utf-8")
    except (ValueError, TypeError, OSError) as erro:
        print("Ranking local indisponível:", erro)


# Distingue o fim real da faixa da espera assíncrona para o navegador começar a tocá-la.
def musica_terminou(arquivo):
    if sys.platform == "emscripten":
        import platform

        return bool(platform.window.foxMusicEnded(arquivo))
    return not pygame.mixer.music.get_busy()


# Persiste alterações no navegador; o ranking é particular deste navegador e deste site.
def salvar_ranking(forcar=False):
    global _ultimo_ranking, _ultima_gravacao
    if sys.platform != "emscripten":
        return
    agora = pygame.time.get_ticks()
    if not forcar and agora - _ultima_gravacao < 1000:
        return
    _ultima_gravacao = agora
    try:
        import platform

        dados = {
            nome: Path(f"ranking/{nome}.txt").read_text(encoding="utf-8")
            for nome in ("melhores", "piores")
        }
        texto = json.dumps(dados, ensure_ascii=False)
        if texto != _ultimo_ranking:
            platform.window.localStorage.setItem(CHAVE_RANKING, texto)
            _ultimo_ranking = texto
    except (OSError, ValueError, TypeError) as erro:
        print("Não foi possível guardar o ranking neste navegador:", erro)
