import json
from datetime import datetime, timedelta, timezone

def load_existing_articles():
    """
    Load existing articles from JSON file or return empty structure if file doesn't exist.
    
    Returns:
        Dictionary with categories as keys and article lists as values
    """
    try:
        with open("articles/articles.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"Últimas": [], "Nacional": [], "Mundo": [], "Desporto": [], 
                "Economia": [], "Cultura": [], "Ciência e Tech": [], "Lifestyle": [],
                "Sociedade": [], "Política": [], "Multimédia": [], "Opinião": [], 
                "Vídeojogos": [], "Outras Notícias": []}

def is_article_within_timeframe(article_date_str, category, current_date):
    """
    Check if an article is within the desired timeframe based on its category.
    
    Args:
        article_date_str: Article date string
        category: Article category
        current_date: Current datetime for comparison
        
    Returns:
        Boolean indicating if article should be kept
    """
    try:
        article_date = datetime.strptime(article_date_str, "%d-%m-%Y %H:%M")
        article_date = article_date.replace(tzinfo=timezone.utc)
        
        if category == "Últimas":
            return current_date - article_date <= timedelta(hours=12)
        else:
            return current_date - article_date <= timedelta(days=5)  
    except Exception as e:
        print(f"⚠️ Error parsing article date {article_date_str}: {e}")
        return False

def merge_articles(existing_articles, new_articles, current_date):
    """
    Merge new articles with existing ones, ensuring articles appear both
    in their category AND in "Últimas" if within 12 hours.
    Uses link as unique identifier to avoid true duplicates.
    """
    merged = {}
    seen_links_per_category = {}  # Track links per category to avoid duplicates
    
    # Initialize all categories
    all_categories = ["Últimas", "Nacional", "Mundo", "Desporto", "Economia", 
                     "Cultura", "Ciência e Tech", "Lifestyle", "Sociedade", 
                     "Política", "Multimédia", "Opinião", "Vídeojogos", "Outras Notícias"]
    
    for cat in all_categories:
        merged[cat] = []
        seen_links_per_category[cat] = set()
    
    # Combine existing and new articles
    all_articles = []
    
    # Add existing articles
    for category, articles in existing_articles.items():
        for article in articles:
            if isinstance(article, dict):
                all_articles.append(article)
    
    # Add new articles
    all_articles.extend(new_articles)
    
    print(f"Merging {len(all_articles)} total articles")
    print(f"New articles: {len(new_articles)}")
    
    processed_count = 0
    skipped_duplicates = 0
    skipped_expired = 0
    skipped_invalid = 0
    ultimas_count = 0
    
    for article in all_articles:
        title = article.get("title")
        category = article.get("category")
        pub_date = article.get("pubDate")
        link = article.get("link", "").strip()
        
        # Skip invalid articles
        if not all([title, category, pub_date, link]):
            skipped_invalid += 1
            continue
        
        # Parse article date for time checks
        try:
            article_date = datetime.strptime(pub_date, "%d-%m-%Y %H:%M")
            article_date = article_date.replace(tzinfo=timezone.utc)
        except:
            skipped_invalid += 1
            continue
        
        # Check if article should be kept based on category-specific retention
        if not is_article_within_timeframe(pub_date, category, current_date):
            skipped_expired += 1
            continue
        
        # VALIDATE category - only allow predefined categories
        if category not in all_categories:
            category = "Outras Notícias"
            article["category"] = category
        
        # Check if this link already exists in this specific category
        if link in seen_links_per_category[category]:
            skipped_duplicates += 1
            continue
            
        # Add to the article's mapped category
        merged[category].append(article)
        seen_links_per_category[category].add(link)
        processed_count += 1
        
        # ALSO add to "Últimas" if within 12 hours AND not already there
        twelve_hours_ago = current_date - timedelta(hours=12)
        if article_date >= twelve_hours_ago and category != "Últimas":
            # Check if this link is already in Últimas
            if link not in seen_links_per_category["Últimas"]:
                # Create a copy for Últimas
                ultimas_article = article.copy()
                ultimas_article["category"] = "Últimas"
                merged["Últimas"].append(ultimas_article)
                seen_links_per_category["Últimas"].add(link)
                ultimas_count += 1
    
    # Sort all categories by date (newest first)
    for category in merged:
        merged[category].sort(
            key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"),
            reverse=True
        )
    
    # Print detailed summary
    print(f"Processing summary:")
    print(f"   - Total processed: {processed_count}")
    print(f"   - Added to Últimas: {ultimas_count}")
    print(f"   - Skipped duplicates: {skipped_duplicates}")
    print(f"   - Skipped expired: {skipped_expired}")
    print(f"   - Skipped invalid: {skipped_invalid}")
    print(f"Final categories:")
    
    for category, articles in merged.items():
        if articles:
            print(f"   - {category}: {len(articles)} articles")
    
    return merged