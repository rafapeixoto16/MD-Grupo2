from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

# Lista de queries relevantes sobre prevenção farmacológica
VITAMIN_QUERIES = [
    # Vitamina D
    '("Vitamin D supplementation" AND "disease prevention")',
    '("Vitamin D deficiency" AND "immune system")',
    '("Vitamin D" AND "bone health" AND "osteoporosis")',
    '("Vitamin D" AND "cardiovascular disease" AND "prevention")',
    '("Vitamin D" AND "respiratory infections" AND "prevention")',

    # Vitamina C
    '("Vitamin C supplementation" AND "antioxidant" AND "disease")',
    '("Ascorbic acid" AND "immune function" AND "prevention")',
    '("Vitamin C" AND "collagen synthesis" AND "wound healing")',
    '("Vitamin C" AND "cancer prevention" AND "antioxidant")',
    '("Vitamin C" AND "iron absorption" AND "anemia")',

    # Vitamina B12
    '("Vitamin B12 deficiency" AND "neurological disorders")',
    '("Cobalamin supplementation" AND "cognitive function")',
    '("Vitamin B12" AND "pernicious anemia" AND "treatment")',
    '("Vitamin B12" AND "methylation" AND "homocysteine")',
    '("Vitamin B12" AND "vegan diet" AND "supplementation")',

    # Folato/Ácido Fólico
    '("Folic acid supplementation" AND "neural tube defects")',
    '("Folate deficiency" AND "pregnancy" AND "prevention")',
    '("Folic acid" AND "cardiovascular disease" AND "homocysteine")',
    '("Folate" AND "cancer prevention" AND "DNA methylation")',
    '("Folic acid fortification" AND "public health")',

    # Vitamina A
    '("Vitamin A supplementation" AND "vision" AND "night blindness")',
    '("Retinol" AND "immune function" AND "infection")',
    '("Beta-carotene" AND "cancer prevention" AND "antioxidant")',
    '("Vitamin A deficiency" AND "developing countries")',
    '("Vitamin A" AND "skin health" AND "epithelial tissue")',

    # Vitamina E
    '("Vitamin E supplementation" AND "cardiovascular disease")',
    '("Alpha-tocopherol" AND "antioxidant" AND "aging")',
    '("Vitamin E" AND "cognitive decline" AND "Alzheimer")',
    '("Vitamin E" AND "muscle damage" AND "exercise")',
    '("Vitamin E deficiency" AND "neurological symptoms")',

    # Vitamina K
    '("Vitamin K supplementation" AND "bone health")',
    '("Vitamin K2" AND "cardiovascular calcification")',
    '("Vitamin K" AND "blood coagulation" AND "warfarin")',
    '("Menaquinone" AND "bone metabolism" AND "osteoporosis")',
    '("Vitamin K deficiency" AND "bleeding disorders")',

    # Complexo B geral
    '("B vitamins" AND "energy metabolism" AND "fatigue")',
    '("B complex supplementation" AND "stress" AND "mood")',
    '("B vitamins deficiency" AND "peripheral neuropathy")',
    '("Thiamine deficiency" AND "beriberi" AND "alcoholism")',
    '("Riboflavin supplementation" AND "migraine prevention")',

    # Múltiplas vitaminas e interações
    '("Multivitamin supplementation" AND "mortality" AND "prevention")',
    '("Vitamin deficiency" AND "elderly" AND "supplementation")',
    '("Fat-soluble vitamins" AND "absorption" AND "malabsorption")',
    '("Water-soluble vitamins" AND "kidney disease" AND "dialysis")',
    '("Vitamin overdose" AND "toxicity" AND "hypervitaminosis")',

    # Contextos específicos
    '("Prenatal vitamins" AND "pregnancy outcomes")',
    '("Vitamin supplementation" AND "chronic kidney disease")',
    '("Vitamins" AND "cancer chemotherapy" AND "interaction")',
    '("Vitamin supplements" AND "drug interactions")',
    '("Vitamin supplementation" AND "COVID-19" AND "prevention")',

    # Informações gerais sobre suplementos
    "Dietary supplements definition and purpose",
    "Difference between dietary supplements and medications",
    "Regulation of dietary supplements vs pharmaceutical drugs",
    "Safety of over-the-counter dietary supplements",
    "Drug-supplement interactions review",

    # Suplementos populares
    "Vitamin D health benefits and functions",
    "Omega-3 cardiovascular disease prevention meta-analysis",
    "Magnesium physiological functions and deficiency symptoms",
    "Curcumin anti-inflammatory properties clinical trials",
    "Biotin supplementation hair nail skin health evidence",

    # Prevenção de doenças
    "Supplements for immune system support review",
    "Supplements for influenza prevention evidence-based",
    "Vitamin D calcium bone health osteoporosis prevention",
    "Cardiovascular disease prevention supplements Cochrane",
    "Long-term drug use and micronutrient deficiencies",

    # Suplementos por fase da vida ou condição
    "Nutritional supplements for elderly health outcomes",
    "Prenatal vitamins and supplements during pregnancy",
    "Menopause supplements efficacy and safety",
    "Iron supplementation in anemia management",
    "Supplements for mental health depression anxiety evidence",

    # Dieta e estilo de vida
    "Vitamin B12 and vegan diet supplementation",
    "Balanced diet vs supplementation necessity",
    "Dietary supplements vs healthy diet outcomes",
    "Health risks of excessive supplement intake",
    "Biomarkers to assess supplement need clinical practice",

    # Uso, eficácia e segurança
    "Time to effectiveness of dietary supplements",
    "Signs of ineffective supplementation",
    "How to choose high-quality dietary supplements",
    "Nutritional blood tests before supplementation",
    "Risks of buying dietary supplements online",

    # Fármacos e prevenção
    '(TITLE:preventive OR ABSTRACT:preventive) AND pharmacology AND ("chronic disease" OR "chronic diseases")',
    '"primary prevention" AND (pharmaceuticals OR drugs OR medications)',
    'statins AND ("disease prevention" OR "cardiovascular prevention")',
    'metformin AND ("cancer prevention" OR "oncoprevention")',
    'aspirin AND ("primary prevention" OR "prophylactic use")',
    '("immunomodulatory drugs" OR "immunosuppressants") AND ("infection prevention" OR "prophylaxis")',
    'nutraceuticals AND pharmaceuticals AND ("disease prevention" OR "preventive health")',
    '"drug repurposing" AND ("disease prevention" OR prophylaxis)',
    'antihypertensives AND ("preventive use" OR "primary prevention")',
    'chemoprevention AND ("randomized controlled trial" OR RCT)',

    # Vitamina C detalhada
    '"vitamin C" OR "ascorbic acid" OR "L-ascorbic acid"',
    '"vitamin C deficiency" OR "scurvy" OR "hypovitaminosis C"',
    '"vitamin C supplementation" OR "ascorbic acid supplement"',
    'antioxidant AND ("vitamin C" OR "ascorbic acid")',
    '"collagen synthesis" AND "vitamin C"',
    '"vitamin C" AND ("immune system" OR "immunity")',
    '"dietary vitamin C" OR "vitamin C content" AND food',
    '"vitamin C absorption" OR "ascorbate transport"',
    '"vitamin C dosage" OR "ascorbic acid dose"',
    '"vitamin C" AND ("iron absorption" OR "wound healing")',

    # Suplementos e gripes/imunidade
    "Immune system supplements influenza treatment",
    "Nutraceuticals antiviral immune response",
    "Vitamin C vitamin D zinc immune support flu",
    "Natural supplements boost immunity common cold",
    "Herbal remedies flu immune modulation",

    # Osteoporose e vitaminas
    "Vitamin D calcium osteoporosis prevention",
    "Vitamin K2 bone health supplementation",
    "Excess vitamin D side effects osteoporosis",
    "Nutrient interactions vitamin K and calcium",
    "Vitamin K supplementation and fracture risk",

    # Deficiências induzidas por medicamentos
    "Drug-induced nutrient depletion review",
    "Medication nutrient interactions long term use",
    "Common drugs causing vitamin mineral deficiency",
    "Age-related drug nutrient depletion",
    "Proton pump inhibitors B12 deficiency aging",

    # Iodo e cálcio
    "Iodine supplementation thyroid health",
    "Iodine deficiency symptoms and treatment",
    "Calcium supplementation bone density elderly",
    "Calcium absorption vitamin D interaction",
    "Risks of calcium over-supplementation cardiovascular",

    # Avaliação da necessidade e eficácia
    "How to assess need for dietary supplements",
    "Clinical signs of vitamin deficiencies",
    "Effectiveness timeline for supplements",
    "Supplement absorption and bioavailability",
    "Guidelines for general supplement use",

    # Segurança geral de suplementos
    "Evidence-based dietary supplement use general population",
    "Multivitamins health outcomes meta-analysis",
    "Safety of long-term supplement use",
    "Public health guidelines on supplements",
    "Nutritional supplementation preventive health",

    # Estratégias preventivas com suplementos
    "preventive effects of dietary supplements on chronic diseases",
    "difference between drugs and supplements in disease prevention",
    "creatine use in the prevention of sarcopenia in elderly",
    "calcium supplementation and osteoporosis prevention",
    "melatonin as a supplement for prevention of sleep disorders",
    "vitamin D as a preventive agent in autoimmune diseases",
    "which supplements have scientific evidence for cardiovascular disease prevention",
    "use of dietary supplements as a public health prevention strategy",
    "effectiveness of dietary supplementation in preventing neurodegenerative diseases",
    "interaction between dietary supplements and pharmaceuticals in disease prevention",
    "how supplements contribute to disease prevention",
    "preventive health benefits of antioxidant supplementation",
    "when is a dietary supplement considered preventive rather than therapeutic",
    "safe calcium levels in preventive supplementation",
    "does melatonin have preventive effects on metabolic syndrome?",
    "role of creatine in preventing age-related muscle atrophy",
    "dietary supplementation and longevity: what does the science say?",
    "are preventive supplements regulated in the EU or Portugal?",
    "assessment of dietary supplements claiming disease prevention benefits",
    "supplements with EFSA-approved health claims for prevention",

    # Suplementos não essenciais
    "health benefits and preventive effects of Tribulus Terrestris supplementation",
    "evidence for Tribulus Terrestris in cardiovascular or metabolic disease prevention",
    "dextrose supplementation and its impact on metabolic health and disease risk",
    "role of dextrose in insulin regulation and chronic disease development",
    "preventive health potential of GABA supplementation in stress-related disorders",
    "GABA as a supplement for prevention of anxiety and sleep disorders",
    "Highly Branched Cyclic Dextrin and its effects on metabolic markers",
    "can Highly Branched Cyclic Dextrin support disease prevention via improved nutrient delivery?",
    "comparative analysis of cyclic dextrins for health and disease prevention",
    "scientific evidence for using GABA as a neuroprotective supplement",
    "impact of carbohydrate-based supplements like dextrose and HBCD on long-term health",
    "evaluation of non-essential supplements (e.g. Tribulus, HBCD, GABA) in preventive nutrition"

    '"drug-induced nutrient deficiencies" OR "drug nutrient interactions"',
    '"long-term medication" AND ("vitamin deficiency" OR "mineral deficiency")',
    '"polypharmacy" AND "nutritional status" AND ("elderly" OR "older adults")',
    '"supplement use" AND "drug-induced deficiency" OR "preventive supplementation"',
    '"clinical guidelines" OR "monitoring" AND "nutrient status" AND "chronic medication"'

]


def display_vitamin_queries():
    """Displays the list of vitamin queries in a formatted table."""
    console = Console()
    table = Table(title="🧪 Preventive Pharmacology Research Queries", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=3)
    table.add_column("Query", style="cyan")
    
    for i, query in enumerate(VITAMIN_QUERIES, 1):
        table.add_row(str(i), query)
    
    console.print(table)
    return len(VITAMIN_QUERIES)

def select_query():
    """Allows user to select a query from the list."""
    console = Console()
    total_queries = display_vitamin_queries()
    
    while True:
        try:
            choice = int(Prompt.ask(f"[bold white]Select a query (1-{total_queries}) or 0 for custom query[/bold white]"))
            if choice == 0:
                return Prompt.ask("[bold white]Enter your custom query:[/bold white]")
            elif 1 <= choice <= total_queries:
                return VITAMIN_QUERIES[choice - 1]
            else:
                console.print(f"[bold red]❌ Please enter a number between 0 and {total_queries}[/bold red]")
        except ValueError:
            console.print("[bold red]❌ Please enter a valid number[/bold red]")

def display_enhanced_menu():
    """Displays the enhanced menu with vitamin queries option."""
    console = Console()
    
    menu_table = Table(title="🔬 Enhanced Research Tool", show_header=True, header_style="bold green")
    menu_table.add_column("Option", style="bold blue", width=8)
    menu_table.add_column("Description", style="white")
    
    menu_options = [
        ("1", "PubMed Search"),
        ("2", "Europe PMC Search"),
        ("3", "Semantic Scholar Search"),
        ("4", "Wikipedia Search"),
        ("5", "Google Scholar Search"),
        ("6", "Search All Sources"),
        ("7", "🧪 Google Scholar Batch (Single Query)"),
        ("8", "📋 View Research Queries List"),
        ("9", "🚀 Execute ALL Research Queries (Batch Mode)"),
        ("T", "🔧 Test Google Scholar Connection"),
        ("Q", "Quit")
    ]
    
    for option, description in menu_options:
        menu_table.add_row(option, description)
    
    console.print(menu_table)
    return Prompt.ask("\n[bold white]Choose an option[/bold white]", default="1")

def display_source_selection_menu():
    """Displays the source selection menu for batch searches."""
    console = Console()
    
    source_table = Table(title="Choose Source for Batch Search", show_header=True, header_style="bold cyan")
    source_table.add_column("Option", style="bold blue", width=8)
    source_table.add_column("Source", style="white")
    
    source_options = [
        ("1", "Google Scholar"),
        ("2", "PubMed"),
        ("3", "Europe PMC"),
        ("4", "Semantic Scholar")
    ]
    
    for opt, src in source_options:
        source_table.add_row(opt, src)
    
    console.print(source_table)
    return source_options

def get_source_map():
    """Returns the mapping of menu choices to source names."""
    return {
        "1": "google_scholar",
        "2": "pubmed", 
        "3": "europe_pmc",
        "4": "semantic_scholar"
    }

def get_sources_dict():
    """Returns the sources dictionary for the main menu."""
    from modules.pubmed_utils import search_pubmed
    from modules.europePMC_utils import search_europe_pmc
    from modules.semanticscholar_utils import search_semanticscholar
    from modules.wikipedia_utils import search_wikipedia
    from modules.googleScholar_utils import search_google_scholar
    
    return {
        "1": ("PubMed", search_pubmed),
        "2": ("Europe PMC", search_europe_pmc),
        "3": ("Semantic Scholar", search_semanticscholar),
        "4": ("Wikipedia", search_wikipedia),
        "5": ("Google Scholar", search_google_scholar),
        "6": ("All Sources", None)
    }

def display_batch_confirmation(num_queries, selected_source, num_docs_per_query):
    """Displays batch operation confirmation details."""
    console = Console()
    
    console.print(f"\n[bold yellow]⚠️  About to execute {num_queries} queries on {selected_source.replace('_', ' ').title()}[/bold yellow]")
    console.print(f"[bold yellow]⚠️  This will retrieve up to {num_queries * num_docs_per_query} documents total[/bold yellow]")
    console.print(f"[bold yellow]⚠️  Estimated time: {num_queries * 2} seconds (with API delays)[/bold yellow]")
    
    return Prompt.ask("[bold white]Continue? (y/n)[/bold white]", default="n")

def display_menu():
    """Legacy function name for backward compatibility."""
    return display_enhanced_menu()