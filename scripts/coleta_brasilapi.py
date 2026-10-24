"""
Coleta da tabela da BrasilAPI:
  - brasilapi_bancos: lista de instituições financeiras (código, ISPB, nomes)

Salva em: data/raw/<tabela>/<data_hora>/data.json
"""

import time
from datetime import datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "raw"

URLS = {
    "brasilapi_bancos": "https://brasilapi.com.br/api/banks/v1",
}


def fazer_pedido(url, tentativas=3):
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = requests.get(url, timeout=300)
            resposta.raise_for_status()
            return resposta
        except requests.RequestException as erro:
            print(f"   tentativa {tentativa} falhou: {erro}")
            if tentativa == tentativas:
                raise
            time.sleep(5 * tentativa)


def salvar(texto, pasta, nome_arquivo):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome_arquivo).write_text(texto, encoding="utf-8")


def main(carimbo=None):
    carimbo = carimbo or datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print(f"Coleta BrasilAPI iniciada: {carimbo}\n")

    for nome, url in URLS.items():
        print(f"[...] {nome}")
        try:
            inicio = time.time()
            resposta = fazer_pedido(url)

            # A BrasilAPI devolve uma lista diretamente, como o IBGE
            linhas = len(resposta.json())

            salvar(resposta.text, PASTA_RAW / nome / carimbo, "data.json")

            segundos = time.time() - inicio
            tamanho_mb = len(resposta.content) / 1_000_000
            print(f"[OK]  {nome}: {linhas} linhas, {tamanho_mb:.2f} MB, {segundos:.0f}s")
        except Exception as erro:
            print(f"[ERRO] {nome}: {erro}")
        print()

    print("Coleta finalizada.")


if __name__ == "__main__":
    main()