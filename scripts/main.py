import asyncio
from datetime import datetime, timedelta, timezone

from scripts.article_merger import load_existing_articles, merge_articles
from scripts.article_processor import process_articles
from scripts.category_mapper import create_normalized_category_mappings
from scripts.data_exporter import export_to_json, export_search_json, export_original_categories_to_json
from scripts.feed_processor import process_rss_feed, process_api_source
from scripts.ai_classifier import categorize_with_ai, setup_ai_classifier
from scripts.mappings import RSS_FEEDS, API_SOURCES

# Initialize the normalized mapping once
NORMALIZED_SUBCATEGORY_TO_MAIN = create_normalized_category_mappings()

async def get_articles():
    """
    Main function to fetch articles from all sources and process them.
    Creates tasks for each feed and API source, then sorts and exports the results.
    """
    articles = []
    now = datetime.now(timezone.utc)
    last_12_hours = now - timedelta(hours=12)
    titles_seen = set()  # Set to track duplicate titles
    
    print(f"🚀 Starting article extraction at {now}")
    print(f"📅 Filtering articles from the last 12 hours: {last_12_hours}")
    print(f"📡 Processing {len(RSS_FEEDS)} RSS feeds and {len(API_SOURCES)} API sources")

    async with aiohttp.ClientSession() as session:
        # Create async tasks for RSS feeds and API sources
        rss_tasks = [process_rss_feed(session, feed_url, titles_seen, last_12_hours) 
                     for feed_url in RSS_FEEDS]
        api_tasks = [process_api_source(session, source, titles_seen, last_12_hours) 
                     for source in API_SOURCES]
        
        # Gather all results
        all_results = await asyncio.gather(*rss_tasks, *api_tasks, return_exceptions=True)
        
        # Process results with better error handling
        for i, result in enumerate(all_results):
            if isinstance(result, list):
                articles.extend(result)
                feed_url = RSS_FEEDS[i] if i < len(RSS_FEEDS) else "API_SOURCE"
                print(f"✅ {feed_url}: {len(result)} articles extracted")
            elif isinstance(result, Exception):
                feed_url = RSS_FEEDS[i] if i < len(RSS_FEEDS) else "API_SOURCE"
                print(f"❌ Error processing {feed_url}: {result}")
            else:
                feed_url = RSS_FEEDS[i] if i < len(RSS_FEEDS) else "API_SOURCE"
                print(f"⚠️ Unknown result type for {feed_url}: {type(result)}")

    print(f"📊 Total articles before sorting: {len(articles)}")
    
    # Debug: Print category distribution before sorting
    category_counts = {}
    for article in articles:
        cat = article.get("category", "Unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print("🔍 Category distribution of NEW articles:")
    for cat, count in sorted(category_counts.items()):
        print(f"   - {cat}: {count} articles")
    
    # Sort articles by publication date (newest first)
    articles.sort(key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"), reverse=True)
    
    # Process articles for additional metadata (exclusive content flags, images)
    await article_processor.process_articles(articles)
    
    # Export original categories before removing the field
    success = export_original_categories_to_json(articles)
    if not success:
        print("❌ Failed to export original categories")
    
    # Export processed articles to JSON
    export_to_json(articles)
    print(f"🎉 Article extraction completed! Total articles: {len(articles)}")
                                    
async def main():
    """
    Main asynchronous entry point to fetch and process articles.
    """
    # Initialize AI classifier
    ai_available = setup_ai_classifier()
    if ai_available:
        print("✅ AI classification ready")
    else:
        print("⚠️ AI classification not available - will use fallback categorization")
    
    await get_articles()

if __name__ == "__main__":
    # Run the main async function when the script is executed directly
    asyncio.run(main())
