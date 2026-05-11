# config.py — Configurações globais do MaqControl
from pathlib import Path

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretório de dados (arquivos JSON)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Caminhos dos arquivos JSON
ARQUIVO_MAQUINAS     = DATA_DIR / "maquinas.json"
ARQUIVO_SETORES      = DATA_DIR / "setores.json"
ARQUIVO_MANUTENCOES  = DATA_DIR / "manutencoes.json"

# Configurações de manutenção
DIAS_ALERTA_MANUTENCAO = 15  # Avisar X dias antes da manutenção

# Configurações de e-mail (opcional — preencha se quiser usar)
EMAIL_REMETENTE  = ""
EMAIL_SENHA      = ""
EMAIL_DESTINATARIOS: list[str] = []
SMTP_HOST        = "smtp.gmail.com"
SMTP_PORT        = 587
