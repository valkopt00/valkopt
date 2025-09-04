import asyncio
from datetime import datetime, timedelta, timezone
import chardet
import traceback
from html import unescape
from urllib.parse import urlparse

import feedparser
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from dateutil import parser, tz

from scripts.core import utils
from scripts.mappers import category_mapper
from scripts.mappers.mappings import IGNORE_ORIGINAL_CATS
from scripts import article_processor 


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
        
        print(f"📄 Processing RSS feed: {feed_url}")
        
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
            else:
                # For other sources, detect encoding
                try:
                    content = content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    detected = chardet.detect(content_bytes)
                    encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'latin1'
                    try:
                        content = content_bytes.decode(encoding)
                    except UnicodeDecodeError:
                        content = content_bytes.decode('latin1', errors='replace')
            
            if not content.strip():
                print(f"⚠️ Empty content from {feed_url}")
                return []
                
            # Parse the feed content
            feed = feedparser.parse(content)
            
            # Better error handling for feedparser
            if hasattr(feed, 'bozo') and feed.bozo:
                print(f"⚠️ Feed parsing warning for {feed_url}: {feed.bozo_exception}")
            
            print(f"📄 Found {len(feed.entries)} entries in feed: {feed_url}")
            
            if "publico.pt" in feed_url or "PublicoRSS" in feed_url:
                print(f"📰 Found {len(feed.entries)} entries in Público feed")
            
            feed_domain = utils.get_feed_domain(feed_url)
            articles = []
            processed_count = 0
            skipped_count = 0
            
            # Process each entry in the feed
            for entry in feed.entries:
                try:
                    # Extract and clean title
                    title = utils.clean_title(entry.get('title', '').strip())
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
                    description = utils.clean_description(description.strip())
                    pub_date_str = (
                        entry.get('published', '') or
                        entry.get('pubDate', '') or
                        entry.get('updated', '')
                    )
                    source = utils.extract_source(feed)

                    link = entry.get('link', '').strip()
                    
                    # Special handling for Público links
                    if "publico.pt" in feed_url and not link.startswith('http'):
                        link = f"https://www.publico.pt{link}"
                    
                    # Extract image URL
                    image_url = await article_processor.extract_image_url(entry, session)
                    
                    # Determine SAPO feed and extract category
                    feed_category = ""
                    is_sapo_feed = "www.sapo.pt" in feed_domain
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
                    
                    # Capture original category
                    original_category = feed_category

                    # Map category using the fixed function
                    category = category_mapper.map_category(feed_category, feed_url, link, title, description)

                    # fallback if mapping failed or returned falsy
                    if not category:
                        category = "Outras Notícias"

                    pub_date = utils.parse_date(pub_date_str, source_url=feed_url)

                    if pub_date:
                        article_age = datetime.now(timezone.utc) - pub_date
                        if article_age <= timedelta(hours=12):  
                            article = {
                                "title": title,
                                "description": description,
                                "image": image_url,
                                "source": source,
                                "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),  # Use the corrected pub_date
                                "category": category,
                                "link": link,
                                "isExclusive": False,
                                "original_category": original_category
                            }

                            # Debug: Print category mapping for problematic cases
                            if category == "Outras Notícias" and original_category:
                                print(f"🔍 MAPPED TO 'Outras Notícias': '{original_category}' from {feed_url}")

                            # Add to articles based on category and date
                            articles.append(article)
                            processed_count += 1
                        else:
                            skipped_count += 1
                    else:
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

async def process_api_source(session, api_source, titles_seen, last_12_hours):
    """
    Process articles from an API source (non-RSS JSON endpoint).
    
    Args:
        session: aiohttp ClientSession
        api_source: Dictionary with API endpoint information
        titles_seen: Set of already seen article titles
        last_12_hours: Datetime threshold for "Últimas" category articles
        
    Returns:
        List of processed articles or False if error occurs
    """
    try:
        print(f"📄 Processing API source: {api_source['url']}")
        
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
                title = utils.clean_title(item.get("titulo") or item.get("title", "Sem título"))
                if title in titles_seen:
                    skipped_count += 1
                    continue
                titles_seen.add(title)
                description = utils.clean_description(item.get("descricao") or item.get("lead", ""))
                pub_date_str = item.get("data") or item.get("publish_date", "")
                link = item.get("url", "")
                source = utils.extract_source(link)
                image_url = item.get("multimediaPrincipal") or item.get("image", "")
                
                # Capture original category before mapping
                feed_category = item.get("rubrica") or item.get("tag", "Últimas")
                original_category = feed_category
                # Map category using the fixed function
                category = category_mapper.map_category(feed_category, api_source["url"], link, title, description)
                if not category:
                    category = "Últimas"

                pub_date = utils.parse_date(pub_date_str, source_url=api_source["url"])

                if pub_date:
                    article_age = datetime.now(timezone.utc) - pub_date
                    if article_age <= timedelta(hours=12):  
                        article = {
                            "title": title,
                            "description": description,
                            "image": image_url,
                            "source": source,
                            "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),  # Use corrected pub_date
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