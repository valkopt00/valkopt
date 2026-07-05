# Data Branch - Simplified JSON System
Automatically updated at: 2026-07-05 05:31:56

## 🎯 Simplified architecture:
Only **3 essential JSON files**, automatically compressed by Netlify (~65% reduction):

### 📱 For main app:
- **articles.json** - All categories and articles (single file)

### 🔍 For search functionality:
- **articles_search.json** - Normalized data for search

### 🗂️ For category mapping:
- **original_categories.json** - Original category mapping

## ⚡ Expected performance:
- **Initial loading**: ~1.8M (2-4 seconds)
- **All categories**: Available immediately after loading
- **Zero timing issues**: No dependencies between files
