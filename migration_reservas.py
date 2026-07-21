# migration_reservas.py — Criação e Inicialização do Banco de Dados JSON para Reservas
import os
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
ARQUIVO_RESERVAS = DATA_DIR / "reservas.json"

def run_migration():
    print("Iniciando migração do Módulo Reserva de Salas...")
    
    # Garante que o diretório de dados existe
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Cria o arquivo reservas.json se não existir
    if not ARQUIVO_RESERVAS.exists():
        with open(ARQUIVO_RESERVAS, "w", encoding="utf-8") as f:
            json.dump([], f)
        print(f"Banco de dados inicializado com sucesso: {ARQUIVO_RESERVAS}")
    else:
        print(f"Banco de dados já existente: {ARQUIVO_RESERVAS}")
        
    print("Migração concluída com sucesso!")

if __name__ == "__main__":
    run_migration()
