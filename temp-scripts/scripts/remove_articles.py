import json
import os

# List of sources to remove
fonts_to_remove = {
    "Sapo"
    }

# List of JSON files to process
json_files = [
    "articles/articles.json",
    "articles/articles_priority.json",
    "articles/articles_secondary.json"
]

for file_json in json_files:
    # Load data from the JSON file
    with open(file_json, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError(f"The JSON file {file_json} does not have the expected top‑level object format.")
        except json.JSONDecodeError as e:
            print(f"Error loading JSON from {file_json}: {e}")
            continue

    total_removed = 0

    # Iterate over each category in the JSON
    for category, articles in list(data.items()):
        # Only process if this entry is a list of articles
        if isinstance(articles, list):
            before_count = len(articles)
            # Filter out articles whose 'source' is in fonts_to_remove
            filtered = [
                article for article in articles
                if article.get("source") not in fonts_to_remove
            ]
            removed = before_count - len(filtered)
            if removed:
                data[category] = filtered
                total_removed += removed

    # Write the updated data back to the JSON file
    with open(file_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"[{os.path.basename(file_json)}] Removed {total_removed} articles in total.")