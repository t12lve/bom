"""Static lexicons used by the BOM pipeline.

Everything here is plain data: no network, no I/O, no side effects.
The banks are bilingual (FR/EN) because BOM candidates are usually
launched from France but ranked and marketed globally.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Stopwords / glue used to isolate roots from raw keyword lists
# --------------------------------------------------------------------------

STOPWORDS: set[str] = {
    # FR
    "le", "la", "les", "un", "une", "des", "du", "de", "d", "au", "aux",
    "et", "ou", "en", "dans", "pour", "par", "sur", "avec", "sans", "chez",
    "que", "qui", "quoi", "dont", "mon", "ma", "mes", "ton", "ta", "tes",
    "son", "sa", "ses", "ce", "cet", "cette", "ces", "est", "sont", "etre",
    "plus", "moins", "tres", "tout", "tous", "toute", "toutes", "quel",
    "quelle", "quels", "quelles", "comment", "pourquoi", "quand", "ou",
    "meilleur", "meilleure", "meilleurs", "meilleures", "gratuit",
    "gratuite", "gratuits", "gratuites", "top", "best", "bon", "bonne",
    # EN
    "the", "a", "an", "of", "for", "to", "in", "on", "with", "without",
    "and", "or", "is", "are", "be", "how", "what", "why", "when", "where",
    "which", "my", "your", "our", "their", "it", "this", "that", "these",
    "those", "best", "free", "cheap", "good", "like", "vs", "versus",
}

# Words that carry intent rather than topic. They are extracted separately
# so the generator never names a product "Gratuit" or "Best".
INTENT_MARKERS: dict[str, set[str]] = {
    "transactional": {
        "acheter", "achat", "prix", "tarif", "tarifs", "abonnement",
        "abonnements", "payer", "paiement", "cout", "coute", "combien",
        "devis", "promo", "reduction", "code", "essai", "telecharger",
        "download", "installer", "install", "buy", "price", "pricing",
        "cheap", "deal", "subscription", "trial", "signup", "register",
    },
    "commercial": {
        "logiciel", "logiciels", "app", "apps", "application",
        "applications", "outil", "outils", "plateforme", "service",
        "services", "saas", "site", "site web", "solution", "software",
        "tool", "tools", "platform", "product", "service", "suite",
        "extension", "plugin", "api", "mobile",
    },
    "informational": {
        "comment", "pourquoi", "guide", "tutoriel", "tutorial", "definition",
        "exemple", "exemples", "modele", "modele", "astuce", "astuces",
        "conseil", "conseils", "formation", "apprendre", "learn", "how",
        "why", "guide", "example", "examples", "template", "tips", "learn",
        "documentation", "docs",
    },
    "navigational": {
        "alternative", "alternatives", "avis", "review", "reviews",
        "comparatif", "comparaison", "comparison", "vs", "versus", "top",
        "classement", "ranking", "meilleur", "best", "concurrent",
        "competitor",
    },
    "problem": {
        "erreur", "erreurs", "probleme", "problemes", "bug", "bugs",
        "panne", "lent", "lente", "bloque", "bloquee", "marche pas",
        "ne fonctionne pas", "error", "issue", "broken", "slow", "fix",
        "crash", "fails", "not working",
    },
}

# --------------------------------------------------------------------------
# The five semantic clusters (BOM Phase 1)
# --------------------------------------------------------------------------

CLUSTER_IDS: tuple[str, ...] = ("benefit", "action", "tech", "target", "metaphor")

CLUSTER_LABELS: dict[str, str] = {
    "benefit": "Benefice",
    "action": "Action",
    "tech": "Tech / Mecanique",
    "target": "Cible",
    "metaphor": "Metaphore",
}

CLUSTER_LEXICONS: dict[str, set[str]] = {
    "benefit": {
        # FR
        "gain", "gains", "temps", "rapidite", "rapide", "simple",
        "simplicite", "facile", "clarte", "clair", "controle", "maitrise",
        "securite", "securise", "fiable", "fiabilite", "productivite",
        "performance", "efficacite", "economie", "economies", "argent",
        "revenu", "revenus", "rentabilite", "croissance", "visibilite",
        "qualite", "confort", "sante", "bienetre", "liberte", "autonomie",
        "precision", "confiance", "tranquillite", "serenite", "impact",
        "resultat", "resultats", "succes", "progres", "amelioration",
        "marge", "marges", "rentable", "gaspillage", "gaspiller", "perte",
        "pertes", "reduire", "reduction", "augmenter", "ameliorer",
        "fidelite", "fideliser", "temps", "rapidite", "simplicite",
        "maitrise", "serenite", "tranquillite", "visibilite",
        # EN
        "save", "saving", "savings", "fast", "faster", "speed", "simple",
        "easy", "clarity", "control", "secure", "security", "reliable",
        "productivity", "performance", "efficiency", "profit", "revenue",
        "growth", "visibility", "quality", "comfort", "health", "freedom",
        "accuracy", "trust", "calm", "impact", "result", "results",
        "success", "progress", "improvement", "roi", "value", "gain",
    },
    "action": {
        # FR
        "creer", "creation", "generer", "generation", "analyser", "analyse",
        "suivre", "suivi", "trier", "classer", "organiser", "planifier",
        "automatiser", "automatisation", "optimiser", "optimisation",
        "comparer", "surveiller", "detecter", "mesurer", "publier",
        "partager", "collaborer", "gerer", "gestion", "convertir",
        "scanner", "filtrer", "rechercher", "trouver", "lancer", "piloter",
        "centraliser", "connecter", "synchroniser", "rediger", "traduire",
        "calculer", "calcul", "commander", "inventorier", "tracer", "saisir",
        "imprimer", "editer", "declencher", "alerter", "notifier", "valider",
        "corriger", "estimer", "simuler", "prevoir", "arbitrer", "prioriser",
        # EN
        "create", "generate", "analyze", "track", "sort", "organize",
        "plan", "automate", "optimize", "compare", "monitor", "detect",
        "measure", "publish", "share", "collaborate", "manage", "convert",
        "scan", "filter", "search", "find", "launch", "pilot", "centralize",
        "connect", "sync", "write", "translate", "build", "ship", "route",
    },
    "tech": {
        # FR
        "ia", "intelligence", "artificielle", "algorithme", "modele",
        "donnees", "data", "api", "cloud", "saas", "no code", "nocode",
        "automatisation", "script", "moteur", "moteurs", "llm", "gpt",
        "prompt", "prompts", "agent", "agents", "plugin", "extension",
        "dashboard", "tableau", "tableau de bord", "workflow", "pipeline",
        "base", "base de donnees", "serveur", "hebergement", "open source",
        "seo", "geo", "serp", "indexation", "backlink", "crawl", "scraping",
        "integration", "webhook", "temps reel", "realtime", "vectoriel",
        "embedding", "embeddings", "rag", "fine tuning", "inference",
        # generic business artefacts an operator manipulates in a tool
        "facture", "factures", "devis", "commande", "commandes", "stock",
        "stocks", "fournisseur", "fournisseurs", "prix", "cout", "couts",
        "recette", "recettes", "ingredient", "ingredients", "fiche",
        "fiches", "tableau", "export", "import", "saisie", "ocr", "scan",
        "referentiel", "catalogue", "calendrier", "notification", "alerte",
        "rapport", "kpi", "indicateur", "indicateurs", "seuil", "marge",
        "inventaire", "tracabilite", "allergene", "etiquette", "caisse",
        "comptabilite", "fichier", "csv", "excel", "template", "modele",
        # EN
        "ai", "machine", "learning", "algorithm", "model", "data", "api",
        "cloud", "saas", "nocode", "automation", "script", "engine", "llm",
        "gpt", "prompt", "agent", "plugin", "extension", "dashboard",
        "workflow", "pipeline", "database", "server", "hosting", "open source",
        "seo", "geo", "serp", "indexing", "backlink", "crawl", "scraping",
        "integration", "webhook", "realtime", "vector", "embedding", "rag",
        "inference", "stack", "devops", "runtime",
        "invoice", "invoices", "quote", "order", "orders", "supplier",
        "suppliers", "ingredient", "ingredients", "recipe", "recipes",
        "sheet", "export", "import", "entry", "ocr", "catalog", "calendar",
        "notification", "alert", "report", "kpi", "threshold", "inventory",
        "traceability", "allergen", "label", "checkout", "accounting",
        "file", "csv", "template",
    },
    "target": {
        # FR
        "debutant", "debutants", "expert", "experts", "pro", "pros",
        "professionnel", "professionnels", "freelance", "freelances",
        "agence", "agences", "pme", "tpe", "startup", "startups",
        "ecommerce", "e commerce", "commercant", "commercants", "marque",
        "marques", "createur", "createurs", "createur de contenu",
        "influenceur", "influenceurs", "developpeur", "developpeurs",
        "designer", "designers", "marketeur", "marketeurs", "artisan",
        "artisans", "restaurateur", "restaurateurs", "etudiant", "etudiants",
        "enseignant", "enseignants", "independant", "independants", "b2b",
        "b2c", "client", "clients", "equipe", "equipes", "direction",
        # EN
        "beginner", "beginners", "expert", "experts", "pro", "pros",
        "professional", "professionals", "freelancer", "freelancers",
        "agency", "agencies", "sme", "startup", "startups", "ecommerce",
        "merchant", "merchants", "brand", "brands", "creator", "creators",
        "influencer", "influencers", "developer", "developers", "designer",
        "designers", "marketer", "marketers", "student", "students",
        "teacher", "teachers", "solo", "indie", "b2b", "b2c", "client",
        "clients", "team", "teams", "enterprise", "smb",
    },
    "metaphor": {
        # FR
        "voyage", "chemin", "route", "boussole", "phare", "feu", "etincelle",
        "ruche", "abeille", "miel", "nid", "jardin", "graine", "semence",
        "arbre", "foret", "riviere", "ocean", "vague", "marée", "port",
        "ancre", "carte", "atlas", "horizon", "sommet", "montagne", "phare",
        "lentille", "prisme", "miroir", "echo", "pouls", "souffle", "elan",
        "tissage", "métier", "a tisser", "forge", "enclume", "mosaique",
        "constellation", "etoile", "lune", "soleil", "aube", "nord",
        # EN
        "journey", "path", "road", "compass", "beacon", "spark", "ember",
        "hive", "bee", "honey", "nest", "garden", "seed", "tree", "forest",
        "river", "ocean", "wave", "tide", "harbor", "anchor", "map", "atlas",
        "horizon", "summit", "peak", "lens", "prism", "mirror", "echo",
        "pulse", "breath", "weave", "loom", "forge", "anvil", "mosaic",
        "constellation", "star", "moon", "sun", "dawn", "north", "keystone",
        "lantern", "orchard", "oasis", "helix", "quill", "hive", "swarm",
    },
}

# --------------------------------------------------------------------------
# Morphology banks for candidate generation
# --------------------------------------------------------------------------

# Suffixes that read as "product" to a French or English reader.
# `tone` describes the positioning, `archetype` the natural fit.
SUFFIXES: tuple[dict[str, str], ...] = (
    {"s": "ly", "tags": "saas friendly modern", "cliche": "high"},
    {"s": "ify", "tags": "verb transformation", "cliche": "high"},
    {"s": "io", "tags": "tech startup short", "cliche": "medium"},
    {"s": "ai", "tags": "ai explicit", "cliche": "high"},
    {"s": "base", "tags": "storage reference", "cliche": "low"},
    {"s": "kit", "tags": "toolbox", "cliche": "medium"},
    {"s": "lab", "tags": "experimentation", "cliche": "medium"},
    {"s": "flow", "tags": "process movement", "cliche": "medium"},
    {"s": "wise", "tags": "advice intelligence", "cliche": "medium"},
    {"s": "deck", "tags": "control surface", "cliche": "low"},
    {"s": "rank", "tags": "seo positioning", "cliche": "low"},
    {"s": "signal", "tags": "data quality", "cliche": "low"},
    {"s": "scope", "tags": "observation", "cliche": "low"},
    {"s": "pilot", "tags": "guidance automation", "cliche": "low"},
    {"s": "bridge", "tags": "connection", "cliche": "low"},
    {"s": "nest", "tags": "shelter aggregation", "cliche": "low"},
    {"s": "forge", "tags": "craft build", "cliche": "low"},
    {"s": "loop", "tags": "iteration feedback", "cliche": "low"},
    {"s": "peak", "tags": "performance summit", "cliche": "low"},
    {"s": "craft", "tags": "artisan quality", "cliche": "low"},
)

PREFIXES: tuple[dict[str, str], ...] = (
    {"s": "nova", "tags": "newness brightness"},
    {"s": "neo", "tags": "newness clarity"},
    {"s": "omni", "tags": "all in one"},
    {"s": "lumi", "tags": "light insight"},
    {"s": "veri", "tags": "truth verification"},
    {"s": "quanti", "tags": "measurement"},
    {"s": "hyper", "tags": "speed scale"},
    {"s": "meta", "tags": "abstraction layer"},
    {"s": "uni", "tags": "unification"},
    {"s": "poly", "tags": "multi capability"},
)

# Metaphor seeds mapped to the business meaning they should carry.
# The generator only uses a seed when a cluster root is compatible.
METAPHOR_SEEDS: tuple[dict[str, str], ...] = (
    {"s": "hive", "meaning": "collective intelligence, many small workers"},
    {"s": "beacon", "meaning": "visibility, signal in the dark"},
    {"s": "compass", "meaning": "direction, decision support"},
    {"s": "loom", "meaning": "weaving raw material into a product"},
    {"s": "forge", "meaning": "crafting, building with force"},
    {"s": "anchor", "meaning": "stability, reference point"},
    {"s": "lantern", "meaning": "guided discovery"},
    {"s": "orchard", "meaning": "patient compounding growth"},
    {"s": "prism", "meaning": "one input, many angles"},
    {"s": "tide", "meaning": "market movement, timing"},
    {"s": "keystone", "meaning": "structural indispensability"},
    {"s": "atlas", "meaning": "structured knowledge map"},
    {"s": "ember", "meaning": "small durable energy"},
    {"s": "swarm", "meaning": "parallel agents at scale"},
    {"s": "quill", "meaning": "authored content, editorial quality"},
    {"s": "helix", "meaning": "compounding, structural depth"},
)

# Light category morphemes used to keep metaphor compounds decodable by LLMs
# (BOM GEO archetype: the model must guess the sector from the name).
CATEGORY_MORPHEMES: tuple[str, ...] = (
    "way", "path", "board", "deck", "works", "studio", "desk", "map",
    "list", "rank", "scan", "lens", "meter", "pilot", "guide",
)

# Onsets / nuclei / codas for the short neologism archetype.
ONSETS: tuple[str, ...] = (
    "b", "c", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "r", "s",
    "t", "v", "w", "z", "br", "dr", "fl", "gr", "pl", "pr", "sk", "sl",
    "sm", "sn", "sp", "st", "tr", "bl", "cl", "gl", "kr", "vr", "th", "sh",
)
NUCLEI: tuple[str, ...] = (
    "a", "e", "i", "o", "u", "y", "ai", "ea", "eo", "ia", "io", "ou", "au",
)
CODAS: tuple[str, ...] = (
    "", "n", "r", "l", "s", "t", "x", "m", "ck", "nt", "st", "rk", "lt",
)

# --------------------------------------------------------------------------
# Hard filters
# --------------------------------------------------------------------------

# Unambiguous profanity / hate / adult terms: hard rejection.
HARD_BAD_WORDS: tuple[str, ...] = (
    "merde", "putain", "pute", "salope", "connard", "connasse", "encul",
    "nique", "couille", "zizi", "chatte", "penis", "vagin", "anus",
    "fdp", "nazi", "hitler", "sida", "kaka", "pipi", "zob", "suce",
    "fuck", "shit", "cunt", "nigger", "rape", "porn", "dick", "cock",
    "bitch", "whore", "slut", "cum", "tits", "boobs", "xxx",
)

# Ambiguous terms: warning + penalty, not a hard reject. They become hard
# only when they are the whole name or sit at its edge (see text._word_hit).
SOFT_BAD_SUBSTRINGS: tuple[str, ...] = (
    "cul", "con", "pd", "pet", "moule", "boudin", "gland", "queue",
    "chier", "chie", "bite", "anal", "sex", "killer", "dead", "kill",
    "hate", "war", "ass",
)

# Well-known entities an LLM already knows. A candidate matching one of these
# starts with a serious GEO handicap and a trademark risk.
BRAND_BLOCKLIST: tuple[str, ...] = (
    "apple", "google", "alphabet", "microsoft", "amazon", "aws", "meta",
    "facebook", "instagram", "whatsapp", "openai", "chatgpt", "anthropic",
    "claude", "gemini", "bard", "perplexity", "copilot", "github", "gitlab",
    "stripe", "shopify", "notion", "figma", "slack", "zoom", "dropbox",
    "spotify", "netflix", "uber", "airbnb", "tesla", "nvidia", "intel",
    "oracle", "salesforce", "hubspot", "mailchimp", "canva", "adobe",
    "semrush", "ahrefs", "surfer", "jasper", "midjourney", "mistral",
    "huggingface", "vercel", "netlify", "supabase", "firebase", "twilio",
    "datadog", "sentry", "atlassian", "jira", "trello", "asana", "monday",
    "airtable", "zapier", "make", "n8n", "wordpress", "wix", "squarespace",
    "webflow", "framer", "linear", "loom", "miro", "calendly", "typeform",
    "intercom", "zendesk", "segment", "amplitude", "mixpanel", "hotjar",
    "cloudflare", "digitalocean", "heroku", "docker", "kubernetes",
    # suites and french/enterprise incumbents: unnacceptable collisions
    "excel", "office", "teams", "windows", "chrome", "android", "word",
    "photoshop", "illustrator", "indesign", "acrobat", "quickbooks", "xero",
    "sage", "cegid", "pennylane", "qonto", "lucca", "payfit", "swile",
    "zapier", "airtable", "clickup", "basecamp", "odoo", "sap", "ibm",
    # consumer marks that must never pass the filter
    "lego", "playmobil", "mattel", "hasbro", "ikea", "decathlon", "carrefour",
)

# Common words that make a name unregistrable and unrankable.
GENERIC_WORDS: set[str] = {
    "app", "apps", "application", "site", "web", "webapp", "tool", "tools",
    "software", "service", "services", "platform", "solution", "solutions",
    "data", "cloud", "ai", "bot", "chat", "code", "dev", "digital", "tech",
    "smart", "fast", "quick", "easy", "simple", "best", "top", "pro", "max",
    "plus", "one", "all", "any", "now", "new", "next", "open", "free",
    "logiciel", "outil", "outils", "plateforme", "service", "services",
    "donnees", "nuage", "intelligence", "artificielle", "application",
    "mobile", "conseil", "gestion", "solution", "solutions", "marque",
    "nom", "naming", "brand", "branding", "seo", "geo", "marketing",
    "studio", "agency", "agence", "group", "groupe", "labs", "lab",
    "works", "systems", "systeme", "digital", "media", "network",
}

# Common nouns (FR/EN) that are unregistrable as-is in the classes we target
# and that no LLM will treat as a distinct entity. A candidate equal to one of
# these is rejected before any network call.
DICTIONARY_NOUNS: set[str] = {
    # food / restaurant
    "restaurant", "cuisine", "menu", "carte", "plat", "recette", "food",
    "kitchen", "recipe", "dish", "meal", "chef", "bistro", "brasserie",
    "pizzeria", "traiteur", "table", "comptoir", "ardoise", "marmite",
    "four", "fourneau", "epice", "miel", "honey", "ruche", "abeille",
    "potager", "jardin", "graine", "recolte", "saison", "burger", "pain",
    # business
    "prix", "price", "cout", "cost", "marge", "margin", "stock", "vente",
    "sale", "achat", "achats", "facture", "invoice", "budget", "compta",
    "gestion", "management", "service", "client", "marque", "brand",
    "marche", "market", "ventes", "profit", "benefice", "perte", "loss",
    "audit", "rapport", "report", "plan", "strategy", "strategie",
    # product / tech
    "app", "software", "logiciel", "outil", "tool", "platform", "produit",
    "product", "data", "donnees", "cloud", "saas", "agent", "prompt",
    "model", "modele", "algo", "algorithme", "code", "dev", "api", "bot",
    "chat", "site", "web", "page", "dashboard", "tableau", "bord",
    # generic metaphors that are too worn to be a mark
    "hive", "beacon", "compass", "loom", "forge", "anchor", "lantern",
    "orchard", "prism", "tide", "keystone", "atlas", "ember", "swarm",
    "quill", "helix", "north", "summit", "peak", "ocean", "river", "wave",
    "forest", "tree", "seed", "garden", "star", "moon", "sun", "dawn",
    "echo", "pulse", "path", "way", "map", "guide", "pilot", "flow",
    "base", "kit", "lab", "deck", "board", "list", "scope", "loop",
    "craft", "bridge", "hub", "suite", "track", "grow", "build", "ops",
    "stack", "vault", "radar", "watch", "guard", "signal", "meter",
}

# TLD weights live in score.PILLARS (technique/com/tlds); the audit only
# reports statuses, it does not weight them.

# French-friendly first names: a candidate that is a common first name will
# be diluted in AI answers and in SERPs.
COMMON_FIRST_NAMES: set[str] = {
    "lucas", "hugo", "leo", "gabriel", "louis", "arthur", "jules", "adam",
    "raphael", "nathan", "paul", "tom", "noah", "lucas", "ethan", "mila",
    "emma", "lea", "chloe", "jade", "louise", "alice", "amber", "rose",
    "marie", "julie", "sophie", "camille", "clara", "nina", "lina", "zoe",
    "max", "sam", "alex", "victor", "oscar", "eli", "noe", "sacha",
}
