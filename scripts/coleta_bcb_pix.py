"""
Coleta dos 4 recursos de Estatísticas do Pix (Banco Central).
Um pedido por recurso, sem paginação (a API do BCB não aceita $skip).

Salva em: data/raw/<recurso>/<data_hora>/data.json
"""

import time
from datetime import datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "raw"

BASE = "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata"
MES_INICIAL = "202601"

# Limite de linhas por pedido. Se um recurso devolver exatamente esse
# número, os dados podem ter sido cortados e o script avisa.
TOP_MAXIMO = 500000

URLS = {
    "bcb_pix_municipio":
        f"{BASE}/TransacoesPixPorMunicipio(DataBase=@DataBase)"
        f"?@DataBase='{MES_INICIAL}'&$top={TOP_MAXIMO}&$format=json",

    "bcb_estatisticas_transacoes":
        f"{BASE}/EstatisticasTransacoesPix(Database=@Database)"
        f"?@Database='{MES_INICIAL}'&$top={TOP_MAXIMO}&$format=json",

    "bcb_fraudes_med":
        f"{BASE}/EstatisticasFraudesPix(Database=@Database)"
        f"?@Database='{MES_INICIAL}'&$top={TOP_MAXIMO}&$format=json",

    "bcb_chaves_pix":
        f"{BASE}/ChavesPix(Data=@Data)"
        f"?@Data='{MES_INICIAL[:4]}-{MES_INICIAL[4:]}-01'&$top={TOP_MAXIMO}&$format=json",
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
    print(f"Coleta BCB Pix iniciada: {carimbo}")
    print(f"Dados a partir de: {MES_INICIAL}\n")

    for nome, url in URLS.items():
        print(f"[...] {nome}")
        try:
            inicio = time.time()
            resposta = fazer_pedido(url)
            linhas = len(resposta.json().get("value", []))

            salvar(resposta.text, PASTA_RAW / nome / carimbo, "data.json")

            segundos = time.time() - inicio
            tamanho_mb = len(resposta.content) / 1_000_000
            print(f"[OK]  {nome}: {linhas} linhas, {tamanho_mb:.1f} MB, {segundos:.0f}s")

            if linhas >= TOP_MAXIMO:
                print("      ATENÇÃO: atingiu o limite, os dados podem estar incompletos")
        except Exception as erro:
            print(f"[ERRO] {nome}: {erro}")
        print()

    print("Coleta finalizada.")


if __name__ == "__main__":
    main()