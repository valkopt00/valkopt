# List of RSS feed URLs to fetch news from Portuguese news sources
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
    "https://tek.sapo.pt/rss",
    "https://www.sapo.pt/rss",
    "https://caras.pt/feed/"
]

# API sources that don't provide RSS feeds but have JSON endpoints
API_SOURCES = [
    {
        "url": "https://observador.pt/wp-json/obs_api/v4/news/widget",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "source_name": "Observador"
    }
]

# Maps feed URLs to predefined categories
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
    "https://tek.sapo.pt/rss": "Ciência e Tech",

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

# Maps specific category names to standardized category names
CATEGORY_GROUPS = {
    "Nacional": [
        "Nacional", "País", "Pais", "Portugal"
    ],
    "Mundo": [
        "Mundo", "Internacional", "União Europeia", "Guerra na Ucrânia",
        "Guerra no médio oriente", "Médio Oriente", "My-europe",
        "África", "Europa", "A guerra na Síria", "Guerra israel-hamas",
        "Faixa de Gaza", "Guerra no Médio Oriente", "Alemanha",
        "Diplomacia", "EUA", "Público Brasil", "Brasil", "Israel", "Reino Unido",
        "Turquia", "Ursula von der Leyen", "América Latina", "Espanha",
        "Bósnia-Herzegovina", "Geopolítica"
    ],
    "Desporto": [
        "Desporto", "Futebol", "Benfica", "Sporting", "Porto",
        "Modalidades", "Mais Modalidades", "Mais modalidades",
        "Futebol Nacional", "Futebol Internacional", "Futebol-internacional",
        "Liga D'Ouro", "Maismotores", "Liga Europa", "Velocidade",
        "Futebol nacional", "Motores", "Ralis", "Karting", "Seleção Nacional",
        "Formula1", "Auto", "Bola-branca", "Futebol feminino", "Volta à França",
        "Automobilismo", "MotoGP", "Ciclismo", "Râguebi", "Futebol internacional",
        "Clube-portugal", "Especial-de-corrida", "Futebol-nacional", "Red Bull",
        "Ténis"
    ],
    "Economia": [
        "Economia", "Negócios", "Segurança Social", "Bolsa e Mercados",
        "Mercados", "Dinheiro", "Energia", "Empresas",
        "Iniciativaseprodutos", "Economia Expresso", "Economia dia a dia",
        "Finanças pessoais", "Finanças públicas", "Imobiliário", "Comércio",
        "Comércio Externo", "Criptomoedas", "Guerra Comercial", "Impostos",
        "irs", "Empreendedorismo", "Poupança", "trabalho", "rendas"
    ],
    "Cultura": [
        "Cultura", "Livros", "Cinema", "Blitz", "Inimigo-publico",
        "Artes", "Música",  "Festivais de Verão", "Fotografia"
    ],
    "Ciência e Tech": [
        "Ciência e Tech", "Ciência & Tech", "Ciência", "Ciencia",
        "Tech", "Tecnologia", "Microsoft", "Inteligência Artificial",
        "Exame Informática Brand studio", "Gadgets", "Internet",
        "Direto do lab", "Exame Informática", "Exameinformatica",
        "Redes_sociais", "Exame", "Facebook", "Apple", "Smartphones-tablets",
        "Biomedicina", "Espaço", "Paleontologia"
    ],
    "Sociedade": [
        "Sociedade", "Coronavírus", "Mau tempo", "Sustentabilidade",
        "Animais", "Ambiente", "Insólitos", "Meteorologia",
        "Viver-com-saude", "Revista", "Transportes", "Clube Expresso",
        "Atualidade", "Geração E", "Alterações climáticas", "Saúde",
        "Clima", "Verão", "Religiao", "Turismo", "Justiça", "Segurança",
        "Expresso-fundamental", "Previsao-de-longo-prazo",
        "Previsao-diaria", "Previsao-semanal", "Analise-meteorologica",
        "Visaosaude", "Projetos Expresso", "Oceanos", "Crime", "Ensino Superior",
        "Acidentes", "Activismo", "Aeroespacial", "Crianças", "Fraudes",
        "Incêndios", "Inimigo Público", "Megafone", "Menores em risco", "PJ",
        "Poluição", "Violência", "gasolina", "pescadores", "pordata",
        "prisão preventiva", "tortura", "Aquecimento", "50 anos das independências",
        "Habitação", "Acessibilidade", "Arquitectura", "Conservação da natureza",
        "Direitos das crianças", "Educação", "SGIFR",  "Segunda Guerra Mundial",
        "TAP", "linha de cascais", "tuk-tuk", "verao"
    ],
    "Política": [
        "Política", "Politica", "Defesa", "Presidenciais 2026",
        "Parlamento", "Partidos", "Crise política", "Governo",
        "Legislativas 2025", "Autárquicas 2025", "Lei da Nacionalidade",
        "Luís Filipe Menezes", "Ministério Público", "sns", "PAN",
        "Presidente"
    ],
    "Multimédia": [
        "Multimédia", "Multimedia", "Video", "Podcasts", "Fotogaleria",
        "No Princípio Era a Bola", "O Mundo a Seus Pés", "Contas Poupança",
        "O CEO é o limite", "Facto político", "Alta definição",
        "Expresso da Manhã", "Isto É Gozar Com Quem Trabalha",
        "Programa Cujo Nome Estamos Legalmente Impedidos de Dizer",
        "Ana Gomes", "Noticiários Desporto", "Minuto Consumidor",
        "Linhas Vermelhas", "Noticiário Antena1", "Memórias de Francisco Pinto Balsemão",
        "Leste Oeste de Nuno Rogeiro", "Vídeos", "O Divórcio do Sono",
        "Tv Media", "Tv-media", "Cmtv", "Antes Pelo Contrário", "Chave na mão",
        "Eixo do Mal", "Expresso da Meia-Noite", "Humor à Primeira Vista",
        "Importa-se de Repetir?", "Irritações", "No Último Episódio",
        "Alta Definição", "Elefante na Sala", "Era Uma Voz", "Facto Político",
        "O Tal Podcast"
    ],
    "Opinião": [
        "Opinião", "Opiniao", "Colunistas", "Nota editorial",
        "Editorial", "Linhas Direitas", "José jorge letria", "Liveblogs",
        "Artigos de Newsletter", "O Vale Era Verde", "Opinião União Europeia",
        "Isso era uma longa conversa", "Opinião Protopia",
         "Tanto faz não é resposta"
    ],
    "Lifestyle": [
        "Lifestyle", "Comer e beber", "Gastronomia", "Vida",
        "Realeza", "Moda", "Truques-dicas", "Boa cama boa mesa",
        "Boa Cama Boa Mesa", "Boa-cama-boa-mesa", "Vidas", "Óscares",
        "Fama", "Visaose7e", "Viagens", "Famosos", "Decoracao", "Ideias",
        "As Novas Cozinhas da Terra", "Beleza", "O gato das botas"
    ],
    "Vídeojogos": [
        "Vídeojogos", "Jogos", "Record-gaming"
    ],
    "Outras Notícias": [
        "Outras Notícias"
    ]
}

CATEGORY_MAPPER = {
    alias: category
    for category, aliases in CATEGORY_GROUPS.items()
    for alias in aliases
}

# Date format patterns for parsing publication dates
DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z"
]
