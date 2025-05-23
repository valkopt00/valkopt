import json

# Lista de fontes a remover
fontes_a_remover = {
    "Record", "AutoSport", "zerozero.pt", "Eurogamer", 
    "IGN Portugal", "Jornal de Negócios", "O Jornal Económico"
}

# Nome do ficheiro JSON
ficheiro_json = "articles/articles.json"

# Carregar os dados do ficheiro JSON
with open(ficheiro_json, "r", encoding="utf-8") as f:
    try:
        dados = json.load(f)
        if not isinstance(dados, dict):
            raise ValueError("O ficheiro JSON não tem o formato esperado (objeto com categorias).")
    except json.JSONDecodeError as e:
        print(f"Erro ao carregar JSON: {e}")
        exit(1)

# Filtrar artigos dentro da categoria "Outras Notícias"
if "Outras Notícias" in dados:
    dados["Outras Notícias"] = [
        artigo for artigo in dados["Outras Notícias"]
        if artigo.get("source") not in fontes_a_remover
    ]

# Guardar os dados filtrados de volta no ficheiro JSON
with open(ficheiro_json, "w", encoding="utf-8") as f:
    json.dump(dados, f, ensure_ascii=False, indent=4)

print(f"Artigos filtrados com sucesso. Restam {len(dados.get('Outras Notícias', []))} artigos em 'Outras Notícias'.")
