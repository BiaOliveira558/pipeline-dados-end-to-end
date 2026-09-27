# Pipeline de Dados End-to-End

Projeto de estudo de um pipeline de dados completo, usando ferramentas comuns no mercado.

## Ferramentas

- **Databricks (Free Edition):** ambiente onde os dados são armazenados e processados
- **PySpark:** limpeza e transformação dos dados
- **dbt:** criação das tabelas finais com SQL, incluindo testes de qualidade
- **MLflow:** registro dos treinos de modelos de machine learning
- **Apache Airflow:** agendamento e ordem de execução das etapas
- **Power BI:** dashboard final

## Arquitetura

Arquitetura medalhão:

- **Bronze:** dado cru, como chegou da fonte
- **Prata:** dado limpo e padronizado
- **Ouro:** dado pronto para análise
