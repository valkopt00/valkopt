import json
import traceback

def export_original_categories_to_json(articles):
    """
    Exports the original categories of articles that have been mapped to 'Outras Notícias'
    to a JSON file (original_categories.json). Only new, unique original categories (based on the article's original_category)
    are added to the file. Also includes a count of how many times each category appears overall.
    Only increments the count for new articles that haven't been processed before.
    """
    if not articles:
        print("No articles provided to export_original_categories_to_json")
        return False

    try:
        print(f"Starting export of original categories mapped to 'Outras Notícias' with {len(articles)} articles...")

        filtered_articles = [article for article in articles if article.get("category", "").strip() == "Outras Notícias"]
        print(f"Found {len(filtered_articles)} articles with category 'Outras Notícias'")

        existing_entries = []
        processed_urls = set()
        try:
            with open("articles/original_categories.json", "r", encoding="utf-8") as f:
                existing_entries = json.load(f)
                print(f"Loaded {len(existing_entries)} existing entries from file")
                for entry in existing_entries:
                    if "url" in entry:
                        processed_urls.add(entry["url"])
                print(f"Loaded {len(processed_urls)} processed URLs from existing entries")
        except (FileNotFoundError, json.JSONDecodeError):
            print("No existing file found or file is empty. Creating new file.")

        existing_categories = {entry["category"] for entry in existing_entries}
        category_counts = {}
        for entry in existing_entries:
            category = entry.get("category")
            if "count" in entry:
                category_counts[category] = entry.get("count")
            else:
                category_counts[category] = 1

        new_entries = []
        new_article_counts = {}
        for article in filtered_articles:
            try:
                article_link = article.get("link", "").strip()
                if "eurogamer.pt" in article_link or "ign.com" in article_link:
                    continue
                if article_link in processed_urls:
                    continue

                source = article.get("source", "").strip()
                mapped_cat = "Outras Notícias"
                orig_cat = article.get("original_category", "").strip()

                if orig_cat:
                    new_article_counts[orig_cat] = new_article_counts.get(orig_cat, 0) + 1
                    processed_urls.add(article_link)

                    if orig_cat not in existing_categories:
                        new_entries.append({
                            "category": orig_cat,
                            "source": source,
                            "mapped_category": mapped_cat,
                            "url": article_link,
                            "count": 1
                        })
                        existing_categories.add(orig_cat)
            except Exception as e:
                print(f"Error processing article: {str(e)}")
                continue

        print(f"Found {len(new_entries)} new category entries to add")
        print(f"Found {sum(new_article_counts.values())} new articles to count")

        for entry in existing_entries:
            category = entry.get("category")
            if category in new_article_counts:
                entry["count"] = entry.get("count", 0) + new_article_counts[category]
                del new_article_counts[category]

        for category, count in new_article_counts.items():
            if category not in existing_categories:
                for article in filtered_articles:
                    if article.get("original_category", "").strip() == category:
                        new_entries.append({
                            "category": category,
                            "source": article.get("source", "").strip(),
                            "mapped_category": "Outras Notícias",
                            "url": article.get("link", "").strip(),
                            "count": count
                        })
                        break

        combined_entries = existing_entries + new_entries
        combined_entries.sort(key=lambda x: (-x.get("count", 0), x["category"], x["source"]))

        try:
            with open("articles/original_categories.json", "w", encoding="utf-8") as f:
                json.dump(combined_entries, f, ensure_ascii=False, indent=4)
            print(f"Original categories file saved successfully with {len(combined_entries)} entries.")
            return True
        except Exception as e:
            print(f"Error saving original categories file: {str(e)}")
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"CRITICAL ERROR in original category export: {str(e)}")
        traceback.print_exc()
        return False