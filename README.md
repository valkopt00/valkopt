# Data Branch - Simplified JSON System
Automatically updated at: 2025-08-30 17:29:17

## 🎯 Simplified architecture:
Only **3 essential JSON files**, automatically compressed by Netlify (~65% reduction):

### 📱 For main app:
- **articles.json** - All categories and articles (single file)

### 🔍 For search functionality:
- **articles_search.json** - Normalized data for search

### 🗂️ For category mapping:
- **original_categories.json** - Original category mapping

## ⚡ Expected performance:
- **Initial loading**: ~2.0M (2-4 seconds)
- **All categories**: Available immediately after loading
- **Zero timing issues**: No dependencies between files
