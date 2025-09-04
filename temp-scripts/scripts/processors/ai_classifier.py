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
    Classify article using AI based on title and description + URL.
    Com cache persistente para evitar processamento duplicado.
    """
    global AI_PROCESSED_CACHE
    
    if not GROQ_CLIENT:
        return None
    
    cache_key = item_link.strip()
    
    # Verificar cache
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

    prompt = f"""Analisa este título e descrição de notícia portuguesa e classifica na categoria mais adequada.

    Título: {title}
    Descrição: {description}
    URL do artigo: {item_link}

    Categorias disponíveis: {', '.join(categories)}

    Regras:
    - Responde APENAS com o nome exato da categoria (uma das opções acima), sem pontuação, explicações ou texto adicional.
    - Se não tiveres certeza, responde "Outras Notícias".
    - Para a categoria "Política", apenas política de Portugal. Política internacional usa "Mundo". 

    - "Mundo": Notícias internacionais, conflitos externos, política externa, eventos fora de Portugal
    - "Desporto": Futebol, outros desportos, competições, atletas, clubes desportivos
    - "Economia": Mercados financeiros, empresas, inflação, PIB, impostos, salários, emprego, negócios
    - "Cultura": Arte, música, cinema, teatro, literatura, festivais, património cultural
    - "Ciência e Tech": Tecnologia, investigação científica, inovação, startups tech, IA, ciência
    - "Política": Eleições, partidos políticos, parlamento, governo (quando foco político específico)
    - "Sociedade": Saúde, educação, direitos sociais, ambiente, segurança pública, justiça
    - "Lifestyle": Moda, gastronomia, viagens, bem-estar, tendências, vida pessoal
    - "Multimédia": Conteúdo visual/áudio específico, galeria de fotos, vídeos especiais
    - "Opinião": Artigos de opinião, editoriais, colunas, comentários
    - "Vídeojogos": Gaming, indústria dos jogos, eSports, consolas

    Resposta esperada (EXACT): <Nome da categoria>
    """

    system_content = (
        "You are a strict category classifier. Given the user's input, output EXACTLY ONE of the "
        "following category names, nothing else: " + ", ".join(categories) +
        ". If you are unsure, output exactly: Outras Notícias. Do NOT ask for more info, do NOT output "
        "explanations or other sentences."
    )

    try:
        response = GROQ_CLIENT.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=50
        )

        ai_raw = response.choices[0].message.content.strip()
        
        if ai_raw in categories:
            cache_entry = {
                "category": ai_raw,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "title": title[:100] + "..." if len(title) > 100 else title
            }
            AI_PROCESSED_CACHE[cache_key] = cache_entry
            save_ai_cache(AI_PROCESSED_CACHE)
            
            print(f"🤖 AI SUCCESS & CACHED: '{ai_raw}' for {item_link}")
            return ai_raw

        lower = ai_raw.lower()
        for c in categories:
            if c.lower() in lower:
                cache_entry = {
                    "category": c,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "title": title[:100] + "..." if len(title) > 100 else title
                }
                AI_PROCESSED_CACHE[cache_key] = cache_entry
                save_ai_cache(AI_PROCESSED_CACHE)
                
                print(f"🤖 AI SUCCESS & CACHED: '{c}' for {item_link}")
                return c

        print(f"⚠️ AI returned invalid category: {ai_raw}")
        return None

    except Exception as e:
        print(f"❌ AI classification error: {e}")
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