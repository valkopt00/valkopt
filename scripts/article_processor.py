import asyncio
import re
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup

from scripts import utils

async def extract_image_url(entry, session, mapped_category=None):
    jornal_economico_logo = (
        "https://leitor.jornaleconomico.pt/assets/uploads/artigos/JE_logo.png"
    )
    cmjornal_logo = (
        "https://imagens.publico.pt/imagens.aspx/260779?tp=UH&db=IMAGENS&type=JPG"
    )

    try:
        link = entry.get("link", "") or ""
        lc_link = link.lower()

        image_url = None

        # 1) media_content
        if hasattr(entry, "media_content"):
            for m in entry.media_content:
                url = m.get("url")
                if url:
                    image_url = utils.process_url(url)
                    break

        # 2) enclosures
        if not image_url and hasattr(entry, "enclosures"):
            for enc in entry.enclosures:
                if enc.get("url") and enc.get("type", "").startswith("image/"):
                    image_url = utils.process_url(enc["url"])
                    break

        # 3) fields image/img/post-thumbnail
        if not image_url:
            for tag in ("image", "img", "post-thumbnail"):
                val = entry.get(tag)
                if isinstance(val, dict) and val.get("url"):
                    image_url = utils.process_url(val["url"])
                    break
                elif isinstance(val, str) and val.strip().startswith("http"):
                    image_url = utils.process_url(val)
                    break

        # 4) content HTML
        if not image_url and hasattr(entry, "content"):
            for block in entry.content:
                html = block.get("value", "")
                m = re.search(r'<img[^>]+src="([^"]+)"', html)
                if m:
                    image_url = utils.process_url(m.group(1))
                    break

        # 5) description/summary HTML
        if not image_url:
            desc = entry.get("description") or entry.get("summary") or ""
            if desc:
                m = re.search(r'<img[^>]+src="([^"]+)"', desc)
                if m:
                    image_url = utils.process_url(m.group(1))
                else:
                    soup = BeautifulSoup(desc, "html.parser")
                    img = soup.find("img")
                    if img and img.get("src"):
                        image_url = utils.process_url(img.get("src"))

        # 6) webpage scraping
        if not image_url and link:
            scraped = await get_image_url_from_link(link, session)
            if scraped:
                image_url = utils.process_url(scraped)

        # 7) fallback to Jornal Económico
        if not image_url and "jornaleconomico.pt" in lc_link:
            image_url = jornal_economico_logo

        if not image_url and re.search(r"(www\.)?cmjornal\.pt/opiniao", lc_link):
            image_url = cmjornal_logo

        return image_url

    except Exception as e:
        print(f"Error extracting image URL: {e}")
        return None
    
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

async def process_article(article, session):
    """
    Processes a single article by checking if its content is exclusive and by extracting the image URL if missing.
    """
    link = article['link']
    is_exclusive = await article_processor.is_content_exclusive_from_url(link, session)
    article['isExclusive'] = is_exclusive
    if not article['image']:
        image_url = await get_image_url_from_link(link, session)
        article['image'] = image_url


async def process_articles(articles):
    """
    Processes a list of articles concurrently by checking for exclusive content and retrieving images if missing.
    """
    tasks = []
    async with aiohttp.ClientSession() as session:
        for article in articles:
            task = asyncio.create_task(article_processor.process_article(article, session))
            tasks.append(task)
        await asyncio.gather(*tasks)
