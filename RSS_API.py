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
import traceback

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
    "https://lusometeo.com/feed/",
    "https://caras.pt/feed/"
]

API_SOURCES = [
    {
        "url": "https://observador.pt/wp-json/obs_api/v4/news/widget",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "source_name": "Observador"
    }
]

FEED_CATEGORY_MAPPER = {
    "https://pt.euronews.com/rss?format=mrss&level=theme&name=news": "Últimas",
    "https://feeds.feedburner.com/PublicoRSS" : "Últimas",
    
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
    "https://lusometeo.com/feed/": "Sociedade",
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
    "Auto": "Desporto",
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
    "Colunistas": "Opinião",
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
    titles_seen = set()

    async with aiohttp.ClientSession() as session:
        rss_tasks = [process_rss_feed(session, feed_url, titles_seen, last_12_hours) 
                     for feed_url in RSS_FEEDS]
        api_tasks = [process_api_source(session, source, titles_seen, last_12_hours) 
                     for source in API_SOURCES]
        all_results = await asyncio.gather(*rss_tasks, *api_tasks, return_exceptions=True)
        for result in all_results:
            if isinstance(result, list):
                articles.extend(result)
            else:
                print(f"Error processing feed: {result}")

    articles.sort(key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"), reverse=True)
    await process_articles(articles)
    export_to_json(articles)
                                
def export_to_json(articles):
    current_date = datetime.now(timezone.utc)
    existing_articles = load_existing_articles()
    merged_articles = merge_articles(existing_articles, articles, current_date)
    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(merged_articles, f, ensure_ascii=False, indent=4)

async def process_rss_feed(session, feed_url, titles_seen, last_12_hours):
    try:
        timeout = ClientTimeout(total=30)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        
        async with session.get(feed_url, headers=headers, timeout=timeout) as response:
            if response.status != 200:
                print(f"Error fetching {feed_url}: Status {response.status}")
                return []
                
            content_bytes = await response.read()
            if "publico.pt" in feed_url or "PublicoRSS" in feed_url:
                try:
                    content = content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        content = content_bytes.decode('cp1252')
                    except UnicodeDecodeError:
                        content = content_bytes.decode('latin1')
                print(f"Processing Público feed from {feed_url}")
            else:
                detected = chardet.detect(content_bytes)
                encoding = detected['encoding'] if detected['confidence'] > 0.7 else 'utf-8'
                try:
                    content = content_bytes.decode(encoding)
                except UnicodeDecodeError:
                    content = content_bytes.decode('latin1')
            
            if not content.strip():
                return []
                
            feed = feedparser.parse(content)
            if "publico.pt" in feed_url or "PublicoRSS" in feed_url:
                print(f"Found {len(feed.entries)} entries in Público feed")
            
            feed_domain = get_feed_domain(feed_url)
            articles = []
            
            for entry in feed.entries:
                try:
                    title = clean_title(entry.get('title', '').strip())
                    if not title or title in titles_seen:
                        continue
                    titles_seen.add(title)
                    description = entry.get('summary', '') or entry.get('description', '')
                    description = clean_description(description.strip())
                    pub_date_str = entry.get('published', '') or entry.get('pubDate', '') or entry.get('updated', '')
                    source = extract_source(feed)
                    link = entry.get('link', '').strip()
                    if "publico.pt" in feed_url and not link.startswith('http'):
                        link = f"https://www.publico.pt{link}"
                    image_url = await extract_image_url(entry, session)
                    feed_category = entry.get('category', '')
                    if isinstance(feed_category, list):
                        feed_category = feed_category[0] if feed_category else ''
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
                        
                        if category == "Últimas" and pub_date >= last_12_hours:
                            articles.append(article)
                        elif category != "Últimas":
                            articles.append(article)
                
                except Exception as e:
                    print(f"Error processing entry from {feed_url}: {str(e)}")
                    continue
            
            if "publico.pt" in feed_url or "PublicoRSS" in feed_url:
                print(f"Total articles processed from Público: {len(articles)}")
            return articles
                        
    except Exception as e:
        print(f"Error processing {feed_url}: {str(e)}")
        return []

def parse_date(date_str):
    if not date_str:
        return None
        
    date_str = date_str.strip()
    date_str = date_str.encode('ascii', 'ignore').decode('ascii')
    
    if "GMT+" in date_str:
        date_str = re.sub(r'GMT\+(\d+)', lambda m: f"+{m.group(1).zfill(2)}00", date_str)
    elif "GMT-" in date_str:
        date_str = re.sub(r'GMT-(\d+)', lambda m: f"-{m.group(1).zfill(2)}00", date_str)
    
    DATE_FORMATS.extend([
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %Z",
    ])
    
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
            
    print(f"Failed to parse date: {date_str}")
    return None

async def process_api_source(session, api_source, titles_seen, last_12_hours):
    try:
        async with session.get(api_source["url"], headers=api_source["headers"]) as response:
            if response.status != 200:
                return []
            data = await response.json()
            articles = []
            articles_list = data if isinstance(data, list) else data.get("articles", [])
            
            for item in articles_list:
                title = clean_title(item.get("titulo") or item.get("title", "Sem título"))
                if title in titles_seen:
                    continue
                titles_seen.add(title)
                description = clean_description(item.get("descricao") or item.get("lead", ""))
                pub_date_str = item.get("data") or item.get("publish_date", "")
                link = item.get("url", "")
                source = extract_source(link)
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
                    
                    if category == "Últimas" and pub_date >= last_12_hours:
                        articles.append(article)
                    elif category != "Últimas":
                        articles.append(article)
            return articles
    except Exception as e:
        print(f"Erro ao acessar {api_source['url']}: {e}")
        traceback.print_exc()
        return False

def load_existing_articles():
    try:
        with open("articles.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"Últimas": [], "Nacional": [], "Mundo": [], "Desporto": [], 
                "Economia": [], "Cultura": [], "Ciência e Tech": [], "Lifestyle": [],
                "Sociedade": [], "Política": [], "Multimédia": [], "Opinião": [], 
                "Vídeojogos": [], "Outras Notícias": []}

def is_article_within_timeframe(article_date_str, category, current_date):
    article_date = datetime.strptime(article_date_str, "%d-%m-%Y %H:%M")
    article_date = article_date.replace(tzinfo=timezone.utc)
    
    if category == "Últimas":
        return current_date - article_date <= timedelta(hours=12)
    else:
        return current_date - article_date <= timedelta(days=15)

def merge_articles(existing_articles, new_articles, current_date):
    merged = {}
    seen_titles = set()
    
    for category in existing_articles.keys():
        merged[category] = []
        
    all_articles = []
    
    for category, articles in existing_articles.items():
        for article in articles:
            if isinstance(article, dict):
                all_articles.append(article)
    
    all_articles.extend(new_articles)
    
    for article in all_articles:
        title = article.get("title")
        category = article.get("category")
        pub_date = article.get("pubDate")
        
        if not all([title, category, pub_date]):
            continue
            
        if title in seen_titles:
            continue
            
        if not is_article_within_timeframe(pub_date, category, current_date):
            continue
            
        seen_titles.add(title)
        
        if category in merged:
            merged[category].append(article)
            
        if is_article_within_timeframe(pub_date, "Últimas", current_date):
            if article not in merged["Últimas"]:
                merged["Últimas"].append(article)
    
    for category in merged:
        merged[category].sort(
            key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"),
            reverse=True
        )
    
    return merged

def export_original_categories_to_json(articles):
    import json
    import traceback
    
    try:
        print("Iniciando exportação de categorias originais...")
        
        # Verificação de dados de entrada
        if not articles:
            print("AVISO: Lista de artigos vazia!")
        
        print(f"Número de artigos recebidos: {len(articles)}")
        print(f"CATEGORY_MAPPER contém {len(CATEGORY_MAPPER)} mapeamentos")
        print(f"FEED_CATEGORY_MAPPER contém {len(FEED_CATEGORY_MAPPER)} mapeamentos")
        
        categories_seen = set()
        
        # Parte 1: Coletar categorias com base no mapeamento
        for i, article in enumerate(articles):
            try:
                mapped_category = article.get("category", "")
                if not mapped_category:
                    continue
                    
                for original_cat, mapped_cat in CATEGORY_MAPPER.items():
                    if mapped_cat == mapped_category:
                        if original_cat and original_cat not in categories_seen:
                            categories_seen.add(original_cat)
                            print(f"Adicionada categoria: {original_cat}")
            except Exception as e:
                print(f"Erro ao processar artigo {i}: {str(e)}")
        
        # Parte 2: Coletar categorias do FEED_CATEGORY_MAPPER
        for feed_url, category in FEED_CATEGORY_MAPPER.items():
            print(f"Processando feed: {feed_url} -> {category}")
            found_match = False
            
            for article in articles:
                article_link = article.get("link", "")
                if not article_link:
                    continue
                    
                # Simplificando a verificação de domínio
                if feed_url.lower() in article_link.lower():
                    found_match = True
                    if category and category not in categories_seen:
                        categories_seen.add(category)
                        print(f"Adicionada categoria do feed: {category}")
            
            if not found_match:
                print(f"Nenhum artigo correspondente encontrado para o feed: {feed_url}")
        
        # Criar e guardar JSON
        unique_categories = [{"category": cat} for cat in sorted(categories_seen)]
        print(f"Total de categorias encontradas: {len(categories_seen)}")
        
        try:
            with open("original_categories.json", "w", encoding="utf-8") as f:
                json.dump(unique_categories, f, ensure_ascii=False, indent=4)
            print("Ficheiro salvo com sucesso.")
        except Exception as e:
            print(f"Erro ao guardar ficheiro: {str(e)}")
            
        print("Exportação concluída.")
        return True
        
    except Exception as e:
        print(f"ERRO CRÍTICO na exportação de categorias: {str(e)}")
        traceback.print_exc()
        return False

async def is_content_exclusive_from_url(link, session):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        async with session.get(link, headers=headers, timeout=10) as response:
            content = await response.text()
    except Exception as e:
        print(f"Erro ao acessar {link}: {e}")
        return False

    soup = BeautifulSoup(content, 'html.parser')
    
    source_checks = [
        {
            'domain': 'publico.pt',
            'exclusive_indicators': [
                {'type': 'class', 'value': 'kicker kicker--exclusive'},
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
    
    parsed_url = urlparse(link)
    domain = parsed_url.netloc.replace('www.', '')
    
    for source in source_checks:
        if source['domain'] in domain:
            for indicator in source['exclusive_indicators']:
                if indicator['type'] == 'class':
                    if soup.find(class_=indicator['value']):
                        return True
                elif indicator['type'] == 'text':
                    if indicator['value'].lower() in soup.get_text().lower():
                        return True
    exclusive_phrases = []
    page_text = soup.get_text(separator=' ', strip=True).lower()
    if any(phrase in page_text for phrase in exclusive_phrases):
        return True

    return False

def clean_title(title):
    if title.startswith("<![CDATA[") and title.endswith("]]>"):
        title = title[9:-3]
    title = re.sub(r"<.*?>", "", title)
    title = unescape(title)
    return title.strip()

def clean_description(description):
    description = unescape(description)
    description = re.sub(r"<[^>]+>", "", description)
    description = description.replace('\"', "").replace("\n", " ")
    description = re.sub(r'\{(?:[^|}]+\|)*([^|}]+)\}', r'\1', description)
    description = description.strip()
    if len(description) > 150:
        description = description[:150].rsplit(' ', 1)[0] + "..."
    return description

def extract_source(data):
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
            
            # Opcional: normaliza capitalização para outros casos
            return source_name.title()
        elif isinstance(data, str):
            # Verificar URLs específicos
            if data.startswith("https://www.noticiasaominuto.com"):
                return "Notícias ao Minuto"
            elif data.startswith("https://www.rtp.pt/"):
                return "RTP Notícias"
            
            # Processamento padrão para outros URLs
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
        print(f"Erro ao extrair fonte: {e}")
    
    return "Desconhecido"

async def process_articles(articles):
    tasks = []
    async with aiohttp.ClientSession() as session:
        for article in articles:
            task = asyncio.create_task(process_article(article, session))
            tasks.append(task)
        await asyncio.gather(*tasks)

async def process_article(article, session):
    link = article['link']
    is_exclusive = await is_content_exclusive_from_url(link, session)
    article['isExclusive'] = is_exclusive
    if not article['image']:
        image_url = await get_image_url_from_link(link, session)
        article['image'] = image_url

async def get_image_url_from_link(news_url, session):
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
        print(f"Timeout while fetching image from {news_url}")
        return None
    except Exception as e:
        print(f"Error fetching image from {news_url}: {str(e)}")
        return None

def process_url(url: str) -> str:
    if "100x100" in url:
        url = url.replace("100x100", "932x621")
    if "932x621" in url and "jornaldenegocios" in url:
        url = url.replace("932x621", "900x560")
    if url.startswith("https://cdn.record.pt/images/https://cdn.record.pt/images/"):
        url = url.replace("https://cdn.record.pt/images/", "", 1)
    return url

async def extract_image_url(entry, session):
    jornal_economico_logo = "https://leitor.jornaleconomico.pt/assets/uploads/artigos/JE_logo.png"
    try:
        if 'link' in entry and entry.link and "jornaleconomico" in entry.link:
            return jornal_economico_logo
        if hasattr(entry, 'media_content'):
            for media in entry.media_content:
                if 'url' in media:
                    url = process_url(media['url'])
                    return url
        if hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if 'url' in enclosure and 'type' in enclosure and enclosure['type'].startswith('image/'):
                    url = process_url(enclosure['url'])
                    return url
        for tag in ['image', 'img', 'post-thumbnail']:
            if tag in entry:
                value = entry.get(tag)
                if isinstance(value, dict) and 'url' in value:
                    url = process_url(value['url'])
                    return url
                elif isinstance(value, str):
                    url = process_url(value)
                    return url
        if hasattr(entry, 'content'):
            for content in entry.content:
                if 'value' in content:
                    match = re.search(r'<img\s+[^>]*src="([^"]+)"', content['value'])
                    if match:
                        url = process_url(match.group(1))
                        return url
        if hasattr(entry, 'description') and entry.description:
            if 'link' in entry and entry.link and "pplware" in entry.link:
                match = re.search(r'<img\s+[^>]*src="([^"]+)"', entry.description)
                if match:
                    url = process_url(match.group(1))
                    return url
            soup = BeautifulSoup(entry.description, 'html.parser')
            img = soup.find('img')
            if img and img.get('src'):
                url = process_url(img.get('src'))
                return url
        if 'link' in entry and entry.link:
            url = await get_image_url_from_link(entry.link, session)
            if url:
                url = process_url(url)
                return url
    except Exception as e:
        print(f"Error extracting image URL: {str(e)}")
    return None
    
def get_feed_domain(feed_url):
    return feed_url

def map_category(feed_category, feed_url, item_link=None):
    if isinstance(feed_url, dict):
        feed_url = feed_url.get("url", "")
    if feed_category in CATEGORY_MAPPER:
        return CATEGORY_MAPPER[feed_category]
    if "cmjornal.pt" in feed_url and item_link:
        parsed_url = urlparse(item_link)
        path_parts = parsed_url.path.strip("/").split("/")
        if path_parts:
            cm_category = path_parts[0].lower()
            cm_category = cm_category.capitalize()
            if cm_category in CATEGORY_MAPPER:
                return CATEGORY_MAPPER[cm_category]
            return "Outras Notícias"
    if "rr.sapo.pt" in feed_url and item_link and "/noticia/" in item_link:
        try:
            parsed_url = urlparse(item_link)
            path_parts = parsed_url.path.strip("/").split("/")
            if "noticia" in path_parts:
                index = path_parts.index("noticia")
                if index + 1 < len(path_parts):
                    rr_category = path_parts[index + 1].lower()
                    rr_category = rr_category.capitalize()
                    if rr_category in CATEGORY_MAPPER:
                        return CATEGORY_MAPPER[rr_category]
                    return rr_category
        except (ValueError, IndexError):
            pass
    for feed, category in FEED_CATEGORY_MAPPER.items():
        if feed_url.startswith(feed):
            return category
    return "Outras Notícias"

async def main():
    await get_articles()

if __name__ == "__main__":
    asyncio.run(main())
