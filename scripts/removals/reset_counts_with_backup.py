#!/usr/bin/env python3
"""
Script para resetar a 0 todos os counts do original_categories.json, 
mantendo um backup do arquivo original.
"""
import json
import os
import shutil
from datetime import datetime

def reset_counts_with_backup():
    """
    Cria um backup do arquivo original_categories.json,
    depois define todos os counts para 0 e salva o arquivo atualizado.
    """
    file_path = "articles/original_categories.json"
    
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(file_path):
            print(f"Erro: O arquivo {file_path} não foi encontrado.")
            return False
        
        # Criar backup com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"articles/original_categories_backup_{timestamp}.json"
        
        shutil.copy2(file_path, backup_path)
        print(f"Backup criado em: {backup_path}")
        
        # Ler o arquivo JSON
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                entries = json.load(f)
                print(f"Carregadas {len(entries)} entradas do arquivo.")
            except json.JSONDecodeError:
                print("Erro: O arquivo não contém JSON válido.")
                return False
        
        # Resetar todos os counts para 0
        modified_count = 0
        for entry in entries:
            if "count" in entry:
                entry["count"] = 0
                modified_count += 1
        
        # Salvar o arquivo de volta
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=4)
            
        print(f"Resetados {modified_count} counts para 0 com sucesso!")
        print(f"Em caso de necessidade, restaure o backup de {backup_path}")
        return True
        
    except Exception as e:
        print(f"Erro durante o processamento: {str(e)}")
        return False

if __name__ == "__main__":
    reset_counts_with_backup()
