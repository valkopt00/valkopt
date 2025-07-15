import json
import os

# List of categories to remove
fonts_to_remove = {
    "Euronews"
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

    # Count how many categories exist before removal
    total_before = len(data)

    # Remove unwanted categories
    for source in fonts_to_remove:
        if source in data:
            del data[source]

    # Count how many categories remain
    total_after = len(data)
    removed = total_before - total_after

    # Write the updated data back to the JSON file
    with open(file_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"[{os.path.basename(file_json)}] Removed {removed} categories; {total_after} remain.")