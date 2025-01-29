import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import time
import json
import re
from html import unescape

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
    "https://caras.pt/feed/",
    "https://www.noticiasaominuto.com/rss/ultima-hora"
]

DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S"
]

FEED_CATEGORY_MAPPER = {
    "www.record.pt": "Desporto",
    "www.autosport.pt": "Desporto",
    "www.jornaleconomico.sapo.pt": "Economia",
    "www.jornaldenegocios.pt": "Economia"
}

CATEGORY_MAPPER = {
    "País": "Nacional",
    "Portugal": "Nacional",
    "Mundo": "Mundo",
    "Internacional": "Mundo",
    "Desporto": "Desporto",
    "Economia": "Economia",
    "Negócios": "Economia",
    "Cultura": "Cultura",
    "Tecnologia": "Tecnologia",
    "Ciência": "Tecnologia",
    "Sociedade": "Sociedade"
}

def get_articles():
    articles = []
    now = datetime.now(timezone.utc)
    last_24_hours = now - timedelta(days=1)

    for feed_url in RSS_FEEDS:
        attempts = 0
        while attempts < 3:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0"
                }
                response = requests.get(feed_url, headers=headers)
                response.raise_for_status()

                if not response.content.strip():
                    print(f"Conteúdo vazio para o feed {feed_url}")
                    break

                root = ET.fromstring(response.content)
                feed_domain = get_feed_domain(feed_url)

                for item in root.findall(".//item"):
                    title = clean_title(item.findtext("title", "").strip())
                    description = clean_description(item.findtext("description", "").strip())
                    pub_date_str = item.findtext("pubDate", "").strip()
                    source = extract_source(root)
                    category = map_category(item.findtext("category"), feed_domain)
                    image_url = extract_image_url(item)
                    
                    pub_date = parse_date(pub_date_str)
                    if pub_date and pub_date >= last_24_hours:
                        articles.append({
                            "title": title,
                            "description": description,
                            "image": image_url,
                            "source": source,
                            "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),
                            "category": category
                        })
                break
            except requests.exceptions.RequestException as e:
                print(f"Erro ao processar {feed_url}: {e}")
                break

    articles.sort(key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"), reverse=True)
    export_to_json(articles)

def export_to_json(articles):
    categorized_data = {"Últimas": articles}

    for category in ["Nacional", "Mundo", "Desporto", "Economia", "Cultura", "Tecnologia", "Sociedade"]:
        categorized_data[category] = [article for article in articles if article["category"] == category]

    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(categorized_data, f, ensure_ascii=False, indent=4)

def clean_title(title):
    if title.startswith("<![CDATA[") and title.endswith("]]>"):
        title = title[9:-3]
    return title.replace('\\"', "").replace("'", "").strip()

def clean_description(description):
    description = re.sub(r"<[^>]+>", "", description)
    description = unescape(description).replace('\\"', "").replace("'", "")
    return description[:200] + "..." if len(description) > 200 else description

def extract_source(root):
    channel_title = root.find(".//channel/title")
    if channel_title is not None:
        source_name = channel_title.text.strip()
        source_name = re.split(r" - | / ", source_name)[0]  # Remove tudo após " - " ou " / "
        return source_name
    return "Desconhecido"

def extract_image_url(item):
    for tag in ["media:content", "enclosure", "image", "img"]:
        element = item.find(tag)
        if element is not None and "url" in element.attrib:
            return element.attrib["url"]
    return None

def parse_date(date_str):
    if not date_str:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).astimezone(timezone.utc)
        except ValueError:
            continue
    return None

def get_feed_domain(feed_url):
    return feed_url.split("//")[-1].split("/")[0]

def map_category(feed_category, feed_domain):
    if feed_domain in FEED_CATEGORY_MAPPER:
        return FEED_CATEGORY_MAPPER[feed_domain]
    if feed_category in CATEGORY_MAPPER:
        return CATEGORY_MAPPER[feed_category]
    return "Outros"

if __name__ == "__main__":
    get_articles()
