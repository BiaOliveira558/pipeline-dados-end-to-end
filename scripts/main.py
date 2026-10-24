"""
Ponto de entrada do pipeline de coleta.

1. Roda todas as coletas com o mesmo carimbo de data e hora
2. Envia para o volume do Databricks só as pastas criadas nesta execução
3. Remove os carimbos antigos, no PC e no volume, mantendo os mais recentes
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import coleta_bcb_pix
import coleta_brasilapi
import coleta_ibge

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "raw"
VOLUME = "dbfs:/Volumes/end_to_end_pipeline/bronze/raw_files"
MANTER_ULTIMOS = 3

COLETAS = [
    ("Banco Central", coleta_bcb_pix.main),
    ("IBGE", coleta_ibge.main),
    ("BrasilAPI", coleta_brasilapi.main),
]


# ---------------------------------------------------------------------------
# Etapa 1: coleta
# ---------------------------------------------------------------------------
def coletar(carimbo):
    for nome, funcao in COLETAS:
        print("=" * 60)
        print(f"COLETA: {nome}")
        print("=" * 60)
        funcao(carimbo)
        print()


# ---------------------------------------------------------------------------
# Etapa 2: envio para o Databricks
# ---------------------------------------------------------------------------
def enviar(carimbo):
    print("=" * 60)
    print("ENVIO PARA O DATABRICKS")
    print("=" * 60)

    # Só as pastas desta execução: data/raw/<fonte>/<carimbo>
    pastas = sorted(PASTA_RAW.glob(f"*/{carimbo}"))
    if not pastas:
        print("Nenhuma pasta nova para enviar.")
        return False

    tudo_ok = True
    for pasta in pastas:
        fonte = pasta.parent.name
        destino = f"{VOLUME}/{fonte}/{carimbo}"
        resultado = subprocess.run(
            ["databricks", "fs", "cp", "-r", str(pasta), destino, "--overwrite"],
            capture_output=True,
            text=True,
        )
        if resultado.returncode == 0:
            print(f"[OK]   {fonte}")
        else:
            print(f"[ERRO] {fonte}: {resultado.stderr.strip()}")
            tudo_ok = False

    return tudo_ok


# ---------------------------------------------------------------------------
# Etapa 3: limpeza dos carimbos antigos
# ---------------------------------------------------------------------------
def limpar_local():
    """Apaga do PC os carimbos antigos, mantendo os MANTER_ULTIMOS mais recentes."""
    for pasta_fonte in sorted(PASTA_RAW.iterdir()):
        if not pasta_fonte.is_dir():
            continue
        carimbos = sorted(p for p in pasta_fonte.iterdir() if p.is_dir())
        for antiga in carimbos[:-MANTER_ULTIMOS]:
            shutil.rmtree(antiga)
            print(f"[LOCAL]  removido {pasta_fonte.name}/{antiga.name}")


def limpar_volume():
    """Apaga do volume os carimbos antigos, mantendo os MANTER_ULTIMOS mais recentes."""
    for pasta_fonte in sorted(PASTA_RAW.iterdir()):
        if not pasta_fonte.is_dir():
            continue
        fonte = pasta_fonte.name
        caminho = f"{VOLUME}/{fonte}"

        listagem = subprocess.run(
            ["databricks", "fs", "ls", caminho],
            capture_output=True,
            text=True,
        )
        if listagem.returncode != 0:
            print(f"[VOLUME] não consegui listar {fonte}: {listagem.stderr.strip()}")
            continue

        carimbos = sorted(
            linha.strip().rstrip("/")
            for linha in listagem.stdout.splitlines()
            if linha.strip()
        )
        for antiga in carimbos[:-MANTER_ULTIMOS]:
            subprocess.run(
                ["databricks", "fs", "rm", "-r", f"{caminho}/{antiga}"],
                capture_output=True,
                text=True,
            )
            print(f"[VOLUME] removido {fonte}/{antiga}")


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main():
    carimbo = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"Pipeline de coleta iniciado: {carimbo}\n")

    coletar(carimbo)
    envio_ok = enviar(carimbo)

    if envio_ok:
        print("\n" + "=" * 60)
        print(f"LIMPEZA (mantendo os {MANTER_ULTIMOS} mais recentes)")
        print("=" * 60)
        limpar_local()
        limpar_volume()

    print(f"\nPipeline finalizado: {carimbo}")
    if not envio_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()