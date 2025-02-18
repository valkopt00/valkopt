import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import json
import re
from html import unescape
from xml.etree.ElementTree import Element
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import feedparser
import asyncio
import aiohttp
from aiohttp import ClientTimeout
import chardet

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
    "https://pt.ign.com/feed.xml",
    "https://caras.pt/feed/"
]

API_SOURCES = [
    {
        "url": "https://www.publico.pt/api/list/ultimas",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "source_name": "Público"
    },
    {
        "url": "https://observador.pt/wp-json/obs_api/v4/news/widget",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "source_name": "Observador"
    }
]

FEED_CATEGORY_MAPPER = {
    "https://pt.euronews.com/rss?format=mrss&level=theme&name=news": "Últimas",
    "https://www.publico.pt/api/list/ultimas" : "Últimas",
    
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

async def get_articles():
    articles = []
    now = datetime.now(timezone.utc)
    last_12_hours = now - timedelta(hours=12)
    last_48_hours = now - timedelta(days=2)
    titles_seen = set()

    async with aiohttp.ClientSession() as session:
        # Create tasks for RSS feeds
        rss_tasks = [process_rss_feed(session, feed_url, titles_seen, last_12_hours, last_48_hours) 
                     for feed_url in RSS_FEEDS]
        
        # Create tasks for API sources
        api_tasks = [process_api_source(session, source, titles_seen, last_12_hours, last_48_hours) 
                    for source in API_SOURCES]
        
        # Gather all results
        all_results = await asyncio.gather(*rss_tasks, *api_tasks, return_exceptions=True)
        
        # Flatten results and filter out errors
        for result in all_results:
            if isinstance(result, list):
                articles.extend(result)
            else:
                print(f"Error processing feed: {result}")

    # Sort articles by date
    articles.sort(key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"), reverse=True)
    
    # Process articles for additional info (images, exclusive status)
    await process_articles(articles)
    
    # Export to JSON
    export_to_json(articles)
                                
def export_to_json(articles):
    categorized_data = {"Últimas": articles}

    for category in ["Nacional", "Mundo", "Desporto", "Economia", "Cultura", "Ciência e Tech", "Lifestyle", 
                     "Sociedade", "Política", "Multimédia", "Opinião", "Vídeojogos", "Outras Notícias"]:
        categorized_data[category] = [article for article in articles if article["category"] == category]

    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(categorized_data, f, ensure_ascii=False, indent=4)

async def process_rss_feed(session, feed_url, titles_seen, last_12_hours, last_48_hours):
    try:
        # Set timeout for initial feed fetch
        timeout = ClientTimeout(total=30)
        headers = {"User-Agent": "Mozilla/5.0"}
        
        async with session.get(feed_url, headers=headers, timeout=timeout) as response:
            if response.status != 200:
                print(f"Error fetching {feed_url}: Status {response.status}")
                return []
                
            # Read raw bytes
            content_bytes = await response.read()
            
            # Detect encoding
            detected = chardet.detect(content_bytes)
            encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
            
            try:
                content = content_bytes.decode(encoding)
            except UnicodeDecodeError:
                # Fallback to latin1 if UTF-8 fails
                content = content_bytes.decode('latin1')
            
            if not content.strip():
                return []
                
            # Use feedparser instead of ElementTree for more robust RSS parsing
            feed = feedparser.parse(content)
            feed_domain = get_feed_domain(feed_url)
            articles = []
            
            for entry in feed.entries:
                title = clean_title(entry.get('title', '').strip())
                if title in titles_seen:
                    continue
                    
                titles_seen.add(title)
                description = clean_description(entry.get('description', '').strip())
                pub_date_str = entry.get('published', '')
                source = extract_source_from_feed(feed)
                link = entry.get('link', '').strip()
                image_url = await extract_image_url(entry, session)
                feed_category = entry.get('category', '')
                
                category = map_category(feed_category, feed_domain, link)
                pub_date = parse_date(pub_date_str)
                
                if pub_date:
                    article = {
                        "title": title,
                        "description": description,
                        "image": image_url,
                        "source": source,
                        "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),
                        "category": category,
                        "link": link,
                        "isExclusive": False
                    }
                    
                    if (category == "Últimas" and pub_date >= last_12_hours) or \
                       (category != "Últimas" and pub_date >= last_48_hours):
                        articles.append(article)
            
            return articles
                        
    except Exception as e:
        print(f"Error processing {feed_url}: {str(e)}")
        return []

async def process_api_source(session, api_source, titles_seen, last_12_hours, last_48_hours):
    try:
        async with session.get(api_source["url"], headers=api_source["headers"]) as response:
            if response.status != 200:
                return []
                
            data = await response.json()
            articles = []
            
            # Handle both list and dict responses
            articles_list = data if isinstance(data, list) else data.get("articles", [])
            
            for item in articles_list:
                title = clean_title(item.get("titulo") or item.get("title", "Sem título"))
                if title in titles_seen:
                    continue
                    
                titles_seen.add(title)
                description = clean_description(item.get("descricao") or item.get("lead", ""))
                pub_date_str = item.get("data") or item.get("publish_date", "")
                link = item.get("url", "")
                source = extract_source_from_url(link)
                image_url = item.get("multimediaPrincipal") or item.get("image", "")
                feed_category = item.get("rubrica") or item.get("tag", "Últimas")
                
                category = map_category(feed_category, source, link)
                if not category:
                    category = "Últimas"
                    
                pub_date = parse_date(pub_date_str)
                
                if pub_date:
                    article = {
                        "title": title,
                        "description": description,
                        "image": image_url,
                        "source": source,
                        "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),
                        "category": category,
                        "link": link,
                        "isExclusive": False
                    }
                    
                    if (category == "Últimas" and pub_date >= last_12_hours) or \
                       (category != "Últimas" and pub_date >= last_48_hours):
                        articles.append(article)
                        
            return articles
            
    except Exception as e:
        print(f"Error processing API {api_source['url']}: {e}")
        return []

async def is_content_exclusive_from_url(link, session):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        async with session.get(link, headers=headers, timeout=5) as response:
            content = await response.text()
    except Exception as e:
        print(f"Erro ao acessar {link}: {e}")
        return False  # Não é possível determinar, assume como não exclusivo

    soup = BeautifulSoup(content, 'html.parser')
    
    # Listar fontes e seus indicadores de exclusividade
    source_checks = [
        {
            'domain': 'publico.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'paywall'},
                {'type': 'text', 'value': 'Exclusivo para assinantes'}
            ]
        },
        {
            'domain': 'expresso.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'premium-icon'},
                {'type': 'text', 'value': 'Para continuar a ler, assine o Expresso'}
            ]
        },
        # Adicionar outras fontes conforme necessário
    ]
    
    parsed_url = urlparse(link)
    domain = parsed_url.netloc.replace('www.', '')
    
    for source in source_checks:
        if source['domain'] in domain:
            # Verificar indicadores no conteúdo da página
            for indicator in source['exclusive_indicators']:
                if indicator['type'] == 'class':
                    if soup.find(class_=indicator['value']):
                        return True
                elif indicator['type'] == 'text':
                    if indicator['value'].lower() in soup.get_text().lower():
                        return True
    # Verificação genérica para páginas que não estejam na lista específica
    exclusive_phrases = [
        "conteúdo exclusivo para assinantes",
        "exclusivo para assinantes",
        "acesso exclusivo para assinantes",
        "assinantes",
        "assine para continuar a ler",
        "assinatura digital",
        "log in para ler",
        "inicie sessão para continuar a ler"
    ]
    page_text = soup.get_text(separator=' ', strip=True).lower()
    if any(phrase in page_text for phrase in exclusive_phrases):
        return True

    return False

def clean_title(title):
    """ Corrige títulos dentro de CDATA e remove caracteres desnecessários. """
    if title.startswith("<![CDATA[") and title.endswith("]]>"):
        title = title[9:-3]  # Remove CDATA
    return title.strip()

def clean_description(description):
    """ Remove HTML, caracteres de escape e limita a 150 caracteres sem cortar palavras. """
    description = unescape(description)  # Remove caracteres HTML escapados
    description = re.sub(r"<[^>]+>", "", description)  # Remove tags HTML
    description = description.replace('\"', "").replace("\n", " ")  # Remove \"
    description = description.strip()

    # Limita a 150 caracteres, garantindo que não corta palavras
    if len(description) > 150:
        description = description[:150].rsplit(' ', 1)[0] + "..."
    
    return description

def extract_source_from_feed(feed):
    """Extract source from feedparser feed object"""
    if hasattr(feed, 'feed') and hasattr(feed.feed, 'title'):
        source_name = feed.feed.title
        if source_name == "News | Euronews RSS":
            return "Euronews"
        if source_name == "Notícias zerozero.pt":
            return "zerozero.pt"
        if source_name == "Eurogamer.pt Latest Articles Feed":
            return "Eurogamer"
        source_name = re.split(r" - | / ", source_name)[0]
        return source_name
    return "Desconhecido"

def extract_source(root):
    """ Extrai a fonte e remove sufixos indesejados. """
    channel_title = root.find(".//channel/title")
    if channel_title is not None:
        source_name = channel_title.text.strip()
        if source_name == "News | Euronews RSS":
            return "Euronews"
        if source_name == "Notícias zerozero.pt":
            return "zerozero.pt"
        if source_name == "Eurogamer.pt Latest Articles Feed":
            return "Eurogamer"
        source_name = re.split(r" - | / ", source_name)[0]  # Remove tudo após " - " ou " / "
        return source_name
    return "Desconhecido"

def extract_source_from_url(url):
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.split('.')[0]
        
        source_mapping = {
            'observador': 'Observador',
            'publico': 'Público',
        }
        
        return source_mapping.get(domain.lower(), domain.capitalize())
        
    except Exception as e:
        print(f"Erro ao extrair fonte da URL {url}: {e}")
        return "Desconhecido"

async def process_articles(articles):
    """
    Processa em paralelo todos os artigos para adicionar informações adicionais
    como status exclusivo e imagens faltantes.
    """
    tasks = []
    async with aiohttp.ClientSession() as session:
        for article in articles:
            task = asyncio.create_task(process_article(article, session))
            tasks.append(task)
        await asyncio.gather(*tasks)

async def process_article(article, session):
    """
    Processa um único artigo para adicionar informações como
    status exclusivo e imagem (se estiver faltando).
    """
    link = article['link']
    
    # Verifica se o artigo é exclusivo
    is_exclusive = await is_content_exclusive_from_url(link, session)
    article['isExclusive'] = is_exclusive
    
    # Atualiza a imagem se necessário
    if not article['image']:
        image_url = await get_image_url_from_link(link, session)
        article['image'] = image_url

    
async def get_image_url_from_link(news_url, session):
    """Safer version of get_image_url_from_link with proper timeout handling"""
    timeout = ClientTimeout(total=10)  # 10 second timeout
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        async with session.get(news_url, headers=headers, timeout=timeout) as response:
            if response.status != 200:
                return None
            content = await response.text()
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Priority list of image selectors
            selectors = [
                {'type': 'class', 'value': 'wp-post-image'},
                {'type': 'class', 'value': 'wp-block-cover__image-background'},
                {'type': 'property', 'value': 'og:image'},
                {'type': 'name', 'value': 'twitter:image'}
            ]
            
            # Try meta tags first
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
        print(f"Timeout while fetching image from {news_url}")
        return None
    except Exception as e:
        print(f"Error fetching image from {news_url}: {str(e)}")
        return None
    
async def extract_image_url(entry, session):
    """Safer version of extract_image_url with better error handling"""
    try:
        # Check for media content
        if 'media_content' in entry and entry.media_content:
            for media in entry.media_content:
                if 'url' in media:
                    return media['url']
        
        # Check for enclosures
        if 'enclosures' in entry and entry.enclosures:
            for enclosure in entry.enclosures:
                if 'url' in enclosure and enclosure.type and enclosure.type.startswith('image/'):
                    return enclosure['url']
        
        # Check description for image
        if 'description' in entry:
            soup = BeautifulSoup(entry.description, 'html.parser')
            img = soup.find('img')
            if img and img.get('src'):
                return img['src']
        
        # If no image found and we have a link, try to fetch from article with timeout
        if 'link' in entry:
            return await get_image_url_from_link(entry.link, session)
            
    except Exception as e:
        print(f"Error extracting image URL: {str(e)}")
        
    return None

def parse_date(date_str):
    """
    Converte a data do RSS para datetime.
    Retorna um objeto datetime com timezone UTC
    """
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
    
def get_feed_domain(feed_url):
    """ Extrai a URL completa do feed RSS. """
    return feed_url

def map_category(feed_category, feed_url, item_link=None):
    # Primeiro, verifica se a tag <category> possui correspondência no CATEGORY_MAPPER
    if feed_category in CATEGORY_MAPPER:
        return CATEGORY_MAPPER[feed_category]

    # Em seguida, verifica a exceção para o CM Jornal: extrai a categoria do link da notícia (item_link)
    if "cmjornal.pt" in feed_url and item_link:
        parsed_url = urlparse(item_link)
        path_parts = parsed_url.path.strip("/").split("/")
        if path_parts:  # Se houver pelo menos um segmento na URL
            cm_category = path_parts[0].lower()
            cm_category = cm_category.capitalize()
            # Aplica o CATEGORY_MAPPER à categoria extraída
            if cm_category in CATEGORY_MAPPER:
                return CATEGORY_MAPPER[cm_category]
            return "Outras Notícias"
            
    # Verifica a exceção para a RR: extrai a categoria do link da notícia
    if "rr.sapo.pt" in feed_url and item_link and "/noticia/" in item_link:
        try:
            parsed_url = urlparse(item_link)
            path_parts = parsed_url.path.strip("/").split("/")
            # Encontra o índice de "noticia" e verifica o próximo segmento
            if "noticia" in path_parts:
                index = path_parts.index("noticia")
                if index + 1 < len(path_parts):  # Verifica se existe um segmento após "noticia"
                    rr_category = path_parts[index + 1].lower()
                    rr_category = rr_category.capitalize()
                    if rr_category in CATEGORY_MAPPER:
                        return CATEGORY_MAPPER[rr_category]
                    return rr_category  # Retorna a categoria extraída, mesmo que não esteja no CATEGORY_MAPPER
        except (ValueError, IndexError):
            pass
            
    # Por fim, verifica o mapeamento completo de feeds
    for feed, category in FEED_CATEGORY_MAPPER.items():
        if feed_url.startswith(feed):  # Verifica se a URL do feed começa com a URL mapeada
            return category
        
    return "Outras Notícias"

async def main():
    await get_articles()

if __name__ == "__main__":
    asyncio.run(main())
