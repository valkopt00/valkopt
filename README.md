# Data Branch - Simplified JSON System
Automatically updated at: 2025-08-22 11:40:45

## 🎯 Simplified architecture:
Only **3 essential JSON files**, automatically compressed by Netlify (~65% reduction):

### 📱 For main app:
- **articles.json** - All categories and articles (single file)

### 🔍 For search functionality:
- **articles_search.json** - Normalized data for search

### 🗂️ For category mapping:
- **original_categories.json** - Original category mapping

## ⚡ Expected performance:
- **Initial loading**: ~944K (2-4 seconds)
- **All categories**: Available immediately after loading
- **Zero timing issues**: No dependencies between files
