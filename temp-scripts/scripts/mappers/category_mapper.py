from urllib.parse import urlparse

from scripts.core import utils
from scripts.mappers.mappings import FEED_CATEGORY_MAPPER, CATEGORY_MAPPER

# Global variable to hold normalized mappings
NORMALIZED_SUBCATEGORY_TO_MAIN = {}

def create_normalized_category_mappings():
    """Create normalized mappings from the CATEGORY_MAPPER"""
    global NORMALIZED_SUBCATEGORY_TO_MAIN
    
    normalized_to_main = {}
    
    # Handle the inverted structure from mappings.py
    for alias, main_category in CATEGORY_MAPPER.items():
        normalized_alias = utils.normalize_text(alias)
        normalized_to_main[normalized_alias] = main_category
        
        # Also add the main category itself
        normalized_main = utils.normalize_text(main_category)
        if normalized_main not in normalized_to_main:
            normalized_to_main[normalized_main] = main_category
    
    NORMALIZED_SUBCATEGORY_TO_MAIN = normalized_to_main
    return normalized_to_main

def map_category(feed_category, feed_url, item_link=None, title="", description=""):
    """
    FIXED: Map the provided feed category and URL to a standardized category using
    the CATEGORY_MAPPER and FEED_CATEGORY_MAPPER. Uses normalized lookups.
    Enhanced with better AI integration and logging.
    """
    # Ensure normalized mappings are initialized
    if not NORMALIZED_SUBCATEGORY_TO_MAIN:
        create_normalized_category_mappings()
    
    if isinstance(feed_url, dict):
        feed_url = feed_url.get("url", "") or ""

    # normalize feed_category early
    feed_cat_norm = utils.normalize_text(feed_category or "")
    
    # --- Special cases based on the article URL (item_link) ---
    if item_link:
        parts = urlparse(item_link).path.strip("/").split("/")

        # Público: look for three numeric segments (year/month/day) and use the next segment as category
        if "publico.pt" in item_link:
            for i in range(len(parts) - 3):
                if (parts[i].isdigit() and len(parts[i]) == 4 and
                    parts[i+1].isdigit() and len(parts[i+1]) == 2 and
                    parts[i+2].isdigit() and len(parts[i+2]) == 2 and
                    i+3 < len(parts)):
                    candidate = parts[i+3]
                    mapped = find_category_in_mapper(candidate)
                    if mapped:
                        return mapped
                    break

        # Expresso: only override if not a supplement path (/semanario)
        if "expresso.pt" in item_link:
            if parts and parts[0] != "semanario":
                candidate = parts[0]
                mapped = find_category_in_mapper(candidate)
                if mapped:
                    return mapped

        # Visão: use the first segment after the domain
        if "visao.pt" in item_link:
            if parts and parts[0]:
                candidate = parts[0]
                mapped = find_category_in_mapper(candidate)
                if mapped:
                    return mapped

    # --- Direct mapping by feed URL prefix (FEED_CATEGORY_MAPPER) ---
    for feed_prefix, default_category in FEED_CATEGORY_MAPPER.items():
        if (feed_url or "").startswith(feed_prefix):
            # Try to map the default_category itself to a main category
            mapped = find_category_in_mapper(default_category)
            if mapped:
                return mapped
            # Return the default category directly if it's valid
            if default_category in ["Últimas", "Nacional", "Mundo", "Desporto", "Economia", 
                                  "Cultura", "Ciência e Tech", "Lifestyle", "Sociedade", 
                                  "Política", "Multimédia", "Opinião", "Vídeojogos"]:
                return default_category
            break

    # --- Map feed category using the fixed mapper structure ---
    if feed_cat_norm:
        mapped = find_category_in_mapper(feed_cat_norm)
        if mapped:
            return mapped

    # --- CM Jornal special case ---
    if "cmjornal.pt" in (feed_url or "") and item_link:
        parsed = urlparse(item_link)
        cm_parts = parsed.path.strip("/").split("/")
        if cm_parts:
            candidate = cm_parts[0]
            mapped = find_category_in_mapper(candidate)
            if mapped:
                return mapped

    # --- Renascença rr.sapo.pt special case ---
    if "rr.sapo.pt" in (feed_url or "") and item_link and "/noticia/" in item_link:
        try:
            parsed = urlparse(item_link)
            rr_parts = parsed.path.strip("/").split("/")
            idx = rr_parts.index("noticia")
            if idx + 1 < len(rr_parts):
                candidate = rr_parts[idx+1]
                mapped = find_category_in_mapper(candidate)
                if mapped:
                    return mapped
        except ValueError:
            pass
        
    # --- Renascença rr.pt special case ---
    if "rr.pt" in item_link:
        try:
            parsed = urlparse(item_link)
            rr_parts = parsed.path.strip("/").split("/")
            
            if len(rr_parts) >= 2:
                candidate = rr_parts[1] # second segment
                mapped = find_category_in_mapper(candidate)

                if mapped:
                    return mapped
                    
        except (ValueError, IndexError):
            pass

    # --- AI Classification for unmapped articles ---
    # Call AI if we have content (title/description) regardless of feed_category
    if (title or description):
        print(f"🤖 Calling AI for unmapped article: '{title}'")
        
        try:
            from scripts import ai_classifier
            ai_category = ai_classifier.categorize_with_ai(
                title=title or "Sem título", 
                description=description or "Sem descrição", 
                item_link=item_link or ""
            )

            if ai_category:
                print(f"🤖 AI SUCCESS: '{feed_category or 'no-category'}' -> '{ai_category}' | {item_link}")
                return ai_category
            else:
                print(f"🤖 AI FAILED: Could not classify '{title}...' | {item_link}")
        except ImportError:
            print("⚠️ AI classifier not available, skipping AI classification")
        except Exception as e:
            print(f"⚠️ Error in AI classification: {e}")
   
    # --- Debug: Log unmapped categories ---
    if feed_category and feed_category.strip():
        print(f"⚠️ UNMAPPED: raw='{feed_category}' normalized='{feed_cat_norm}' | {item_link}")
    else:
        print(f"⚠️ NO CATEGORY: empty feed_category | {item_link}")

    # --- Fallback to "Outras Notícias" ---
    print(f"💡 FALLBACK to 'Outras Notícias' | {item_link}")
    return "Outras Notícias"

def find_category_in_mapper(category_to_find):
    """
    Fast lookup using a precomputed normalized -> main_category map.
    Returns main category or None.
    """
    if not category_to_find:
        return None
    
    # Ensure mappings are initialized
    if not NORMALIZED_SUBCATEGORY_TO_MAIN:
        create_normalized_category_mappings()
        
    return NORMALIZED_SUBCATEGORY_TO_MAIN.get(utils.normalize_text(category_to_find))