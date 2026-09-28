"""
Coleta dados das APIs do Banco Central (Pix) e do IBGE (população)
e envia os arquivos JSON crus para o Volume do Databricks (camada bronze).

Uso:
    python coleta/coletar_dados.py --inicio 202601 --fim 202603
"""

import argparse
import io
import json

import requests
from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient

# Endereços das APIs
BASE_PIX = "https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata"
URL_IBGE = "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/{ano}?formato=json"

# Pasta de destino no Databricks
VOLUME = "/Volumes/workspace/bronze/arquivos_api"

# Máximo de linhas pedidas por consulta (o Brasil tem ~5.570 municípios)
LIMITE_LINHAS = 10000


def gerar_meses(inicio, fim):
    """Gera a lista de meses entre inicio e fim, no formato AAAAMM."""
    ano, mes = int(inicio[:4]), int(inicio[4:])
    ano_fim, mes_fim = int(fim[:4]), int(fim[4:])
    meses = []
    while (ano, mes) <= (ano_fim, mes_fim):
        meses.append(f"{ano}{mes:02d}")
        mes += 1
        if mes == 13:
            ano, mes = ano + 1, 1
    return meses


def buscar_json(url):
    """Chama uma API e devolve a resposta em JSON. Dá erro se a API falhar."""
    resposta = requests.get(url, timeout=120)
    resposta.raise_for_status()
    return resposta.json()


def enviar_para_volume(cliente, caminho, dados):
    """Transforma os dados em arquivo JSON e envia para o Volume do Databricks."""
    conteudo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
    cliente.files.upload(caminho, io.BytesIO(conteudo), overwrite=True)


def coletar_pix_municipio(cliente, ano_mes):
    # DataBase significa "a partir deste mês", então filtramos para trazer só o mês pedido
    url = (
        f"{BASE_PIX}/TransacoesPixPorMunicipio(DataBase=@DataBase)"
        f"?@DataBase='{ano_mes}'&$filter=AnoMes%20eq%20{ano_mes}"
        f"&$top={LIMITE_LINHAS}&$format=json"
    )
    dados = buscar_json(url)
    linhas = dados.get("value", [])

    if not linhas:
        print(f"  Pix por município {ano_mes}: sem dados, pulando")
        return
    if len(linhas) == LIMITE_LINHAS:
        print(f"  ATENÇÃO: {ano_mes} atingiu o limite de {LIMITE_LINHAS} linhas, podem faltar dados")

    caminho = f"{VOLUME}/pix_municipio/pix_municipio_{ano_mes}.json"
    enviar_para_volume(cliente, caminho, dados)
    print(f"  Pix por município {ano_mes}: {len(linhas)} linhas enviadas")


def coletar_pix_fraudes(cliente, ano_mes):
    # Atenção: aqui o parâmetro é "Database", com b minúsculo
    # Também significa "a partir deste mês", então filtramos o mês pedido
    url = (
        f"{BASE_PIX}/EstatisticasFraudesPix(Database=@Database)"
        f"?@Database='{ano_mes}'&$filter=AnoMes%20eq%20{ano_mes}"
        f"&$format=json"
    )
    dados = buscar_json(url)
    linhas = dados.get("value", [])

    if not linhas:
        print(f"  Fraudes Pix {ano_mes}: sem dados, pulando")
        return

    caminho = f"{VOLUME}/pix_fraudes/pix_fraudes_{ano_mes}.json"
    enviar_para_volume(cliente, caminho, dados)
    print(f"  Fraudes Pix {ano_mes}: {len(linhas)} linhas enviadas")


def coletar_ibge_populacao(cliente, ano):
    url = URL_IBGE.format(ano=ano)
    dados = buscar_json(url)

    # A primeira linha da resposta do IBGE é o cabeçalho, não é dado
    if len(dados) <= 1:
        print(f"  IBGE população {ano}: sem dados, pulando")
        return

    caminho = f"{VOLUME}/ibge_populacao/ibge_populacao_{ano}.json"
    enviar_para_volume(cliente, caminho, dados)
    print(f"  IBGE população {ano}: {len(dados) - 1} municípios enviados")


def main():
    parser = argparse.ArgumentParser(description="Coleta dados do Pix e do IBGE")
    parser.add_argument("--inicio", required=True, help="Mês inicial no formato AAAAMM")
    parser.add_argument("--fim", required=True, help="Mês final no formato AAAAMM")
    args = parser.parse_args()

    load_dotenv()
    cliente = WorkspaceClient()

    meses = gerar_meses(args.inicio, args.fim)
    anos = sorted({mes[:4] for mes in meses})
    erros = []

    print(f"Coletando {len(meses)} meses: {meses[0]} até {meses[-1]}")

    for ano_mes in meses:
        print(f"\nMês {ano_mes}")
        for funcao in (coletar_pix_municipio, coletar_pix_fraudes):
            try:
                funcao(cliente, ano_mes)
            except Exception as erro:
                print(f"  ERRO em {funcao.__name__} {ano_mes}: {erro}")
                erros.append(f"{funcao.__name__} {ano_mes}")

    print("\nPopulação IBGE")
    for ano in anos:
        try:
            coletar_ibge_populacao(cliente, ano)
        except Exception as erro:
            print(f"  ERRO no IBGE {ano}: {erro}")
            erros.append(f"ibge {ano}")

    print("\nColeta finalizada.")
    if erros:
        print(f"Itens com erro ({len(erros)}): {erros}")


if __name__ == "__main__":
    main()