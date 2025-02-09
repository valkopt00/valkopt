import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import json
import re
from html import unescape
from xml.etree.ElementTree import Element
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import base64
from io import BytesIO
from PIL import Image

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

    "https://www.noticiasaominuto.com/rss/fama": "Sociedade",
    "https://www.noticiasaominuto.com/rss/lifestyle": "Sociedade",
    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=89": "Sociedade",
    "https://pt.euronews.com/rss?format=mrss&level=vertical&name=green": "Sociedade",
    "https://pt.euronews.com/travel": "Sociedade",

    "https://www.rtp.pt/noticias/rss/videos": "Multimédia",
    "https://www.rtp.pt/noticias/rss/audios": "Multimédia",

    "https://caras.pt/feed/": "Lifestyle",

    "https://rr.sapo.pt/rss/rssfeed.aspx?fid=71": "Opinião"
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
    "Diplomacia": "Mundo",
    "EUA": "Mundo",
    "Desporto": "Desporto",
    "Futebol Nacional": "Desporto",
    "Futebol Internacional": "Desporto",
    "Economia": "Economia",
    "Negócios": "Economia",
    "Segurança Social": "Economia",
    "Bolsa e Mercados": "Economia",
    "Energia": "Economia",
    "Cultura": "Cultura",
    "Livros": "Cultura",
    "Blitz": "Cultura",
    "Ciência e Tech": "Ciência e Tech",
    "Ciência & Tech": "Ciência e Tech",
    "Ciência": "Ciência e Tech",
    "Tech": "Ciência e Tech",
    "Exame Informática": "Ciência e Tech",
    "Sociedade": "Sociedade",
    "Coronavírus": "Sociedade",
    "Mau tempo": "Sociedade",
    "Insólitos": "Sociedade",
    "Meteorologia": "Sociedade",
    "Saúde": "Sociedade",
    "Clima": "Sociedade",
    "Justiça": "Sociedade",
    "Política": "Política",
    "Defesa": "Política",
    "Parlamento": "Política",
    "Partidos": "Política",
    "Multimédia": "Multimédia",
    "Fotogaleria": "Multimédia",
    "O Mundo a Seus Pés": "Multimédia",
    "Contas Poupança": "Multimédia",
    "O CEO é o limite": "Multimédia",
    "Expresso da Manhã": "Multimédia",
    "Isto É Gozar Com Quem Trabalha": "Multimédia",
    "Ana Gomes": "Multimédia",
    "Noticiários Desporto": "Multimédia",
    "Minuto Consumidor": "Multimédia",
    "Noticiário Antena1": "Multimédia",
    "Leste Oeste de Nuno Rogeiro": "Multimédia",
    "Vídeos": "Multimédia",
    "Opinião": "Opinião",
    "Lifestyle": "Lifestyle",
    "Comer e beber": "Lifestyle",
    "Gastronomia": "Lifestyle",
    "Vidas": "Lifestyle",
    "Fama": "Lifestyle",
    "Ideias": "Lifestyle",
    "Outras Notícias": "Outras Notícias"
}

def get_articles():
    articles = []
    now = datetime.now(timezone.utc)
    last_12_hours = now - timedelta(hours=12)
    last_48_hours = now - timedelta(days=2)
    titles_seen = set()

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
                if title in titles_seen:
                    continue  # Se o título já foi processado, ignora                
                titles_seen.add(title)  # Adiciona o título ao conjunto para evitar duplicados

                description = clean_description(item.findtext("description", "").strip())
                pub_date_str = item.findtext("pubDate", "").strip()
                source = extract_source(root)
                category = map_category(item.findtext("category"), feed_domain)
                image_url = extract_image_url(item)
                link = item.findtext("link", "").strip()  # Adiciona a extração do link

                pub_date = parse_date(pub_date_str)

                if pub_date:
                    # Para a categoria "Últimas", considerar apenas as notícias das últimas 12 horas
                    if category == "Últimas" and pub_date >= last_12_hours:
                        articles.append({
                            "title": title,
                            "description": description,
                            "image": image_url,
                            "source": source,
                            "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),
                            "category": category,
                            "link": link
                        })
                    # Para todas as outras categorias, considerar as notícias das últimas 48 horas
                    elif category != "Últimas" and pub_date >= last_48_hours:
                        articles.append({
                            "title": title,
                            "description": description,
                            "image": image_url,
                            "source": source,
                            "pubDate": pub_date.strftime("%d-%m-%Y %H:%M"),
                            "category": category,
                            "link": link
                        })
        except requests.exceptions.RequestException as e:
            print(f"Erro ao processar {feed_url}: {e}")

    articles.sort(key=lambda x: datetime.strptime(x["pubDate"], "%d-%m-%Y %H:%M"), reverse=True)
    export_to_json(articles)

def export_to_json(articles):
    categorized_data = {"Últimas": articles}

    for category in ["Nacional", "Mundo", "Desporto", "Economia", "Cultura", "Ciência e Tech", "Lifestyle", 
                     "Sociedade", "Política", "Multimédia", "Opinião", "Outras Notícias"]:
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
    if len(description) > 150:
        description = description[:230].rsplit(' ', 1)[0] + "..."
    
    return description

def extract_source(root):
    """ Extrai a fonte e remove sufixos indesejados. """
    channel_title = root.find(".//channel/title")
    if channel_title is not None:
        source_name = channel_title.text.strip()
        if source_name == "News | Euronews RSS":
            return "Euronews"
        if source_name == "Notícias zerozero.pt":
            return "zerozero.pt"
        source_name = re.split(r" - | / ", source_name)[0]  # Remove tudo após " - " ou " / "
        return source_name
    return "Desconhecido"

def get_image_url_from_link(news_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(news_url, headers=headers)
    if response.status_code != 200:
        print(f"Erro ao acessar a página: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    # Primeiro, tentamos encontrar a imagem principal (wp-post-image)
    image_tag = soup.find('img', class_='wp-post-image')

    # Se não encontrar, buscamos qualquer imagem dentro de um bloco de capa (cover image)
    if not image_tag:
        image_tag = soup.find('img', class_='wp-block-cover__image-background')

    # Se ainda não encontrou, buscamos qualquer <img> na página
    if not image_tag:
        image_tags = soup.find_all('img')
        for img in image_tags:
            image_url = img.get('data-src') or img.get('src')
            if image_url and image_url.startswith("https://ionline.sapo.pt/wp-content/uploads/"):
                return image_url
    
    # Se encontrou a tag, extrai a URL
    if image_tag:
        image_url = image_tag.get('data-src') or image_tag.get('src')
        if image_url and image_url.startswith("https://ionline.sapo.pt/wp-content/uploads/"):
            return image_url

    print("Nenhuma imagem correspondente encontrada.")
    return None

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
        if element is None:
            # Tenta sem namespaces caso a tag não esteja no namespace fornecido
            element = item.find(tag)

        if element is not None:
            # Verifica se a tag tem atributo 'url'
            url = None
            if tag == "post-thumbnail" and element.find("url") is not None:
                url = element.find("url").text

def convert_image_to_webp_base64(image_url, quality=80):
    """
    Baixa a imagem do URL, converte para WebP com a qualidade definida e codifica em base64.
    Retorna uma string do tipo "data:image/webp;base64,<dados>".
    """
    response = requests.get(image_url)
    response.raise_for_status()  # Levanta exceção se houver erro
    img = Image.open(BytesIO(response.content))
    output = BytesIO()
    img.save(output, format='WEBP', quality=quality)
    webp_data = output.getvalue()
    base64_str = base64.b64encode(webp_data).decode('utf-8')
    return "data:image/webp;base64," + base64_str

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
        element = item.find(tag, namespaces)  # Tenta com namespace
        if element is None:
            element = item.find(tag)          # Tenta sem namespace

        if element is not None:
            url = None
            if tag == "post-thumbnail" and element.find("url") is not None:
                url = element.find("url").text
            elif "url" in element.attrib:
                url = element.attrib["url"]

            if url:
                # Substitui a versão 100x100 pela versão maior 932x621
                if "100x100" in url:
                    url = url.replace("100x100", "932x621")
                # Substitui a versão 932x621 pela versão maior 900x560 para o jornal de negócios
                if "932x621" in url and "jornaldenegocios" in url:
                    url = url.replace("932x621", "900x560")
                # Corrigir URLs duplicados no caso específico do Record
                if url.startswith("https://cdn.record.pt/images/https://cdn.record.pt/images/"):
                    url = url.replace("https://cdn.record.pt/images/", "", 1)
                try:
                    return convert_image_to_webp_base64(url)
                except Exception as e:
                    # Se houver erro na conversão, retorna o URL original
                    return url

    # Se não encontrou imagem nas tags principais, verifica dentro do <content:encoded>
    content_encoded = item.find("content:encoded")
    if content_encoded is not None and content_encoded.text:
        match = re.search(r'<img\s+[^>]*src="([^"]+)"', content_encoded.text)
        if match:
            try:
                return convert_image_to_webp_base64(match.group(1))
            except Exception as e:
                return match.group(1)

    # Se ainda não encontrou imagem, tenta dentro da <description>
    description = item.find("description")
    if description is not None and description.text:
        # Se a fonte for o Pplware, extrai a imagem da descrição
        link_element = item.find("link")
        if link_element is not None and link_element.text and "pplware" in link_element.text:
            match = re.search(r'<img\s+[^>]*src="([^"]+)"', description.text)
            if match:
                try:
                    return convert_image_to_webp_base64(match.group(1))
                except Exception as e:
                    return match.group(1)
        match = re.search(r'<img\s+src="([^"]+)"', description.text)
        if match:
            try:
                return convert_image_to_webp_base64(match.group(1))
            except Exception as e:
                return match.group(1)

    # Se ainda não encontrou imagem, tenta buscar no link da notícia
    if link_element is not None and link_element.text:
        image_url = get_image_url_from_link(link_element.text)
        if image_url:
            try:
                return convert_image_to_webp_base64(image_url)
            except Exception as e:
                return image_url

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

def map_category(feed_category, feed_url, item_link=None):
    # Exceção para o CM Jornal: extrai a categoria do link da notícia (item_link)
    if "cmjornal.pt" in feed_url and item_link:
        parsed_url = urlparse(item_link)
        path_parts = parsed_url.path.strip("/").split("/")
        if path_parts:  # Se houver pelo menos um segmento na URL
            cm_category = path_parts[0].lower()
            # Aplica o CATEGORY_MAPPER à categoria extraída
            if cm_category in CATEGORY_MAPPER:
                return CATEGORY_MAPPER[cm_category]
            return cm_category.capitalize()  # Retorna a categoria formatada se não houver mapeamento

    # Lógica original para outros feeds
    if feed_category:  # Verifica se feed_category não é None
        category = feed_category.capitalize()  # Formata a categoria do feed
    else:
        category = "Outras Notícias"  # Categoria padrão se feed_category for None

    # Verifica se a URL completa do feed está no mapeamento
    for feed, mapped_category in FEED_CATEGORY_MAPPER.items():
        if feed_url.startswith(feed):  # Verifica se a URL do feed começa com a URL mapeada
            return mapped_category

    # Se não encontrou no mapeamento de feed completo, verifica pelo nome da categoria
    if feed_category in CATEGORY_MAPPER:
        return CATEGORY_MAPPER[feed_category]

    return category  # Retorna a categoria formatada ou "Outras Notícias"

if __name__ == "__main__":
    get_articles()
