import json
import os
from datetime import datetime, timezone, timedelta

from scripts import utils

def export_to_json(articles):
    """
    Export processed articles to JSON, merging with existing articles.
    Creates articles.json file.
    Removes original_category field before saving.
    """
    os.makedirs("articles", exist_ok=True)

    current_date = datetime.now(timezone.utc)
    existing_articles = load_existing_articles()
    merged_articles = merge_articles(existing_articles, articles, current_date)
    
    # Remove original_category field from all articles
    for cat, articles_list in merged_articles.items():
        for article in articles_list:
            article.pop("original_category", None)
    
    # Export complete file
    with open("articles/articles.json", "w", encoding="utf-8") as f:
        json.dump(merged_articles, f, ensure_ascii=False, indent=4)
    
    # Export search version
    export_search_json(merged_articles)
    
    print(f"✅ Exported complete file to articles.json")
    print(f"✅ Total categories: {len(merged_articles)}")
    total_articles = sum(len(articles_list) for articles_list in merged_articles.values())
    print(f"✅ Total articles: {total_articles}")

def export_search_json(merged_articles):
    """
    Exports normalized version of articles for search.
    
    Args:
        merged_articles: Dictionary with processed articles
    """
    try:
        # Create version for search
        search_articles = create_search_articles(merged_articles)
        
        # Export articles_search.json
        with open("articles/articles_search.json", "w", encoding="utf-8") as f:
            json.dump(search_articles, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Exported articles_search.json with {len(search_articles)} categories")
        
    except Exception as e:
        print(f"❌ Error exporting articles_search.json: {e}")

def create_search_articles(articles_dict):
    """
    Creates a simplified version of the articles only for search.  
    Contains only the normalized fields and the mapping link.
    
    Args:
        articles_dict: Dictionary with categories and articles
        
    Returns:
        Dictionary with simplified articles for search
    """
    search_articles = {}
    total_processed = 0
    
    print("🔍 Creating simplified version for search...")
    
    for category, articles_list in articles_dict.items():
        if not articles_list:
            continue
            
        search_articles[category] = []
        
        for article in articles_list:
            try:
                title = article.get('title', '')
                description = article.get('description', '')
                link = article.get('link', '')
                
                # Only the necessary fields for search
                search_article = {
                    "link": link,  # For mapping with articles.json
                    "normalized_title": utils.normalize_text(title),
                    "normalized_description": utils.normalize_text(description)
                }
                
                search_articles[category].append(search_article)
                total_processed += 1
                
            except Exception as e:
                print(f"❌ Error processing article for search: {e}")
                continue
    
    print(f"✅ {total_processed} simplified articles for search")
    return search_articles

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

        # Filter only articles with the category "Outras Notícias"
        filtered_articles = [article for article in articles if article.get("category", "").strip() == "Outras Notícias"]
        print(f"Found {len(filtered_articles)} articles with category 'Outras Notícias'")

        # Load the existing entries from the file if available
        existing_entries = []
        processed_urls = set()  # Set to track URLs that have already been processed
        
        try:
            with open("articles/original_categories.json", "r", encoding="utf-8") as f:
                existing_entries = json.load(f)
                print(f"Loaded {len(existing_entries)} existing entries from file")
                
                # Extract URLs from existing entries to avoid double counting
                for entry in existing_entries:
                    if "url" in entry:
                        processed_urls.add(entry["url"])
                
                print(f"Loaded {len(processed_urls)} processed URLs from existing entries")
        except (FileNotFoundError, json.JSONDecodeError):
            print("No existing file found or file is empty. Creating new file.")

        # Create a set of unique original categories from the existing entries
        existing_categories = {entry["category"] for entry in existing_entries}
        
        # Create a dictionary to track category occurrence counts
        # Initialize with counts from existing entries
        category_counts = {}
        for entry in existing_entries:
            category = entry.get("category")
            # If the entry already has a count field, use it as starting point
            if "count" in entry:
                category_counts[category] = entry.get("count")
            else:
                # Otherwise start with count of 1 for existing entries
                category_counts[category] = 1

        # Process new articles to collect new category entries and update counts
        new_entries = []
        new_article_counts = {}  # Track new articles by category for count increments
        
        for article in filtered_articles:
            try:
                article_link = article.get("link", "").strip()
                
                # Skip articles from Eurogamer and IGN feeds
                if "eurogamer.pt" in article_link or "ign.com" in article_link:
                    continue
                    
                # Skip already processed URLs
                if article_link in processed_urls:
                    continue
                
                source = article.get("source", "").strip()
                mapped_cat = "Outras Notícias"  # We already know it maps to "Outras Notícias"
                orig_cat = article.get("original_category", "").strip()

                # Check mapping for ignored categories
                if orig_cat in IGNORE_ORIGINAL_CATS:
                    continue

                # Only count this as a new occurrence if we haven't seen this URL before
                if orig_cat:
                    # Increment the count for this category only for new articles
                    new_article_counts[orig_cat] = new_article_counts.get(orig_cat, 0) + 1
                    
                    # Add URL to processed set to avoid double counting
                    processed_urls.add(article_link)
                    
                    # If the original category is not already recorded, add it as a new entry
                    if orig_cat not in existing_categories:
                        new_entries.append({
                            "category": orig_cat,
                            "source": source,
                            "mapped_category": mapped_cat,
                            "url": article_link,
                            "count": 1  # Start with count 1 for new categories
                        })
                        # Add to the set to prevent duplicates in the current batch
                        existing_categories.add(orig_cat)
            except Exception as e:
                print(f"Error processing article: {str(e)}")
                continue

        print(f"Found {len(new_entries)} new category entries to add")
        print(f"Found {sum(new_article_counts.values())} new articles to count")

        # Update counts for existing entries based on new articles
        for entry in existing_entries:
            category = entry.get("category")
            if category in new_article_counts:
                # Add the count of new articles with this category
                entry["count"] = entry.get("count", 0) + new_article_counts[category]
                # Remove this category from new_article_counts as we've handled it
                del new_article_counts[category]

        # For any remaining categories in new_article_counts that weren't in existing entries
        # but also weren't new enough to create an entry (this shouldn't happen given our logic,
        # but included for completeness)
        for category, count in new_article_counts.items():
            if category not in existing_categories:
                # Find any article with this category to create a new entry
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

        # Combine the existing entries with the new entries
        combined_entries = existing_entries + new_entries

        # Sort the combined entries by count (descending) and then by category and source
        combined_entries.sort(key=lambda x: (-x.get("count", 0), x["category"], x["source"]))

        try:
            # Save the combined entries back to the JSON file
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
