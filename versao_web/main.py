# /// script
# dependencies = ["pygame-ce"]
# ///
# Entrada exclusiva da versão web; o jogo original permanece na pasta ao lado.
import asyncio
import os
import sys
from pathlib import Path

import pygame

RAIZ = Path(__file__).resolve().parent
os.chdir(RAIZ)
sys.path.insert(0, str(RAIZ / "codigo"))

from jogo import Jogo
from recursos_web import configurar_navegador, salvar_ranking


# Devolve o controle ao navegador em cada quadro para permitir entrada, áudio e desenho.
async def main():
    configurar_navegador()
    jogo = Jogo()
    await jogo.game_loop()
    salvar_ranking(forcar=True)


asyncio.run(main())
