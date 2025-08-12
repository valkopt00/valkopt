# Branch Data - Sistema JSON Simplificado
Atualizado automaticamente em: 2025-08-12 23:19:26

## 🎯 Arquitetura simplificada:
Apenas **3 ficheiros JSON** essenciais, comprimidos automaticamente pelo Netlify (~65% redução):

### 📱 Para a app principal:
- **articles.json** - Todas as categorias e artigos (ficheiro único)

### 🔍 Para funcionalidade de pesquisa:
- **articles_search.json** - Dados normalizados para pesquisa

### 🗂️ Para mapeamento de categorias:
- **original_categories.json** - Mapeamento de categorias originais

## ⚡ Performance esperada:
- **Carregamento inicial**: ~1.4M (2-4 segundos)
- **Todas as categorias**: Disponíveis imediatamente após carregamento
- **Zero problemas de timing**: Sem dependências entre ficheiros
