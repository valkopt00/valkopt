import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import json
import re
from html import unescape
from xml.etree.ElementTree import Element


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
    "https://pt.euronews.com/rss?format=mrss&level=theme&name=news",
    "https://www.noticiasaominuto.com/rss/ultima-hora"
]

DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S"
]

FEED_CATEGORY_MAPPER = {
    "https://www.record.pt/rss": "Desporto",
    "https://www.autosport.pt/feed": "Desporto",
    "https://www.zerozero.pt/rss/noticias.php": "Desporto",
    "https://www.noticiasaominuto.com/rss/desporto": "Desporto",
    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=2": "Desporto",
    "https://pt.euronews.com/rss?format=mrss&level=theme&name=sport": "Desporto",
    
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
    "https://pt.euronews.com/rss?format=mrss&level=vertical&name=my-europe": "Mundo",

    "https://www.noticiasaominuto.com/rss/cultura": "Cultura",
    "https://www.rtp.pt/noticias/rss/cultura": "Cultura",
    "https://pt.euronews.com/rss?format=mrss&level=vertical&name=culture": "Cultura",

    "https://www.noticiasaominuto.com/rss/tech": "Tecnologia",
    "https://pt.euronews.com/rss?format=mrss&level=vertical&name=next": "Tecnologia",

    "https://www.noticiasaominuto.com/rss/fama": "Sociedade",
    "https://www.noticiasaominuto.com/rss/lifestyle": "Sociedade",
    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=89": "Sociedade",
    "https://pt.euronews.com/rss?format=mrss&level=vertical&name=travel": "Sociedade"
}

CATEGORY_MAPPER = {
    "Nacional": "Nacional",
    "País": "Nacional",
    "Portugal": "Nacional",
    "Mundo": "Mundo",
    "Internacional": "Mundo",
    "União Europeia": "Mundo",
    "Médio Oriente": "Mundo",
    "Faixa de Gaza": "Mundo",
    "EUA": "Mundo",
    "Desporto": "Desporto",
    "Economia": "Economia",
    "Negócios": "Economia",
    "Segurança Social": "Economia",
    "Bolsa e Mercados": "Economia",
    "Energia": "Economia",
    "Cultura": "Cultura",
    "Livros": "Cultura",
    "Blitz": "Cultura",
    "Tecnologia": "Tecnologia",
    "Ciência": "Tecnologia",
    "Exame Informática": "Tecnologia",
    "Sociedade": "Sociedade",
    "Coronavírus": "Sociedade",
    "Mau tempo": "Sociedade",
    "Comer e beber": "Sociedade",
    "Insólitos": "Sociedade",
    "Meteorologia": "Sociedade",
    "Saúde": "Sociedade",
    "Clima": "Sociedade",
    "Política": "Política",
    "Defesa": "Política",
    "Partidos": "Política",
    "Outras Notícias": "Outras Notícias"
}

def get_articles():
    articles = []
    now = datetime.now(timezone.utc)
    last_24_hours = now - timedelta(days=1)

    for feed_url in RSS_FEEDS:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(feed_url, headers=headers)
            response.raise_for_status()

            if not response.content.strip():
                print(f"Conteúdo vazio para o feed {feed_url}")
                continue

            root = ET.fromstring(response.content)
            feed_domain = get_feed_domain(feed_url)

            for item in root.findall(".//item"):
                title = clean_title(item.findtext("title", "").strip())
                description = clean_description(item.findtext("description", "").strip())
                pub_date_str = item.findtext("pubDate", "").strip()
                source = extract_source(root)
                category = map_category(item.findtext("category"), feed_domain)
                image_url = extract_image_url(item)
                link = item.findtext("link", "").strip()  # Adiciona a extração do link

                pub_date = parse_date(pub_date_str)
                if pub_date and pub_date >= last_24_hours:
                    articles.append({
                        "title": title,
                        "description": description,
                        "image": image_url,
                        "source": source,
                        "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),
                        "category": category,
                        "link": link  # Adiciona o link ao dicionário
                    })
        except requests.exceptions.RequestException as e:
            print(f"Erro ao processar {feed_url}: {e}")

    articles.sort(key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"), reverse=True)
    export_to_json(articles)

def export_to_json(articles):
    categorized_data = {"Últimas": articles}

    for category in ["Nacional", "Mundo", "Desporto", "Economia", "Cultura", "Tecnologia", "Sociedade", "Política", "Outras Notícias"]:
        categorized_data[category] = [article for article in articles if article["category"] == category]

    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(categorized_data, f, ensure_ascii=False, indent=4)

def clean_title(title):
    """ Corrige títulos dentro de CDATA e remove caracteres desnecessários. """
    if title.startswith("<![CDATA[") and title.endswith("]]>"):
        title = title[9:-3]  # Remove CDATA
    return title.strip()

def clean_description(description):
    """ Remove HTML, caracteres de escape e limita a 200 caracteres sem cortar palavras. """
    description = unescape(description)  # Remove caracteres HTML escapados
    description = re.sub(r"<[^>]+>", "", description)  # Remove tags HTML
    description = description.replace('\"', "").replace("\n", " ")  # Remove \"
    description = description.strip()

    # Limita a 230 caracteres, garantindo que não corta palavras
    if len(description) > 230:
        description = description[:230].rsplit(' ', 1)[0] + "..."
    
    return description

def extract_source(root):
    """ Extrai a fonte e remove sufixos indesejados. """
    channel_title = root.find(".//channel/title")
    if channel_title is not None:
        source_name = channel_title.text.strip()
        source_name = re.split(r" - | / ", source_name)[0]  # Remove tudo após " - " ou " / "
        return source_name
    return "Desconhecido"

def extract_image_url(item: Element):
    """Procura uma imagem válida no RSS, corrige URLs duplicados e extrai imagens da <description>.
       Se o link for do Jornal Económico, define uma imagem padrão.
    """
    namespaces = {"media": "http://search.yahoo.com/mrss/"}  # Namespace comum para media:content
    jornal_economico_logo = "https://leitor.jornaleconomico.pt/assets/uploads/artigos/JE_logo.png"

    # Verifica se o link é do Jornal Económico
    link_element = item.find("link")
    if link_element is not None and link_element.text and "jornaleconomico" in link_element.text:
        return jornal_economico_logo

    # Verifica nas tags principais (media:content, enclosure, image, img, post-thumbnail)
    for tag in ["media:content", "enclosure", "image", "img", "post-thumbnail"]:
        element = item.find(tag, namespaces)  # Passa namespaces para garantir que encontra media:content
        if element is not None:
            # Verifica se a tag tem atributo 'url'
            if tag == "post-thumbnail" and element.find("url") is not None:
                url = element.find("url").text
            elif "url" in element.attrib:
                url = element.attrib["url"]

            # Substitui a versão 100x100 pela versão maior 932x621
            if "100x100" in url:
                url = url.replace("100x100", "932x621")

            # Corrigir URLs duplicados no caso específico do Record
            if url.startswith("https://cdn.record.pt/images/https://cdn.record.pt/images/"):
                return url.replace("https://cdn.record.pt/images/", "", 1)
            
            return url  # Retorna o URL normal se não precisar de correção

    # Se não encontrou imagem nas tags principais, verifica dentro do <content:encoded>
    content_encoded = item.find("content:encoded")
    if content_encoded is not None and content_encoded.text:
        match = re.search(r'<img\s+[^>]*src="([^"]+)"', content_encoded.text)
        if match:
            return match.group(1)

    # Se ainda não encontrou imagem, tenta dentro da <description>
    description = item.find("description")
    if description is not None and description.text:
        match = re.search(r'<img\s+src="([^"]+)"', description.text)
        if match:
            return match.group(1)

    return None  # Retorna None se não encontrar uma imagem

def parse_date(date_str):
    """ Converte a data do RSS para datetime. """
    if not date_str:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).astimezone(timezone.utc)
        except ValueError:
            continue
    return None

def get_feed_domain(feed_url):
    """ Extrai a URL completa do feed RSS. """
    return feed_url

def map_category(feed_category, feed_url):
    """ Determina a categoria da notícia. """
    # Primeiro verifica se a URL completa do feed está no mapeamento
    for feed, category in FEED_CATEGORY_MAPPER.items():
        if feed_url.startswith(feed):  # Verifica se a URL do feed começa com a URL mapeada
            return category

    # Se não encontrou no mapeamento de feed completo, verifica pelo nome da categoria
    if feed_category in CATEGORY_MAPPER:
        return CATEGORY_MAPPER[feed_category]

    return "Outras Notícias"


if __name__ == "__main__":
    get_articles()
