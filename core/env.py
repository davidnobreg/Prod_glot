from decouple import Config, RepositoryEnv
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent  # glot/
ENV_PATH = BASE_DIR / "configuration" / ".env"

config = Config(RepositoryEnv(str(ENV_PATH)))

def get_env(name: str, *, default=None, required=False):
    try:
        value = config(name, default=default)

        if required and (value is None or value == ""):
            raise ValueError(f"Variável obrigatória não definida: {name}")

        return value

    except Exception as e:
        print("\n❌ ERRO DE CONFIGURAÇÃO")
        print(f"➡ {e}")
        print(f"➡ Arquivo esperado: {ENV_PATH}\n")
        sys.exit(1)
