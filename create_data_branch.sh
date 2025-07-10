#!/bin/bash

# Script para criar a branch data com os ficheiros JSON atuais

echo "🔄 Criando branch data..."

# Certifique-se de que está na branch main e tudo está atualizado
git checkout main
git pull origin main

# Verificar se os ficheiros JSON existem
echo "📁 Verificando ficheiros JSON existentes..."
if [ -f "articles/articles.json" ]; then
    echo "✅ articles/articles.json encontrado"
else
    echo "❌ articles/articles.json não encontrado"
fi

if [ -f "articles/articles_priority.json" ]; then
    echo "✅ articles/articles_priority.json encontrado"
else
    echo "❌ articles/articles_priority.json não encontrado"
fi

if [ -f "articles/articles_secondary.json" ]; then
    echo "✅ articles/articles_secondary.json encontrado"
else
    echo "❌ articles/articles_secondary.json não encontrado"
fi

if [ -f "public/articles.json" ]; then
    echo "✅ public/articles.json encontrado"
else
    echo "❌ public/articles.json não encontrado"
fi

# Guardar os ficheiros JSON temporariamente
echo "💾 Guardando ficheiros JSON temporariamente..."
mkdir -p /tmp/json-backup-$(date +%Y%m%d)
BACKUP_DIR="/tmp/json-backup-$(date +%Y%m%d)"

# Copiar todos os ficheiros JSON que existem
cp articles/articles.json "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ articles/articles.json não copiado"
cp articles/articles_priority.json "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ articles/articles_priority.json não copiado"
cp articles/articles_secondary.json "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ articles/articles_secondary.json não copiado"
cp articles/original_categories.json "$BACKUP_DIR/" 2>/dev/null || echo "⚠️ articles/original_categories.json não copiado"
cp public/articles.json "$BACKUP_DIR/public_articles.json" 2>/dev/null || echo "⚠️ public/articles.json não copiado"
cp public/articles_priority.json "$BACKUP_DIR/public_articles_priority.json" 2>/dev/null || echo "⚠️ public/articles_priority.json não copiado"
cp public/articles_secondary.json "$BACKUP_DIR/public_articles_secondary.json" 2>/dev/null || echo "⚠️ public/articles_secondary.json não copiado"

echo "📂 Ficheiros guardados em: $BACKUP_DIR"
ls -la "$BACKUP_DIR"

# Criar branch data órfã (sem histórico)
echo "🌿 Criando branch data órfã..."
git checkout --orphan data

# Remover tudo da staging area
git rm -rf . 2>/dev/null || true

# Criar estrutura de pastas
mkdir -p articles public

# Copiar ficheiros JSON de volta
echo "📋 Copiando ficheiros JSON para a branch data..."
cp "$BACKUP_DIR/articles.json" articles/ 2>/dev/null && echo "✅ articles/articles.json copiado"
cp "$BACKUP_DIR/articles_priority.json" articles/ 2>/dev/null && echo "✅ articles/articles_priority.json copiado"
cp "$BACKUP_DIR/articles_secondary.json" articles/ 2>/dev/null && echo "✅ articles/articles_secondary.json copiado"
cp "$BACKUP_DIR/original_categories.json" articles/ 2>/dev/null && echo "✅ articles/original_categories.json copiado"
cp "$BACKUP_DIR/public_articles.json" public/articles.json 2>/dev/null && echo "✅ public/articles.json copiado"
cp "$BACKUP_DIR/public_articles_priority.json" public/articles_priority.json 2>/dev/null && echo "✅ public/articles_priority.json copiado"
cp "$BACKUP_DIR/public_articles_secondary.json" public/articles_secondary.json 2>/dev/null && echo "✅ public/articles_secondary.json copiado"

# Criar um README simples para a branch data
echo "# Branch Data - Ficheiros JSON

Esta branch contém apenas os ficheiros JSON gerados automaticamente.
Não edite manualmente - é atualizada pelo GitHub Actions.

Última atualização: $(date)
" > README.md

# Mostrar estrutura final
echo "📁 Estrutura da branch data:"
find . -type f -name "*.json" -o -name "README.md" | head -10

# Adicionar tudo
git add .

# Fazer commit inicial
git commit -m "Inicial branch data com ficheiros JSON existentes"

# Fazer push
echo "🚀 Fazendo push da branch data..."
git push origin data

echo "✅ Branch data criada com sucesso!"
echo "🔄 Voltando para a branch main..."
git checkout main

echo "🧹 Limpando ficheiros temporários..."
rm -rf "$BACKUP_DIR"

echo "✅ Processo concluído!"
echo ""
echo "📝 Próximos passos:"
echo "1. Atualize o workflow do GitHub Actions"
echo "2. Configure o Vercel para usar a branch 'data'"
echo "3. Teste se a app Android continua a funcionar"