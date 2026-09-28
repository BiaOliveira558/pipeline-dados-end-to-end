from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient

# Lê o DATABRICKS_HOST e o DATABRICKS_TOKEN do arquivo .env
load_dotenv()

# Conecta ao Databricks usando essas informações
cliente = WorkspaceClient()

# Teste 1: quem sou eu?
usuario = cliente.current_user.me()
print(f"Conectada como: {usuario.user_name}")

# Teste 2: o volume existe?
caminho_volume = "/Volumes/workspace/bronze/arquivos_api"
arquivos = list(cliente.files.list_directory_contents(caminho_volume))
print(f"Volume encontrado. Arquivos dentro dele: {len(arquivos)}")