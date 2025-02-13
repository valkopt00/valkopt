import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import json
import re
from html import unescape
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple
import logging
from aiohttp import ClientTimeout
from dataclasses import dataclass
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://www.record.pt/rss/",
    "https://www.autosport.pt/feed/",
    "https://www.zerozero.pt/rss/noticias.php",
    "https://visao.pt/feed/",
    "https://feeds.feedburner.com/publicoRSS",
    "https://jornaleconomico.sapo.pt/feed/",
    "https://www.cmjornal.pt/rss",
    "https://feeds.feedburner.com/expresso-geral",
    "https://www.jornaldenegocios.pt/rss",
    "https://www.rtp.pt/noticias/rss/",
    "https://rr.sapo.pt/rss/rssfeed.aspx?section=section_noticias",
    "https://rss.impresa.pt/feed/latest/expresso.rss?type=ARTICLE,VIDEO,STREAM,PLAYLIST,EVENT&limit=20&pubsubhub=true",
    "https://pt.euronews.com/rss?format=mrss&level=theme&name=news",
    "https://pplware.sapo.pt/feed/",
    "https://ionline.sapo.pt/feed/",
    "https://www.noticiasaominuto.com/rss/ultima-hora",
    "https://www.eurogamer.pt/feed",
    "https://pt.ign.com/feed.xml"
]

API_SOURCES = [
    {
        "url": "https://observador.pt/wp-json/obs_api/v4/news/widget",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "source_name": "NewsAPI"
    }
]

FEED_CATEGORY_MAPPER = {
    "https://www.record.pt/rss": "Desporto",
    "https://www.autosport.pt/feed": "Desporto",
    "https://www.zerozero.pt/rss/noticias.php": "Desporto",
    "https://www.noticiasaominuto.com/rss/desporto": "Desporto",
    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=2": "Desporto",
    "https://pt.euronews.com/sport": "Desporto",
    
    "https://jornaleconomico.sapo.pt/feed": "Economia",
    "https://www.jornaldenegocios.pt/rss": "Economia",
    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=86": "Economia",
    "https://www.rtp.pt/noticias/rss/economia": "Economia",
    "https://www.noticiasaominuto.com/rss/economia": "Economia",

    "https://noticiasaominuto.com/rss/politica": "Política",
    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=85": "Política",

    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=6": "Nacional",
    "https://www.rtp.pt/noticias/rss/pais": "Nacional",
    "https://www.noticiasaominuto.com/rss/pais": "Nacional",

    "https://noticiasaominuto.com/rss/mundo": "Mundo",
    "https://www.rtp.pt/noticias/rss/mundo": "Mundo",
    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=88": "Mundo",
    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=84": "Mundo",
    "https://pt.euronews.com/my-europe": "Mundo",
    "https://pt.euronews.com/rss?format=mrss&level=program&name=nocomment": "Mundo",

    "https://www.noticiasaominuto.com/rss/cultura": "Cultura",
    "https://www.rtp.pt/noticias/rss/cultura": "Cultura",
    "https://pt.euronews.com/culture": "Cultura",

    "https://www.noticiasaominuto.com/rss/tech": "Ciência e Tech",
    "https://pt.euronews.com/rss?format=mrss&level=vertical&name=next": "Ciência e Tech",
    "https://pplware.sapo.pt/feed/": "Ciência e Tech",
    "https://www.eurogamer.pt/feed": "Ciência e Tech",

    "https://www.noticiasaominuto.com/rss/fama": "Sociedade",
    "https://www.noticiasaominuto.com/rss/lifestyle": "Sociedade",
    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=89": "Sociedade",
    "https://pt.euronews.com/rss?format=mrss&level=vertical&name=green": "Sociedade",
    "https://pt.euronews.com/travel": "Sociedade",

    "https://www.rtp.pt/noticias/rss/videos": "Multimédia",
    "https://www.rtp.pt/noticias/rss/audios": "Multimédia",

    "https://caras.pt/feed/": "Lifestyle",

    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=71": "Opinião",

    "https://www.eurogamer.pt/feed": "Vídeojogos",
    "https://pt.ign.com/feed.xml": "Vídeojogos"
}

CATEGORY_MAPPER = {
    "Nacional": "Nacional",
    "País": "Nacional",
    "Pais": "Nacional",
    "Portugal": "Nacional",
    "Mundo": "Mundo",
    "Internacional": "Mundo",
    "União Europeia": "Mundo",
    "Guerra no médio oriente": "Mundo",
    "Médio Oriente": "Mundo",
    "Guerra israel-hamas": "Mundo",
    "Faixa de Gaza": "Mundo",
    "Alemanha": "Mundo",
    "Diplomacia": "Mundo",
    "EUA": "Mundo",
    "Desporto": "Desporto",
    "Futebol": "Desporto",
    "Benfica": "Desporto",
    "Sporting": "Desporto",
    "Porto": "Desporto",
    "Modalidades": "Desporto",
    "Mais modalidades": "Desporto",
    "Futebol Nacional": "Desporto",
    "Futebol Internacional": "Desporto",
    "Futebol-internacional": "Desporto",
    "Liga D'Ouro": "Desporto",
    "Economia": "Economia",
    "Negócios": "Economia",
    "Segurança Social": "Economia",
    "Bolsa e Mercados": "Economia",
    "Mercados": "Economia",
    "Dinheiro": "Economia",
    "Energia": "Economia",
    "Cultura": "Cultura",
    "Livros": "Cultura",
    "Cinema": "Cultura",
    "Blitz": "Cultura",
    "Ciência e Tech": "Ciência e Tech",
    "Ciência & Tech": "Ciência e Tech",
    "Ciência": "Ciência e Tech",
    "Tech": "Ciência e Tech",
    "Direto do lab": "Ciência e Tech",
    "Exame Informática": "Ciência e Tech",
    "Facebook": "Ciência e Tech",
    "Sociedade": "Sociedade",
    "Coronavírus": "Sociedade",
    "Mau tempo": "Sociedade",
    "Animais": "Sociedade",
    "Insólitos": "Sociedade",
    "Meteorologia": "Sociedade",
    "Alterações climáticas": "Sociedade",
    "Saúde": "Sociedade",
    "Clima": "Sociedade",
    "Religiao": "Sociedade",
    "Justiça": "Sociedade",
    "Política": "Política",
    "Politica": "Política",
    "Defesa": "Política",
    "Presidenciais 2026": "Política",
    "Parlamento": "Política",
    "Partidos": "Política",
    "Multimédia": "Multimédia",
    "Fotogaleria": "Multimédia",
    "O Mundo a Seus Pés": "Multimédia",
    "Contas Poupança": "Multimédia",
    "O CEO é o limite": "Multimédia",
    "Facto político": "Multimédia",
    "Alta definição": "Multimédia",
    "Expresso da Manhã": "Multimédia",
    "Isto É Gozar Com Quem Trabalha": "Multimédia",
    "Ana Gomes": "Multimédia",
    "Noticiários Desporto": "Multimédia",
    "Minuto Consumidor": "Multimédia",
    "Noticiário Antena1": "Multimédia",
    "Leste Oeste de Nuno Rogeiro": "Multimédia",
    "Vídeos": "Multimédia",
    "Tv Media": "Multimédia",
    "Opinião": "Opinião",
    "Nota editorial": "Opinião",
    "José jorge letria": "Opinião",
    "Lifestyle": "Lifestyle",
    "Comer e beber": "Lifestyle",
    "Gastronomia": "Lifestyle",
    "Vida": "Lifestyle",
    "Boa cama boa mesa": "Lifestyle",
    "Vidas": "Lifestyle",
    "Fama": "Lifestyle",
    "Ideias": "Lifestyle",
    "Vídeojogos": "Vídeojogos",
    "Outras Notícias": "Outras Notícias"
}

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z"
]


@dataclass
class Article:
    title: str
    description: str
    image: Optional[str]
    source: str
    pub_date: str
    category: str
    link: str
    is_exclusive: bool

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "image": self.image,
            "source": self.source,
            "pubDate": self.pub_date,
            "category": self.category,
            "link": self.link,
            "isExclusive": self.is_exclusive
        }

class ArticleCache:
    def __init__(self, cache_duration: int = 3600):  # 1 hour default cache duration
        self._cache: Dict[str, Tuple[datetime, Article]] = {}
        self._cache_duration = timedelta(seconds=cache_duration)

    def get(self, key: str) -> Optional[Article]:
        if key in self._cache:
            timestamp, article = self._cache[key]
            if datetime.now() - timestamp < self._cache_duration:
                return article
            del self._cache[key]
        return None

    def set(self, key: str, article: Article) -> None:
        self._cache[key] = (datetime.now(), article)

    def clear_expired(self) -> None:
        now = datetime.now()
        expired_keys = [
            key for key, (timestamp, _) in self._cache.items()
            if now - timestamp >= self._cache_duration
        ]
        for key in expired_keys:
            del self._cache[key]

class AsyncNewsAPI:
    def __init__(self):
        self.cache = ArticleCache()
        self.session = None
        self.timeout = ClientTimeout(total=30)

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0"}
            )

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_api_source(self, source: dict) -> List[Article]:
        try:
            async with self.session.get(source["url"], headers=source["headers"]) as response:
                if response.status != 200:
                    logger.error(f"Error fetching API {source['url']}: {response.status}")
                    return []

                data = await response.json()
                articles = []

                articles_list = data if isinstance(data, list) else data.get("articles", [])
                
                for item in articles_list:
                    try:
                        title = self.clean_title(item.get("title", "Sem título"))
                        cache_key = self.generate_cache_key(title, item.get("url", ""))
                        
                        cached_article = self.cache.get(cache_key)
                        if cached_article:
                            articles.append(cached_article)
                            continue

                        article = await self.process_api_item(item)
                        if article:
                            self.cache.set(cache_key, article)
                            articles.append(article)

                    except Exception as e:
                        logger.error(f"Error processing API item: {e}")
                        continue

                return articles

        except Exception as e:
            logger.error(f"Error fetching API source: {e}")
            return []

class AsyncNewsAPI:
    def __init__(self):
        self.cache = ArticleCache()
        self.session = None
        self.timeout = ClientTimeout(total=30)
        self.titles_seen: Set[str] = set()

    @staticmethod
    def generate_cache_key(title: str, link: str) -> str:
        """Generate a unique cache key for an article."""
        return hashlib.md5(f"{title}{link}".encode()).hexdigest()

    async def create_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0"}
            )

    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    @staticmethod
    def clean_title(title: str) -> str:
        if title.startswith("<![CDATA[") and title.endswith("]]>"):
            title = title[9:-3]
        return title.strip()

    @staticmethod
    def clean_description(description: str) -> str:
        description = unescape(description)
        description = re.sub(r"<[^>]+>", "", description)
        description = description.replace('\"', "").replace("\n", " ")
        description = description.strip()

        if len(description) > 150:
            description = description[:230].rsplit(' ', 1)[0] + "..."

        return description

    @staticmethod
    def extract_source_from_url(url: str) -> str:
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            domain = re.sub(r'^www\.', '', domain)
            domain = domain.split('.')[0]
            
            source_mapping = {
                'observador': 'Observador',
                'publico': 'Público',
                'expresso': 'Expresso',
                'cmjornal': 'Correio da Manhã',
                'jornaldenegocios': 'Jornal de Negócios',
                'rtp': 'RTP',
                'sapo': 'SAPO',
                'euronews': 'Euronews'
            }
            
            return source_mapping.get(domain.lower(), domain.capitalize())
            
        except Exception as e:
            logger.error(f"Erro ao extrair fonte da URL {url}: {e}")
            return "Desconhecido"

    @lru_cache(maxsize=100)
    def map_category(self, feed_category: Optional[str], feed_domain: str, item_link: Optional[str]) -> str:
        if feed_category in CATEGORY_MAPPER:
            return CATEGORY_MAPPER[feed_category]

        if "cmjornal.pt" in feed_domain and item_link:
            parsed_url = urlparse(item_link)
            path_parts = parsed_url.path.strip("/").split("/")
            if path_parts:
                cm_category = path_parts[0].capitalize()
                return CATEGORY_MAPPER.get(cm_category, "Outras Notícias")

        if "rr.sapo.pt" in feed_domain and item_link and "/noticia/" in item_link:
            try:
                parsed_url = urlparse(item_link)
                path_parts = parsed_url.path.strip("/").split("/")
                if "noticia" in path_parts:
                    index = path_parts.index("noticia")
                    if index + 1 < len(path_parts):
                        rr_category = path_parts[index + 1].capitalize()
                        return CATEGORY_MAPPER.get(rr_category, rr_category)
            except (ValueError, IndexError):
                pass

        for feed, category in FEED_CATEGORY_MAPPER.items():
            if feed_domain.startswith(feed):
                return category

        return "Outras Notícias"

class AsyncNewsAPI(AsyncNewsAPI):  # Continua a classe anterior
    @staticmethod
    def parse_date(date_str: str) -> Optional[datetime]:
        if not date_str:
            return None

        date_str = date_str.strip()
        date_str = date_str.encode('ascii', 'ignore').decode('ascii')

        if "GMT+" in date_str:
            date_str = re.sub(r'GMT\+(\d+)', lambda m: f"+{m.group(1).zfill(2)}00", date_str)
        elif "GMT-" in date_str:
            date_str = re.sub(r'GMT-(\d+)', lambda m: f"-{m.group(1).zfill(2)}00", date_str)

        for fmt in DATE_FORMATS:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue

        return None

    async def check_exclusive(self, url: str) -> bool:
        if not any(domain in url for domain in ["publico.pt", "expresso.pt", "observador.pt"]):
            return False

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return False

                content = await response.text()
                exclusive_patterns = {
                    "publico.pt": '<div class="kicker kicker--exclusive">',
                    "expresso.pt": '<span class="exclusive-label-inner">Exclusivo</span>',
                    "observador.pt": '<obs-paywall-btn'
                }

                for domain, pattern in exclusive_patterns.items():
                    if domain in url and pattern in content:
                        return True

                return False

        except Exception as e:
            logger.error(f"Error checking exclusive content: {e}")
            return False

    async def extract_image_url(self, item: ET.Element, link: str) -> Optional[str]:
        try:
            # Check standard RSS image tags first
            namespaces = {"media": "http://search.yahoo.com/mrss/"}
            for tag in ["media:content", "enclosure", "image", "img", "post-thumbnail"]:
                element = item.find(tag, namespaces)
                if element is None:
                    element = item.find(tag)

                if element is not None:
                    url = None
                    if tag == "post-thumbnail" and element.find("url") is not None:
                        url = element.find("url").text
                    elif "url" in element.attrib:
                        url = element.attrib["url"]

                    if url:
                        # Apply image URL transformations
                        if "100x100" in url:
                            url = url.replace("100x100", "932x621")
                        if "932x621" in url and "jornaldenegocios" in url:
                            url = url.replace("932x621", "900x560")
                        if url.startswith("https://cdn.record.pt/images/https://cdn.record.pt/images/"):
                            url = url.replace("https://cdn.record.pt/images/", "", 1)
                        return url

            # Check content:encoded
            content_encoded = item.find("content:encoded")
            if content_encoded is not None and content_encoded.text:
                match = re.search(r'<img\s+[^>]*src="([^"]+)"', content_encoded.text)
                if match:
                    return match.group(1)

            # Check description
            description = item.find("description")
            if description is not None and description.text:
                if "pplware" in link:
                    match = re.search(r'<img\s+[^>]*src="([^"]+)"', description.text)
                    if match:
                        return match.group(1)
                match = re.search(r'<img\s+src="([^"]+)"', description.text)
                if match:
                    return match.group(1)

            # Fetch image from article page if needed
            if link and any(domain in link for domain in ["ionline.sapo.pt"]):
                async with self.session.get(link) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'html.parser')
                        for img in soup.find_all('img'):
                            src = img.get('data-src') or img.get('src')
                            if src and src.startswith("https://ionline.sapo.pt/wp-content/uploads/"):
                                return src

            return None

        except Exception as e:
            logger.error(f"Error extracting image URL: {e}")
            return None

    async def process_rss_item(self, item: ET.Element, root: ET.Element, feed_url: str) -> Optional[Article]:
        try:
            title = self.clean_title(item.findtext("title", "").strip())
            
            if title in self.titles_seen:
                return None
                
            self.titles_seen.add(title)
            description = self.clean_description(item.findtext("description", "").strip())
            pub_date_str = item.findtext("pubDate", "").strip()
            source = self.extract_source_from_url(feed_url)
            link = item.findtext("link", "").strip()
            image_url = await self.extract_image_url(item, link)
            feed_category = item.findtext("category")
            category = self.map_category(feed_category, feed_url, link)
            is_exclusive = await self.check_exclusive(link)

            pub_date = self.parse_date(pub_date_str)
            if not pub_date:
                return None

            now = datetime.now(timezone.utc)
            if (category == "Últimas" and pub_date >= now - timedelta(hours=12)) or \
               (category != "Últimas" and pub_date >= now - timedelta(days=2)):
                return Article(
                    title=title,
                    description=description,
                    image=image_url,
                    source=source,
                    pub_date=pub_date.strftime("%d-%m-%Y %H:%M"),
                    category=category,
                    link=link,
                    is_exclusive=is_exclusive
                )

            return None

        except Exception as e:
            logger.error(f"Error processing RSS item: {e}")
            return None

    async def fetch_rss_feed(self, feed_url: str) -> List[Article]:
        try:
            async with self.session.get(feed_url) as response:
                if response.status != 200:
                    logger.error(f"Error fetching RSS feed {feed_url}: {response.status}")
                    return []

                content = await response.text()
                if not content.strip():
                    return []

                root = ET.fromstring(content)
                articles = []

                for item in root.findall(".//item"):
                    article = await self.process_rss_item(item, root, feed_url)
                    if article:
                        articles.append(article)

                return articles

        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {e}")
            return []

    async def fetch_all_sources(self) -> List[Article]:
        await self.create_session()
        try:
            # Fetch RSS feeds
            rss_tasks = [self.fetch_rss_feed(feed_url) for feed_url in RSS_FEEDS]
            # Fetch API sources
            api_tasks = [self.fetch_api_source(source) for source in API_SOURCES]
            
            # Gather all results
            all_results = await asyncio.gather(*(rss_tasks + api_tasks))
            all_articles = [article for sublist in all_results for article in sublist if article]
            
            # Sort articles by date
            all_articles.sort(
                key=lambda x: datetime.strptime(x.pub_date, "%d-%m-%Y %H:%M"),
                reverse=True
            )
            
            return all_articles

        finally:
            await self.close_session()

    async def export_to_json(self, articles: List[Article]):
        categorized_data = {"Últimas": [article.to_dict() for article in articles]}

        for category in [
            "Nacional", "Mundo", "Desporto", "Economia", "Cultura",
            "Ciência e Tech", "Lifestyle", "Sociedade", "Política",
            "Multimédia", "Opinião", "Vídeojogos", "Outras Notícias"
        ]:
            categorized_data[category] = [
                article.to_dict() for article in articles
                if article.category == category
            ]

        with open("articles.json", "w", encoding="utf-8") as f:
            json.dump(categorized_data, f, ensure_ascii=False, indent=4)

async def main():
    api = AsyncNewsAPI()
    articles = await api.fetch_all_sources()
    await api.export_to_json(articles)
    logger.info(f"Processed {len(articles)} articles")

if __name__ == "__main__":
    asyncio.run(main())
