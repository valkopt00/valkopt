import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
import time
import json  # Importando para manipulação de arquivos JSON

app = FastAPI()

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

@app.get("/articles")
def get_articles():
    articles = []
    now = datetime.now(timezone.utc)
    last_24_hours = now - timedelta(days=1)

    for feed_url in RSS_FEEDS:
        attempts = 0
        while attempts < 3:  # Máximo de 3 tentativas
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
                }

                response = requests.get(feed_url, headers=headers)
                response.raise_for_status()
                
                # Verificar se a resposta está vazia
                if not response.content.strip():
                    print(f"Conteúdo vazio para o feed {feed_url}")
                    break

                root = ET.fromstring(response.content)
                
                for item in root.findall(".//item"):
                    title = clean_title(item.findtext("title", "").strip())  # Chama a função para limpar o título
                    description = clean_description(item.findtext("description", "").strip())
                    pub_date_str = item.findtext("pubDate", "").strip()
                    source = extract_source(root)
                    category = item.findtext("category")
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
                
                break  # Sai do loop se o pedido for bem-sucedido
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    attempts += 1
                    print(f"Erro 429 - Aguardando antes de tentar novamente (Tentativa {attempts})")
                    time.sleep(5 * attempts)  # Atraso progressivo
                elif response.status_code == 403:
                    print(f"Erro 403 - Acesso proibido ao feed {feed_url}")
                    break  # Sai do loop para este feed
                else:
                    print(f"Erro ao processar {feed_url}: {e}")
                    break  # Sai do loop se o erro não for 429 ou 403
            except Exception as e:
                print(f"Erro ao processar {feed_url}: {e}")
                break

    articles.sort(key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"), reverse=True)
    
    # Exportar para arquivo JSON
    export_to_json(articles)

    return {"articles": articles}

def export_to_json(data):
    """Função para exportar os dados para um arquivo JSON"""
    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def clean_title(title):
    # Verifica se o título contém a tag CDATA e remove o nó CDATA
    if title.startswith("<![CDATA[") and title.endswith("]]>"):
        title = title[9:-3]  # Remove a parte <![CDATA[ e ]]>
    return title.strip()  # Remove espaços extras no início e no final

def clean_description(description):
    import re
    from html import unescape
    
    description = re.sub(r"<[^>]+>", "", description)  # Remove HTML tags
    description = unescape(description)  # Decodifica entidades HTML
    return description[:200] + "..." if len(description) > 200 else description

def extract_source(root):
    channel_title = root.find(".//channel/title")
    return channel_title.text.strip() if channel_title is not None else "Desconhecido"

def extract_image_url(item):
    for tag in ["media:content", "enclosure", "image", "img"]:
        element = item.find(tag)
        if element is not None and "url" in element.attrib:
            image_url = element.attrib["url"]
            return image_url.replace("https://cdn.record.pt/images/https://cdn.record.pt/images/", "https://cdn.record.pt/images/")
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
