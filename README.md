# The Fox Funk — navegador

Esta pasta contém a versão web do jogo. O jogo para computador continua separado em `26-2-devlife-pygame-Branco`, e o site de apresentação continua em `26-2-devlife-pygame-site-Branco`.

## Testar

Abra `Jogar no navegador.cmd` nesta pasta e mantenha a janela do servidor aberta enquanto joga. Acesse <http://127.0.0.1:8000> e clique no jogo para liberar o áudio.

Se já houver uma janela do servidor antigo aberta, feche-a antes de iniciar esta versão.

O primeiro carregamento precisa de internet para buscar o runtime do Pygbag e carregar aproximadamente 130 MB do jogo.

Também é possível iniciar manualmente, a partir desta pasta:

```console
python -m http.server 8000 --bind 127.0.0.1
```

## Publicar no GitHub Pages

Envie esta pasta para um repositório próprio, mantendo na raiz `index.html`, `favicon.png`, `.nojekyll` e a pasta `dados` com suas sete partes.

No GitHub, selecione **Settings → Pages → Deploy from a branch → main → /(root)** e salve. Use o nome correto da branch principal caso não seja `main`.

O navegador reúne as partes automaticamente. Não é necessário enviar `versao_web/build`, que contém os pacotes grandes e está ignorado pelo Git.

## Atualizar o jogo

Os fontes adaptados ao Pygbag estão em `versao_web`. As mudanças feitas no jogo para computador não são copiadas automaticamente: precisam ser incorporadas nessa versão e compiladas conforme seu README.

Após compilar, execute nesta pasta:

```console
python versao_web/preparar_pages.py
```

Isso atualiza a publicação aqui, sem escrever na pasta do jogo para computador.
