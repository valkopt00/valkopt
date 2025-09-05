import json
import os
from datetime import datetime, timedelta, timezone
from groq import Groq

# Constantes
AI_CACHE_FILE = "ai_cache.json"
AI_PROCESSED_CACHE = {}

# Groq client
GROQ_CLIENT = None

def initialize_groq_client():
    """Initialize Groq client with API key"""
    global GROQ_CLIENT
    try:
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            print("⚠️ GROQ_API_KEY not found - AI classification disabled")
            return False
        GROQ_CLIENT = Groq(api_key=api_key)
        print("✅ Groq client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Error initializing Groq client: {e}")
        return False

def load_ai_cache():
    """Carrega o cache da AI de um ficheiro JSON"""
    try:
        if os.path.exists(AI_CACHE_FILE):
            with open(AI_CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                print(f"📋 Loaded AI cache with {len(cache_data)} entries")
                return cache_data
    except Exception as e:
        print(f"⚠️ Error loading AI cache: {e}")
    return {}

def save_ai_cache(cache_data):
    """Guarda o cache da AI num ficheiro JSON"""
    try:
        os.makedirs("articles", exist_ok=True)
        with open(AI_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ Error saving AI cache: {e}")

def cleanup_ai_cache():
    """Remove entradas do cache com mais de 5 dias"""
    global AI_PROCESSED_CACHE
    
    if not AI_PROCESSED_CACHE:
        return
        
    five_days_ago = datetime.now(timezone.utc) - timedelta(days=5)
    initial_count = len(AI_PROCESSED_CACHE)
    
    cleaned_cache = {}
    
    for url, entry in AI_PROCESSED_CACHE.items():
        # Se a entrada é só uma string (formato antigo), remover
        if isinstance(entry, str):
            continue
            
        # Se a entrada tem timestamp, verificar se é recente
        if isinstance(entry, dict) and "timestamp" in entry:
            try:
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if entry_time >= five_days_ago:
                    cleaned_cache[url] = entry
            except:
                continue
    
    if len(cleaned_cache) != initial_count:
        AI_PROCESSED_CACHE = cleaned_cache
        save_ai_cache(AI_PROCESSED_CACHE)
        print(f"🧹 AI cache cleaned: {initial_count} -> {len(cleaned_cache)} entries")

def categorize_with_ai(title, description, item_link=""):
    """
    Classify article using AI based on title, description, and URL.
    With persistent cache to avoid duplicate processing.
    """
    global AI_PROCESSED_CACHE
    
    if not GROQ_CLIENT:
        return None
    
    cache_key = item_link.strip()
    
    # Check cache first
    if cache_key in AI_PROCESSED_CACHE:
        cached_entry = AI_PROCESSED_CACHE[cache_key]
        
        if isinstance(cached_entry, str):
            cached_result = cached_entry
        elif isinstance(cached_entry, dict):
            cached_result = cached_entry.get("category")
        else:
            cached_result = None
            
        if cached_result:
            print(f"📋 Cache HIT: Using cached result '{cached_result}' for {item_link}")
            return cached_result
    
    categories = ["Nacional", "Mundo", "Desporto", "Economia", "Cultura", 
                  "Ciência e Tech", "Política", "Sociedade", "Lifestyle", 
                  "Multimédia", "Opinião", "Vídeojogos"]

    # Improved prompt with URL analysis
    prompt = f"""Classifica esta notícia portuguesa numa das categorias disponíveis.

ARTIGO:
Título: {title}
Descrição: {description}
URL: {item_link}

CATEGORIAS VÁLIDAS: {', '.join(categories)}

CRITÉRIOS DE CLASSIFICAÇÃO:
• Nacional: Eventos, políticas e assuntos nacionais de Portugal (exceto quando há foco político específico)
• Mundo: Notícias internacionais, conflitos globais, diplomacia, eventos fora de Portugal
• Desporto: Futebol, modalidades, competições, atletas, clubes, resultados desportivos
• Economia: Mercados, empresas, PIB, inflação, emprego, negócios, finanças, impostos
• Cultura: Arte, música, cinema, literatura, teatro, festivais, património, entretenimento cultural
• Ciência e Tech: Tecnologia, investigação científica, inovação, startups, IA, descobertas científicas
• Política: Governo português, parlamento, eleições, partidos políticos nacionais
• Sociedade: Saúde, educação, ambiente, justiça, direitos sociais, segurança pública
• Lifestyle: Moda, gastronomia, viagens, bem-estar, tendências, vida pessoal, famosos
• Multimédia: Conteúdo visual/áudio específico, podcasts, vídeos, fotogalerias
• Opinião: Editoriais, colunas de opinião, artigos de comentário, análises pessoais
• Vídeojogos: Gaming, indústria dos jogos, eSports, consolas, jogos digitais

PISTAS DO URL:
• Analisa o path do URL para identificar secções temáticas (ex: /desporto/, /economia/, /cultura/)
• Sites especializados: zerozero.pt, autosport.pt = Desporto; pplware.sapo.pt, tek.sapo.pt = Ciência e Tech
• Secções de opinião: /opiniao/, /editorial/, /coluna/ = Opinião
• Política internacional em sites portugueses = "Mundo", não "Política"

INSTRUÇÕES:
- Responde APENAS com o nome exato da categoria
- Se incerto, responde "Outras Notícias"
- Política internacional = "Mundo", não "Política"
- Considera o contexto português na classificação

Categoria:"""

    system_content = f"""You are a Portuguese news categorization system. Analyze the title, description, and URL provided and classify into ONE of these exact categories: {', '.join(categories)}.

Rules:
- Output ONLY the exact category name, nothing else
- If uncertain, output exactly: "Outras Notícias"  
- Do not provide explanations or additional text
- Consider Portuguese context for all classifications
- Use URL path clues (e.g., /desporto/, /economia/, domain specialization)
- Political news about other countries = "Mundo", not "Política"

You must respond with exactly one category name."""

    try:
        response = GROQ_CLIENT.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,  # More deterministic for classification
            max_tokens=20,    # Reduced - only need one word
            top_p=0.1        # More focused on most likely responses
        )

        ai_raw = response.choices[0].message.content.strip()
        
        # Clean possible extra formatting
        ai_clean = ai_raw.replace("Categoria:", "").replace("**", "").replace("*", "").strip()
        
        # Exact match first
        if ai_clean in categories:
            cache_entry = {
                "category": ai_clean,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "title": title[:100] + "..." if len(title) > 100 else title,
                "confidence": "exact"
            }
            AI_PROCESSED_CACHE[cache_key] = cache_entry
            save_ai_cache(AI_PROCESSED_CACHE)
            
            print(f"🤖 AI SUCCESS & CACHED (exact): '{ai_clean}' for {item_link}")
            return ai_clean
        
        # Case-insensitive check as fallback
        lower_clean = ai_clean.lower()
        for category in categories:
            if category.lower() == lower_clean:
                cache_entry = {
                    "category": category,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "title": title[:100] + "..." if len(title) > 100 else title,
                    "confidence": "case_insensitive"
                }
                AI_PROCESSED_CACHE[cache_key] = cache_entry
                save_ai_cache(AI_PROCESSED_CACHE)
                
                print(f"🤖 AI SUCCESS & CACHED (case fix): '{category}' for {item_link}")
                return category
        
        # Partial match as last resort (more restrictive)
        for category in categories:
            if len(ai_clean) > 3 and category.lower() in lower_clean and len(lower_clean) < len(category) + 5:
                cache_entry = {
                    "category": category,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "title": title[:100] + "..." if len(title) > 100 else title,
                    "confidence": "partial"
                }
                AI_PROCESSED_CACHE[cache_key] = cache_entry
                save_ai_cache(AI_PROCESSED_CACHE)
                
                print(f"🤖 AI SUCCESS & CACHED (partial): '{category}' from '{ai_clean}' for {item_link}")
                return category
        
        # If we reach here, invalid response
        print(f"⚠️ AI returned invalid category: '{ai_raw}' -> cleaned: '{ai_clean}'")
        
        # Cache failure to avoid unnecessary retry
        cache_entry = {
            "category": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": title[:100] + "..." if len(title) > 100 else title,
            "raw_response": ai_raw,
            "confidence": "failed"
        }
        AI_PROCESSED_CACHE[cache_key] = cache_entry
        save_ai_cache(AI_PROCESSED_CACHE)
        
        return None

    except Exception as e:
        print(f"❌ AI classification error: {e}")
        # Cache error to avoid immediate retry
        cache_entry = {
            "category": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": title[:100] + "..." if len(title) > 100 else title,
            "error": str(e),
            "confidence": "error"
        }
        AI_PROCESSED_CACHE[cache_key] = cache_entry
        save_ai_cache(AI_PROCESSED_CACHE)
        
        return None

def setup_ai_classifier():
    """Configura o classificador AI (chama no início do script principal)"""
    global AI_PROCESSED_CACHE
    
    if initialize_groq_client():
        print("✅ AI classifier initialized")
        AI_PROCESSED_CACHE = load_ai_cache()
        cleanup_ai_cache()
        return True
    else:
        print("⚠️ AI classifier not available")
        return False
