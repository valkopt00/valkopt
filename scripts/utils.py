import re
import unicodedata
from datetime import datetime
from html import unescape
from urllib.parse import urlparse
from dateutil import parser, tz

from scripts.mappings import DATE_FORMATS

# Normalize text
def normalize_text(text):
    """
    Normalizes text by removing accents, converting to lowercase,
    removing punctuation and extra spaces.
    
    Args:
        text: String to be normalized
        
    Returns:
        Normalized string for search
    """
    if not text:
        return ""
    
    # Remove accents (NFD decomposition + removal of diacritical marks)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # Lowercase and remove punctuation (keep only letters, numbers, and spaces)
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    return text

def fix_encoding(text):
    """
    Fix only when common double-encoding artifacts are detected.
    """
    # Typical patterns of bad decoding: "ÃƒÆ'Ã‚Â©", "ÃƒÆ'Ã‚Â¡", "ÃƒÆ'Ã‚Âª", "ÃƒÆ'Ã‚Â£", etc.
    if not re.search(r"[ÃƒÆ'Ãƒâ€š][Ã‚Â©Ã‚ÂªÃ‚Â¢Ã‚Â±Ã‚ÂºÃ‚Â«Ã‚Â°]", text):
        return text  # Looks fine, don't touch
    
    try:
        return text.encode('latin1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
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
            source_name_lower = source_name.lower()

            # Check for specific sources first (before any normalization)
            if "tek" in source_name_lower and "notícias" in source_name_lower:
                return "SAPO Tek"
            elif "sapo" in source_name_lower:
                return "SAPO"
            elif "rtp" in source_name_lower:
                return "RTP Notícias"
            elif "notícias ao minuto" in source_name_lower:
                return "Notícias ao Minuto"
            elif "renascença" in source_name_lower:
                return "Renascença"
            elif source_name.upper() == "PÚBLICO":
                return "Público"
            elif source_name == "News | Euronews RSS":
                return "Euronews"
            elif source_name == "Notícias zerozero.pt":
                return "zerozero.pt"
            elif source_name == "Eurogamer.pt Latest Articles Feed":
                return "Eurogamer"
            elif "jornal i" in source_name_lower:
                return "Jornal i"
            elif "jornal de negocios" in source_name_lower:
                return "Jornal de Negócios"
            elif "correio da manhã" in source_name_lower:
                return "Correio da Manhã"
            
            # Normalize capitalization for other cases
            return source_name.title()
            
        elif isinstance(data, str):
            parsed = urlparse(data)
            domain = parsed.netloc.lower().removeprefix('www.')

            # Check for specific URLs
            if data.startswith("https://www.noticiasaominuto.com"):
                return "Notícias ao Minuto"
            elif data.startswith("https://www.rtp.pt/"):
                return "RTP Notícias"
            elif "tek.sapo.pt" in domain:
                return "SAPO Tek"

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
                'tek': 'SAPO Tek',
            }
            return source_mapping.get(domain, domain)
    except Exception as e:
        print(f"Error extracting source: {e}")
    return "Desconhecido"

def parse_date(date_str, source_url=None):
    """
    Parse publication date from various formats.
    
    Args:
        date_str: Date string to parse
        source_url: URL of the RSS feed (for RTP and Euronews correction)
        
    Returns:
        Datetime object with corrected timezone or None if parsing fails
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
    
    parsed_dt = None
    
    # Try each format until one works
    for fmt in all_formats:
        try:
            parsed_dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    
    # If all formats fail, try a more flexible approach
    if parsed_dt is None:
        try:
            parsed_dt = parser.parse(date_str)
        except:
            print(f"Warning: Failed to parse date: {date_str}")
            return None
    
    # Add timezone if missing
    if parsed_dt.tzinfo is None:
        portugal_tz = tz.gettz('Europe/Lisbon')
        parsed_dt = parsed_dt.replace(tzinfo=portugal_tz)
    
    # Convert to Portugal timezone FIRST, then apply any specific corrections
    portugal_tz = tz.gettz('Europe/Lisbon')
    
    parsed_dt = parsed_dt.astimezone(portugal_tz)
    
    # Apply specific source corrections AFTER converting to Portugal timezone
    if source_url:
        # Convert set to string if necessary
        if isinstance(source_url, set):
            source_url = next(iter(source_url)) if source_url else None
        
        if source_url:
            from datetime import timedelta
            if 'rtp.pt' in source_url.lower():
                parsed_dt = parsed_dt - timedelta(hours=1)
           
    return parsed_dt

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

def get_feed_domain(feed_url):
    """
    Returns the feed URL as is (placeholder function for future domain processing if needed).
    """
    return feed_url