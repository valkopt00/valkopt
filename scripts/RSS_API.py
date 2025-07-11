import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import json
import re
from html import unescape
from xml.etree.ElementTree import Element
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from scripts.mappings import CATEGORY_MAPPER, FEED_CATEGORY_MAPPER, API_SOURCES, RSS_FEEDS, DATE_FORMATS
import feedparser
import asyncio
import aiohttp
from aiohttp import ClientTimeout
import chardet
import traceback
import os
from dateutil import tz
from dateutil import parser


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
                print(f"⚠️  Unknown result type for {feed_url}: {type(result)}")

    print(f"📊 Total articles before sorting: {len(articles)}")
    
    # Sort articles by publication date (newest first)
    articles.sort(key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"), reverse=True)
    
    # Process articles for additional metadata (exclusive content flags, images)
    await process_articles(articles)
    
    # Export original categories before removing the field
    success = export_original_categories_to_json(articles)
    if not success:
        print("❌ Failed to export original categories")
    
    # Export processed articles to JSON
    export_to_json(articles)
    print(f"🎉 Article extraction completed! Total articles: {len(articles)}")
                                
def export_to_json(articles):
    """
    Export processed articles to JSON, merging with existing articles.
    Creates two separate files: priority and secondary categories.
    Removes original_category field before saving.
    """
    os.makedirs("articles", exist_ok=True)

    current_date = datetime.now(timezone.utc)
    existing_articles = load_existing_articles()
    merged_articles = merge_articles(existing_articles, articles, current_date)
    
    # Define priority categories (lowercase for comparison)
    priority_categories = ["Últimas", "Nacional", "Mundo"]
    
    # Create priority and secondary dictionaries
    priority_articles = {}
    secondary_articles = {}
    
    # Remove original_category field and split articles
    for cat, articles_list in merged_articles.items():
        # Clean articles
        for article in articles_list:
            article.pop("original_category", None)
        
        # Split by priority
        if cat in priority_categories:
            priority_articles[cat] = articles_list
        else:
            secondary_articles[cat] = articles_list
    
    # Export priority articles (main file for app startup)
    with open("articles/articles_priority.json", "w", encoding="utf-8") as f:
        json.dump(priority_articles, f, ensure_ascii=False, indent=4)
    
    # Export secondary articles (loaded on demand)
    with open("articles/articles_secondary.json", "w", encoding="utf-8") as f:
        json.dump(secondary_articles, f, ensure_ascii=False, indent=4)
    
    # Keep the original full file for compatibility (optional)
    with open("articles/articles.json", "w", encoding="utf-8") as f:
        json.dump(merged_articles, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Exported {len(priority_articles)} priority categories to articles_priority.json")
    print(f"✅ Exported {len(secondary_articles)} secondary categories to articles_secondary.json")
    print(f"✅ Exported complete file to articles.json")

async def process_rss_feed(session, feed_url, titles_seen, last_12_hours):
    """
    Process a single RSS feed to extract articles.
    
    Args:
        session: aiohttp ClientSession for making requests
        feed_url: URL of the RSS feed
        titles_seen: Set of already seen article titles (to avoid duplicates)
        last_12_hours: Datetime threshold for "Últimas" category articles
        
    Returns:
        List of processed articles
    """
    try:
        timeout = ClientTimeout(total=45)  # Increased timeout
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        
        print(f"🔄 Processing RSS feed: {feed_url}")
        
        async with session.get(feed_url, headers=headers, timeout=timeout) as response:
            if response.status != 200:
                print(f"❌ Error fetching {feed_url}: Status {response.status}")
                return []
                
            # Handle encoding for specific sources (Público requires special handling)
            content_bytes = await response.read()
            if "publico.pt" in feed_url or "PublicoRSS" in feed_url:
                try:
                    content = content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        content = content_bytes.decode('cp1252')
                    except UnicodeDecodeError:
                        content = content_bytes.decode('latin1')
                print(f"📰 Processing Público feed from {feed_url}")
            else:
                # For other sources, detect encoding
                detected = chardet.detect(content_bytes)
                encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
                try:
                    content = content_bytes.decode(encoding)
                except UnicodeDecodeError:
                    content = content_bytes.decode('latin1')
            
            if not content.strip():
                print(f"⚠️  Empty content from {feed_url}")
                return []
                
            # Parse the feed content
            feed = feedparser.parse(content)
            
            # Better error handling for feedparser
            if hasattr(feed, 'bozo') and feed.bozo:
                print(f"⚠️  Feed parsing warning for {feed_url}: {feed.bozo_exception}")
            
            print(f"📄 Found {len(feed.entries)} entries in feed: {feed_url}")
            
            if "publico.pt" in feed_url or "PublicoRSS" in feed_url:
                print(f"📰 Found {len(feed.entries)} entries in Público feed")
            
            feed_domain = get_feed_domain(feed_url)
            articles = []
            processed_count = 0
            skipped_count = 0
            
            # Process each entry in the feed
            for entry in feed.entries:
                try:
                    # Extract and clean title
                    title = clean_title(entry.get('title', '').strip())
                    if not title:
                        skipped_count += 1
                        continue
                    
                    # Check for duplicates - but make it less strict
                    title_lower = title.lower()
                    if any(title_lower in seen_title.lower() or seen_title.lower() in title_lower 
                           for seen_title in titles_seen):
                        skipped_count += 1
                        continue
                    
                    titles_seen.add(title)
                    
                    # Extract other article metadata
                    description = entry.get('summary', '') or entry.get('description', '')
                    description = clean_description(description.strip())
                    pub_date_str = (
                        entry.get('published', '') or
                        entry.get('pubDate', '') or
                        entry.get('updated', '')
                    )
                    source = extract_source(feed)
                    link = entry.get('link', '').strip()
                    
                    # Special handling for Público links
                    if "publico.pt" in feed_url and not link.startswith('http'):
                        link = f"https://www.publico.pt{link}"
                    
                    # Extract image URL
                    image_url = await extract_image_url(entry, session)
                    
                    # Determine SAPO feed and extract category
                    feed_category = ""
                    is_sapo_feed = "sapo.pt" in feed_domain
                    if is_sapo_feed:
                        # feedparser puts first <category> in entry.category and the rest in entry.tags
                        tags = getattr(entry, 'tags', None)
                        if isinstance(tags, list) and tags:
                            last_tag = tags[-1]
                            if isinstance(last_tag, dict):
                                feed_category = last_tag.get('term', '').strip()
                            elif hasattr(last_tag, 'term'):
                                feed_category = last_tag.term.strip()
                            else:
                                feed_category = entry.get('category', '').strip()
                        else:
                            cat = entry.get('category', '')
                            if isinstance(cat, list):
                                feed_category = cat[-1] if cat else ''
                            else:
                                feed_category = cat.strip()
                    else:
                        feed_category = entry.get('category', '')
                        if isinstance(feed_category, list):
                            feed_category = feed_category[0] if feed_category else ''
                    
                    original_category = feed_category
                    category = map_category(feed_category, feed_domain, link)
                    pub_date = parse_date(pub_date_str, source_url={feed_url})
                    
                    if pub_date:
                        # More lenient time filtering - keep articles from last 24 hours instead of 12
                        article_age = datetime.now(timezone.utc) - pub_date
                        if article_age <= timedelta(hours=24):  # Increased from 12 to 24 hours
                            article = {
                                "title": title,
                                "description": description,
                                "image": image_url,
                                "source": source,
                                "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),
                                "category": category,
                                "link": link,
                                "isExclusive": False,
                                "original_category": original_category
                            }
                            
                            # Add to articles based on category and date
                            articles.append(article)
                            processed_count += 1
                        else:
                            # Debug: show why articles are being skipped
                            print(f"⏰ Skipping old article from {source}: {title[:50]}... (Age: {article_age})")
                            skipped_count += 1
                    else:
                        print(f"📅 Failed to parse date for article: {title[:50]}... Date string: {pub_date_str}")
                        skipped_count += 1
                
                except Exception as e:
                    print(f"❌ Error processing entry from {feed_url}: {str(e)}")
                    skipped_count += 1
                    continue
            
            print(f"📊 {feed_url}: {processed_count} processed, {skipped_count} skipped")
            
            if "publico.pt" in feed_url or "PublicoRSS" in feed_url:
                print(f"📰 Total articles processed from Público: {len(articles)}")
            
            return articles
                        
    except Exception as e:
        print(f"❌ Error processing {feed_url}: {str(e)}")
        traceback.print_exc()
        return []
    

def parse_date(date_str, source_url=None):
    """
    Parse publication date from various formats.
    
    Args:
        date_str: Date string to parse
        source_url: URL of the RSS feed (for RTP correction)
        
    Returns:
        Datetime object with original timezone or None if parsing fails
    """
    if not date_str:
        return None
        
    date_str = date_str.strip()
    
    # Handle common Portuguese timezone abbreviations
    date_str = date_str.replace(' WET', ' +0000')  # Western European Time
    date_str = date_str.replace(' WEST', ' +0100')  # Western European Summer Time
    
    # Remove non-ASCII characters that might cause issues
    date_str = date_str.encode('ascii', 'ignore').decode('ascii')
    
    # Handle special GMT timezone cases
    if "GMT+" in date_str:
        date_str = re.sub(r'GMT\+(\d+)', lambda m: f"+{m.group(1).zfill(2)}00", date_str)
    elif "GMT-" in date_str:
        date_str = re.sub(r'GMT-(\d+)', lambda m: f"-{m.group(1).zfill(2)}00", date_str)
    
    # Extended date formats - include more common formats
    extended_formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S %Z",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S",
        "%d %b %Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    
    # Combine with existing formats (assuming DATE_FORMATS exists)
    try:
        all_formats = DATE_FORMATS + extended_formats
    except NameError:
        all_formats = extended_formats
    
    # Try each format until one works
    for fmt in all_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            
            # Só adicionar timezone português se a data não tiver timezone
            if dt.tzinfo is None:
                from dateutil import tz
                portugal_tz = tz.gettz('Europe/Lisbon')
                dt = dt.replace(tzinfo=portugal_tz)
            
            # CORREÇÃO: Aplicar correção específica RTP para feeds rtp.pt
            # independentemente de ter timezone ou não
            print(f"🔍 Debug - source_url: '{source_url}'")
            print(f"🔍 Debug - source_url type: {type(source_url)}")
            
            # Converter set para string se necessário
            if isinstance(source_url, set):
                source_url = next(iter(source_url)) if source_url else None
                print(f"🔍 Debug - source_url converted from set: '{source_url}'")
            
            if source_url and ('rtp.pt' in source_url.lower()):
                from datetime import timedelta
                print(f"⚠️  BEFORE RTP correction: {dt}")
                dt = dt - timedelta(hours=1)
                print(f"⚠️  AFTER RTP correction: {dt} (applied -1 hour)")
            else:
                print(f"⚠️  RTP correction NOT applied - source_url: '{source_url}'")
            
            # Display da data para debug (sem alterar a data original)
            formatted_for_json = dt.strftime("%d-%m-%Y %H:%M")
            timezone_info = f"({dt.tzinfo})" if dt.tzinfo else "(no timezone)"
            print(f"📅 Date parsed: {date_str} -> {formatted_for_json} {timezone_info}")
            
            return dt  # Return with original/correct timezone
            
        except ValueError:
            continue
    
    # If all formats fail, try a more flexible approach
    try:
        from dateutil import parser
        dt = parser.parse(date_str)
        
        # Só adicionar timezone português se a data não tiver timezone
        if dt.tzinfo is None:
            from dateutil import tz
            portugal_tz = tz.gettz('Europe/Lisbon')
            dt = dt.replace(tzinfo=portugal_tz)
        
        # CORREÇÃO: Aplicar correção específica RTP para feeds rtp.pt
        # independentemente de ter timezone ou não
        print(f"🔍 Debug - source_url: '{source_url}'")
        print(f"🔍 Debug - source_url type: {type(source_url)}")
        
        # Converter set para string se necessário
        if isinstance(source_url, set):
            source_url = next(iter(source_url)) if source_url else None
            print(f"🔍 Debug - source_url converted from set: '{source_url}'")
        
        if source_url and ('rtp.pt' in source_url.lower()):
            from datetime import timedelta
            print(f"⚠️  BEFORE RTP correction: {dt}")
            dt = dt - timedelta(hours=1)
            print(f"⚠️  AFTER RTP correction: {dt} (applied -1 hour)")
        else:
            print(f"⚠️  RTP correction NOT applied - source_url: '{source_url}'")
        
        # Display da data para debug (sem alterar a data original)
        formatted_for_json = dt.strftime("%d-%m-%Y %H:%M")
        timezone_info = f"({dt.tzinfo})" if dt.tzinfo else "(no timezone)"
        print(f"📅 Date parsed: {date_str} -> {formatted_for_json} {timezone_info}")
        
        return dt  # Return with original/correct timezone
        
    except:
        pass
            
    print(f"⚠️  Failed to parse date: {date_str}")
    
    return None

async def process_api_source(session, api_source, titles_seen, last_12_hours):
    """
    Process articles from an API source (non-RSS JSON endpoint).
    
    Args:
        session: aiohttp ClientSession
        api_source: Dictionary with API endpoint information
        titles_seen: Set of already seen article titles
        last_12_hours: Datetime threshold for "Últimas" category
        
    Returns:
        List of processed articles or False if error occurs
    """
    try:
        print(f"🔄 Processing API source: {api_source['url']}")
        
        timeout = ClientTimeout(total=45)  # Increased timeout
        async with session.get(api_source["url"], headers=api_source["headers"], timeout=timeout) as response:
            if response.status != 200:
                print(f"❌ API source error {api_source['url']}: Status {response.status}")
                return []
            data = await response.json()
            articles = []
            articles_list = data if isinstance(data, list) else data.get("articles", [])
            
            print(f"📄 Found {len(articles_list)} articles from API source")
            
            processed_count = 0
            skipped_count = 0
            
            for item in articles_list:
                title = clean_title(item.get("titulo") or item.get("title", "Sem título"))
                if title in titles_seen:
                    skipped_count += 1
                    continue
                titles_seen.add(title)
                description = clean_description(item.get("descricao") or item.get("lead", ""))
                pub_date_str = item.get("data") or item.get("publish_date", "")
                link = item.get("url", "")
                source = extract_source(link)
                image_url = item.get("multimediaPrincipal") or item.get("image", "")
                
                # Capture original category before mapping
                feed_category = item.get("rubrica") or item.get("tag", "Últimas")
                original_category = feed_category
                
                category = map_category(feed_category, source, link)
                if not category:
                    category = "Últimas"

                pub_date = parse_date(pub_date_str, source_url=api_source["url"])

                if pub_date:
                    # More lenient time filtering
                    article_age = datetime.now(timezone.utc) - pub_date
                    if article_age <= timedelta(hours=24):  # Increased from 12 to 24 hours
                        article = {
                            "title": title,
                            "description": description,
                            "image": image_url,
                            "source": source,
                            "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),
                            "category": category,
                            "link": link,
                            "isExclusive": False,
                            "original_category": original_category
                        }
                        
                        articles.append(article)
                        processed_count += 1
                    else:
                        skipped_count += 1
                else:
                    skipped_count += 1
                    
            print(f"📊 API source: {processed_count} processed, {skipped_count} skipped")
            return articles
    except Exception as e:
        print(f"❌ Error processing API source {api_source['url']}: {str(e)}")
        traceback.print_exc()
        return []

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
        
        # More generous retention periods
        if category == "Últimas":
            return current_date - article_date <= timedelta(hours=12)
        else:
            return current_date - article_date <= timedelta(days=5)  
    except Exception as e:
        print(f"⚠️  Error parsing article date {article_date_str}: {e}")
        return False

def merge_articles(existing_articles, new_articles, current_date):
    """
    Merge new articles with existing ones, removing duplicates and expired articles.
    
    Args:
        existing_articles: Dictionary of existing articles by category
        new_articles: List of new articles to merge
        current_date: Current datetime for timeframe filtering
        
    Returns:
        Dictionary of merged articles by category
    """
    merged = {}
    seen_titles = set()
    
    # Combine existing and new articles
    all_articles = []
    
    # Add existing articles
    for category, articles in existing_articles.items():
        for article in articles:
            if isinstance(article, dict):
                all_articles.append(article)
    
    # Add new articles
    all_articles.extend(new_articles)
    
    print(f"📊 Merging {len(all_articles)} total articles (existing + new)")
    print(f"📊 New articles to process: {len(new_articles)}")
    
    # Process all articles
    processed_count = 0
    skipped_duplicates = 0
    skipped_expired = 0
    skipped_invalid = 0
    
    for article in all_articles:
        title = article.get("title")
        category = article.get("category")
        pub_date = article.get("pubDate")
        
        # Skip invalid articles
        if not all([title, category, pub_date]):
            skipped_invalid += 1
            print(f"⚠️  Skipped invalid article: title={title}, category={category}, pubDate={pub_date}")
            continue
        
        # Initialize category if it doesn't exist
        if category not in merged:
            merged[category] = []
        
        # Skip duplicates - use exact title match (case insensitive)
        title_lower = title.lower().strip()
        if title_lower in seen_titles:
            skipped_duplicates += 1
            continue
        
        # Skip expired articles
        if not is_article_within_timeframe(pub_date, category, current_date):
            skipped_expired += 1
            continue
        
        # Add the title to seen titles
        seen_titles.add(title_lower)
        
        # Add to appropriate category
        merged[category].append(article)
        processed_count += 1
        
        # Add recent articles to "Últimas" category as well
        if category != "Últimas" and is_article_within_timeframe(pub_date, "Últimas", current_date):
            if "Últimas" not in merged:
                merged["Últimas"] = []
            
            # Check if article is already in Últimas
            titles_in_ultimas = {art.get("title", "").lower().strip() for art in merged["Últimas"]}
            if title_lower not in titles_in_ultimas:
                merged["Últimas"].append(article)
    
    # Sort articles by date (newest first)
    for category in merged:
        merged[category].sort(
            key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"),
            reverse=True
        )
    
    # Print detailed summary
    print(f"📊 Processing summary:")
    print(f"   - Processed: {processed_count}")
    print(f"   - Skipped duplicates: {skipped_duplicates}")
    print(f"   - Skipped expired: {skipped_expired}")
    print(f"   - Skipped invalid: {skipped_invalid}")
    print(f"📂 Final categories:")
    
    for category, articles in merged.items():
        if articles:
            print(f"   - {category}: {len(articles)} articles")
    
    return merged

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
async def is_content_exclusive_from_url(link, session):
    """
    Checks if the content at the given URL is exclusive (e.g. behind a paywall or marked as premium).
    It uses several indicators based on the domain.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        async with session.get(link, headers=headers, timeout=10) as response:
            content = await response.text()
    except Exception as e:
        return False

    soup = BeautifulSoup(content, 'html.parser')

    # Define source-specific exclusive indicators
    source_checks = [
        {
            'domain': 'publico.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'kicker kicker--exclusive'},
                {'type': 'class', 'value': 'paywall-header'},
            ]
        },
        {
            'domain': 'expresso.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'g-premium-blocker'},
            ]
        },
        {
            'domain': 'observador.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'paywall-toptitle'},
            ]
        },
        {
            'domain': 'autosport.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'exclusive_alert'},
            ]
        },
        {
            'domain': 'visao.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'paywall-blocker'},
            ]
        },
        {
            'domain': 'jornaleconomico.sapo.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'bloco_bloqueio_premium'},
            ]
        },
        {
            'domain': 'cmjornal.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'widget_je_widget_premium_content'},
            ]
        },
        {
            'domain': 'jornaldenegocios.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'paywall'},
            ]
        },
    ]

    # Parse the URL to extract the domain
    parsed_url = urlparse(link)
    domain = parsed_url.netloc.replace('www.', '')

    # Check for exclusive indicators based on domain
    for source in source_checks:
        if source['domain'] in domain:
            for indicator in source['exclusive_indicators']:
                if indicator['type'] == 'class':
                    if soup.find(class_=indicator['value']):
                        return True
                elif indicator['type'] == 'text':
                    if indicator['value'].lower() in soup.get_text().lower():
                        return True

    # Additional check for exclusive phrases (currently empty)
    exclusive_phrases = []
    page_text = soup.get_text(separator=' ', strip=True).lower()
    if any(phrase in page_text for phrase in exclusive_phrases):
        return True

    return False


def fix_encoding(text):
    """
    Attempts to detect and fix encoding issues in the given text.
    """
    try:
        # First, try to fix potential double encoding issues
        text = text.encode('latin1').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        try:
            # If that fails, try decoding as utf-8
            text = text.encode('utf-8').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            # If all fails, return the original text
            pass
    return text


def clean_title(title):
    """
    Cleans the title string by removing CDATA markers, HTML tags, unescaping HTML entities,
    and fixing encoding issues.
    """
    if title.startswith("<![CDATA[") and title.endswith("]]>"):
        title = title[9:-3]
    title = re.sub(r"<.*?>", "", title)
    title = unescape(title)
    title = fix_encoding(title)  # Fix encoding issues
    return title.strip()


def clean_description(description):
    """
    Cleans the description string by unescaping HTML, removing HTML tags, quotes, and newlines.
    Also fixes encoding issues and truncates the description to 150 characters if necessary.
    """
    description = unescape(description)
    description = re.sub(r"<[^>]+>", "", description)
    description = description.replace('\"', "").replace("\n", " ")
    description = re.sub(r'\{(?:[^|}]+\|)*([^|}]+)\}', r'\1', description)
    description = fix_encoding(description)  # Fix encoding issues
    description = description.strip()
    if len(description) > 150:
        description = description[:150].rsplit(' ', 1)[0] + "..."
    return description


def extract_source(data):
    """
    Extracts the source name from a feed or URL.
    For feed objects, uses the feed title; for URLs, attempts to parse the domain.
    """
    try:
        if hasattr(data, 'feed') and hasattr(data.feed, 'title'):
            source_name = data.feed.title
            if "rtp" in source_name.lower():
                return "RTP Notícias"
            if "notícias ao minuto" in source_name.lower():
                return "Notícias ao Minuto"
            if "renascença" in source_name.lower():
                return "Renascença"
            if source_name.upper() == "PÚBLICO":
                return "Público"
            if source_name == "News | Euronews RSS":
                return "Euronews"
            if source_name == "Notícias zerozero.pt":
                return "zerozero.pt"
            if source_name == "Eurogamer.pt Latest Articles Feed":
                return "Eurogamer"
            # Normalize capitalization for other cases
            return source_name.title()
        elif isinstance(data, str):
            # Check for specific URLs
            if data.startswith("https://www.noticiasaominuto.com"):
                return "Notícias ao Minuto"
            elif data.startswith("https://www.rtp.pt/"):
                return "RTP Notícias"
            # Default processing for other URLs: extract domain and map if necessary
            parsed_url = urlparse(data)
            domain = parsed_url.netloc
            domain = re.sub(r'^www\.', '', domain)
            domain = domain.split('.')[0]
            source_mapping = {
                'observador': 'Observador',
                'publico': 'Público',
                'público': 'Público',
                'PÚBLICO': 'Público',
                'PUBLICO': 'Público',
            }
            return source_mapping.get(domain, domain)
    except Exception as e:
        print(f"Error extracting source: {e}")

    return "Desconhecido"


async def process_articles(articles):
    """
    Processes a list of articles concurrently by checking for exclusive content and retrieving images if missing.
    """
    tasks = []
    async with aiohttp.ClientSession() as session:
        for article in articles:
            task = asyncio.create_task(process_article(article, session))
            tasks.append(task)
        await asyncio.gather(*tasks)


async def process_article(article, session):
    """
    Processes a single article by checking if its content is exclusive and by extracting the image URL if missing.
    """
    link = article['link']
    is_exclusive = await is_content_exclusive_from_url(link, session)
    article['isExclusive'] = is_exclusive
    if not article['image']:
        image_url = await get_image_url_from_link(link, session)
        article['image'] = image_url


async def get_image_url_from_link(news_url, session):
    """
    Retrieves an image URL from a news article's webpage by searching for meta tags and image selectors.
    """
    timeout = ClientTimeout(total=10)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        async with session.get(news_url, headers=headers, timeout=timeout) as response:
            if response.status != 200:
                return None
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            # Define selectors to search for images
            selectors = [
                {'type': 'class', 'value': 'wp-post-image'},
                {'type': 'class', 'value': 'wp-block-cover__image-background'},
                {'type': 'property', 'value': 'og:image'},
                {'type': 'name', 'value': 'twitter:image'}
            ]
            for selector in selectors:
                if selector['type'] == 'property':
                    meta = soup.find('meta', property=selector['value'])
                    if meta and meta.get('content'):
                        return meta['content']
                elif selector['type'] == 'name':
                    meta = soup.find('meta', attrs={'name': selector['value']})
                    if meta and meta.get('content'):
                        return meta['content']
                else:
                    img = soup.find('img', class_=selector['value'])
                    if img:
                        return img.get('data-src') or img.get('src')
            return None
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        return None


def process_url(url: str) -> str:
    """
    Adjusts image URLs based on known patterns to obtain a higher resolution image.
    """
    if "100x100" in url:
        url = url.replace("100x100", "932x621")
    if "932x621" in url and "jornaldenegocios" in url:
        url = url.replace("932x621", "900x560")
    if "220x220" in url and "record.pt" in url:
        url = url.replace("220x220", "920x518")
    if url.startswith("https://cdn.record.pt/images/https://cdn.record.pt/images/"):
        url = url.replace("https://cdn.record.pt/images/", "", 1)
    return url

async def extract_image_url(entry, session, mapped_category=None):
    
    jornal_economico_logo = (
        "https://leitor.jornaleconomico.pt/assets/uploads/artigos/JE_logo.png"
    )
    cmjornal_opinion_img = (
        "https://imagens.publico.pt/imagens.aspx/260779?tp=UH&db=IMAGENS&type=JPG"
    )
    
    try:
        link = entry.get("link", "") or ""
        lc_link = link.lower()
        
        if "cmjornal.pt" in lc_link and mapped_category:
            normalized_category = mapped_category.strip().lower()
            if normalized_category == "opinião":
                print(f"DEBUG: CM Jornal + Opinião detectado. Link: {link}, Categoria: {mapped_category}")
                return cmjornal_opinion_img
        
        if hasattr(entry, "media_content"):
            for m in entry.media_content:
                url = m.get("url")
                if url:
                    return process_url(url)
        
        if hasattr(entry, "enclosures"):
            for enc in entry.enclosures:
                if enc.get("url") and enc.get("type", "").startswith("image/"):
                    return process_url(enc["url"])
        
        for tag in ("image", "img", "post-thumbnail"):
            val = entry.get(tag)
            if isinstance(val, dict) and val.get("url"):
                return process_url(val["url"])
            elif isinstance(val, str) and val.strip().startswith("http"):
                return process_url(val)
        
        if hasattr(entry, "content"):
            for block in entry.content:
                html = block.get("value", "")
                m = re.search(r'<img[^>]+src="([^"]+)"', html)
                if m:
                    return process_url(m.group(1))
        
        desc = entry.get("description") or entry.get("summary") or ""
        if desc:
            m = re.search(r'<img[^>]+src="([^"]+)"', desc)
            if m:
                return process_url(m.group(1))
            
            soup = BeautifulSoup(desc, "html.parser")
            img = soup.find("img")
            if img and img.get("src"):
                return process_url(img.get("src"))
        
        if link:
            scraped = await get_image_url_from_link(link, session)
            if scraped:
                return process_url(scraped)
        
        if "jornaleconomico.pt" in lc_link:
            return jornal_economico_logo
            
    except Exception as e:
        print(f"Error extracting image URL: {e}")
    
    return None

def get_feed_domain(feed_url):
    """
    Returns the feed URL as is (placeholder function for future domain processing if needed).
    """
    return feed_url


def map_category(feed_category, feed_url, item_link=None):
    """
    Maps the provided feed category and URL to a standardized category using predefined mappers.
    Includes special handling for certain sources (e.g., CM Jornal, Renascença, and Sapo.pt).
    """
    if isinstance(feed_url, dict):
        feed_url = feed_url.get("url", "")
    
    # First, check if the feed URL is in the FEED_CATEGORY_MAPPER
    for feed, category in FEED_CATEGORY_MAPPER.items():
        if feed_url.startswith(feed):
            return category
    
    # If not, process the feed_category using the CATEGORY_MAPPER
    if feed_category in CATEGORY_MAPPER:
        return CATEGORY_MAPPER[feed_category]
    
    # Special case handling for CM Jornal
    if "cmjornal.pt" in feed_url and item_link:
        parsed_url = urlparse(item_link)
        path_parts = parsed_url.path.strip("/").split("/")
        if path_parts:
            cm_category = path_parts[0].lower().capitalize()
            if cm_category in CATEGORY_MAPPER:
                return CATEGORY_MAPPER[cm_category]
            return "Outras Notícias"
    
    # Special case handling for Renascença
    if "rr.sapo.pt" in feed_url and item_link and "/noticia/" in item_link:
        try:
            parsed_url = urlparse(item_link)
            path_parts = parsed_url.path.strip("/").split("/")
            if "noticia" in path_parts:
                index = path_parts.index("noticia")
                if index + 1 < len(path_parts):
                    rr_category = path_parts[index + 1].lower().capitalize()
                    if rr_category in CATEGORY_MAPPER:
                        return CATEGORY_MAPPER[rr_category]
                    return rr_category
        except (ValueError, IndexError):
            pass
    
    return "Outras Notícias"
    
async def main():
    """
    Main asynchronous entry point to fetch and process articles.
    """
    await get_articles()


if __name__ == "__main__":
    # Run the main async function when the script is executed directly
    asyncio.run(main())
