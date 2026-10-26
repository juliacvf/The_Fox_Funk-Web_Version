"""Prepara uma cópia estática para GitHub Pages, com arquivos abaixo de 25 MiB."""

import hashlib
import json
import shutil
from pathlib import Path


# Divide o pacote já compilado e adapta só o carregador HTML da distribuição Pages.
def main():
    raiz = Path(__file__).resolve().parent
    origem = raiz / "build" / "web"
    # A publicação fica na raiz do mesmo repositório; os fontes web continuam separados.
    destino = raiz.parent
    partes = destino / "dados"
    partes.mkdir(parents=True, exist_ok=True)
    pacote = origem / "thefoxfunk-web.apk"
    nomes = []
    resumo = hashlib.sha256()
    with pacote.open("rb") as arquivo:
        while trecho := arquivo.read(20 * 1024 * 1024):
            nome = f"dados/parte-{len(nomes) + 1:02d}.bin"
            (destino / nome).write_bytes(trecho)
            resumo.update(trecho)
            nomes.append(nome)

    html = (origem / "index.html").read_text(encoding="utf-8")
    trecho_original = '    apk = "thefoxfunk-web.apk"'
    trecho_novo = '''    # As partes são reunidas pelo navegador antes de montar o pacote Pygbag.
    while not platform.window.foxPackageReady:
        if platform.window.foxPackageError:
            raise RuntimeError(str(platform.window.foxPackageError))
        await asyncio.sleep(0)
    apk = str(platform.window.foxPackageURL)'''
    if trecho_original not in html:
        raise RuntimeError("O carregador Pygbag mudou; confira a referência ao pacote antes de publicar.")
    html = html.replace(trecho_original, trecho_novo, 1)
    carregador = '''
<div id="fox-download" role="status" style="position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:1001;background:#fff9f0;color:#252f49;padding:20px;font:18px sans-serif;text-align:center;border:3px solid #4173af">Carregando o jogo… 0%</div>
<script>
window.foxPackageReady = false;
window.foxPackageError = '';
(async function () {
    const status = document.getElementById('fox-download');
    const arquivos = __PARTES__;
    let concluidos = 0;
    try {
        const partes = await Promise.all(arquivos.map(async arquivo => {
            const resposta = await fetch(arquivo);
            if (!resposta.ok) throw new Error('Não foi possível carregar ' + arquivo);
            const dados = await resposta.arrayBuffer();
            concluidos += 1;
            status.textContent = 'Carregando o jogo… ' + Math.round(100 * concluidos / arquivos.length) + '%';
            return dados;
        }));
        window.foxPackageURL = URL.createObjectURL(new Blob(partes, {type: 'application/zip'}));
        window.foxPackageReady = true;
        status.hidden = true;
    } catch (erro) {
        window.foxPackageError = String(erro);
        status.textContent = 'Não foi possível carregar o jogo. Atualize a página para tentar novamente.';
        console.error(erro);
    }
})();
</script>
'''.replace("__PARTES__", json.dumps(nomes))
    html = html.replace("</body>", carregador + "\n</body>", 1)
    (destino / "index.html").write_text(html, encoding="utf-8")
    (destino / ".nojekyll").touch()
    shutil.copy2(origem / "favicon.png", destino / "favicon.png")
    assert resumo.hexdigest() == hashlib.sha256(pacote.read_bytes()).hexdigest()
    assert all((destino / nome).stat().st_size < 25 * 1024 * 1024 for nome in nomes)
    print(f"GitHub Pages pronto em {destino}; {len(nomes)} partes de até 20 MiB.")


if __name__ == "__main__":
    main()
