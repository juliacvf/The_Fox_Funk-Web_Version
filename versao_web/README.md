# The Fox Funk — versão extra para navegador

Esta pasta contém os fontes adaptados ao Pygbag. A publicação web fica um nível acima, em `TheFoxFunk-navegador`. O jogo para computador e o site de apresentação ficam separados, nas pastas `26-2-devlife-pygame-Branco` e `26-2-devlife-pygame-site-Branco` do workspace.

## Jogar neste computador

Abra `Jogar no navegador.cmd`. Ele inicia um servidor local e abre o jogo no navegador. Mantenha a janela do servidor aberta durante a partida; para encerrá-lo, feche essa janela.

Também é possível iniciar manualmente, a partir desta pasta:

```console
python -m http.server 8000 --bind 127.0.0.1 --directory build/web
```

Depois acesse <http://127.0.0.1:8000>. Não abra `build/web/index.html` por duplo clique: o carregamento do Pygbag precisa do servidor.

Clique na área do jogo para liberar o áudio. O primeiro acesso precisa de internet para baixar o Python/Pygame do Pygbag. A versão inclui as 100 músicas; o pacote inicial tem aproximadamente 130 MB, além do runtime.

## O que foi adaptado

- `main.py` é a entrada da versão web e o ciclo principal usa `await asyncio.sleep(0)`.
- As funções auxiliares ficam em `codigo/funcoes.py`, seguindo a organização do jogo principal.
- A fonte Noto Sans Symbols 2 está incluída em `fontes`, com sua licença, para desenhar os emojis do ranking e as estrelas de dificuldade sem depender de fontes do Windows.
- As músicas e os efeitos são cópias em OGG. As músicas têm no máximo 240 segundos; os arquivos originais não foram convertidos nem cortados.
- `audios.json` relaciona cada arquivo original ao nome correspondente na versão web.
- Os rankings começam vazios e são guardados no armazenamento local do navegador. Não são compartilhados entre computadores nem entre sites diferentes. A disponibilidade depende das configurações de armazenamento do navegador.
- Os comandos de teclado são os mesmos do jogo original. O suporte físico a controles também depende do navegador e do dispositivo.

Esta é uma cópia do estado atual do jogo. Alterações futuras no original não são transferidas automaticamente para esta pasta.

## Recriar a versão publicável

Após editar esta cópia, instale as ferramentas e gere novamente o pacote:

```console
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-web.txt
.venv\Scripts\python -m pygbag --build --no_opt --cdn https://pygame-web.github.io/archives/0.9/ --template template-web.tmpl --PYBUILD 3.12 --title "The Fox Funk" .
```

O template local `template-web.tmpl` define a página de abertura do jogo. O endereço de arquivos do Pygbag está explícito para usar os recursos compatíveis com esta versão da ferramenta.

## Publicar no GitHub Pages

Os arquivos publicáveis estão **na raiz do repositório, um nível acima desta pasta**. A distribuição divide o pacote em sete arquivos de até 20 MiB, que o navegador reúne automaticamente. Não envie o `.apk` de `build/web` para o repositório: ele ultrapassa o limite de tamanho por arquivo do GitHub.

1. Mantenha `index.html`, `favicon.png`, `.nojekyll` e a pasta `dados` na raiz do repositório.
2. Envie todos esses arquivos para o GitHub, mantendo a estrutura da pasta `dados`.
3. Em **Settings → Pages**, escolha **Deploy from a branch**, selecione a branch `main` e a pasta **/(root)** e salve.
4. Abra o endereço informado pelo GitHub após a publicação terminar.

Se a raiz já tiver o site de apresentação, coloque esses arquivos em uma pasta `jogar` em vez de substituir seu `index.html`. Nesse caso, o jogo fica disponível no endereço do site seguido de `/jogar/`.

Depois de uma nova compilação Pygbag, atualize esta distribuição antes de copiar novamente os arquivos:

```console
python preparar_pages.py
```

O script `preparar_pages.py` atualiza diretamente a publicação na raiz de `TheFoxFunk-navegador`. Ele não escreve na pasta do jogo para computador. As pastas desta cópia web não precisam ser movidas nem misturadas com as pastas do jogo original.

## Outras hospedagens

Publique **todo o conteúdo de `build/web`**, incluindo os arquivos de pacote e o `index.html`, em uma hospedagem de arquivos estáticos. A pasta já é o resultado preparado para hospedagem; nenhuma publicação foi feita automaticamente.

No itch.io, compacte o conteúdo de `build/web`, selecione o tipo HTML e marque que o jogo será executado no navegador.

Referências: [tutorial do Insper](https://github.com/Insper/devlife_261/blob/main/pybag/pygbag-tutorial.md) e [documentação do Pygbag](https://pygame-web.github.io/wiki/pygbag/).
