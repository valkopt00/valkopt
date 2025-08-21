import json
import os

# JSON file to process
json_file = "articles/articles.json"

# Check if file exists
if not os.path.exists(json_file):
    print(f"File {json_file} does not exist. Skipping duplicate removal.")
    exit(0)

# Load data from the JSON file
with open(json_file, "r", encoding="utf-8") as f:
    try:
        data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"The JSON file {json_file} does not have the expected format.")
    except json.JSONDecodeError as e:
        print(f"Error loading JSON from {json_file}: {e}")
        exit(1)

total_removed = 0
total_before = 0
total_after = 0

# Iterate over each category in the JSON
for category, articles in list(data.items()):
    if isinstance(articles, list):
        before_count = len(articles)
        total_before += before_count
        
        # Use link as unique identifier to remove duplicates
        seen_links = set()
        unique_articles = []
        
        for article in articles:
            link = article.get("link", "").strip()
            if link and link not in seen_links:
                seen_links.add(link)
                unique_articles.append(article)
        
        after_count = len(unique_articles)
        removed = before_count - after_count
        
        if removed > 0:
            data[category] = unique_articles
            total_removed += removed
            print(f"Category '{category}': removed {removed} duplicates ({before_count} -> {after_count})")
        
        total_after += after_count

# Write the updated data back to the JSON file
with open(json_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"Total duplicates removed: {total_removed}")
if total_removed > 0:
    print(f"File updated: {json_file}")