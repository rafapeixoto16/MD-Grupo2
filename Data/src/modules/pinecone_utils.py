import os
import uuid
import json
import hashlib
import numpy as np
from tqdm import tqdm
from modules.spaCy_utils import process_text
from pinecone import Pinecone, ServerlessSpec


def configure_pinecone_connection():
    """Configure Pinecone connection."""
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY não está definida.")
    pc = Pinecone(api_key=pinecone_api_key)
    index_name = "project"
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=1024,
            metric='cosine',
            spec=ServerlessSpec(cloud='aws', region='us-east-1')
        )
    return pc.Index(index_name)


def generate_doc_id(title, text, source, doi=None, pmid=None, semantic_id=None, url=None):
    """
    Generate a deterministic document ID using the most reliable unique identifier available.
    Priority: DOI > PMID > Semantic Scholar ID > URL > Content Hash
    """
    # Limpar e normalizar identificadores
    title_clean = title.strip().lower() if title else ""
    text_clean = text.strip().lower() if text else ""
    
    # 1. Usar DOI como identificador principal se disponível
    if doi and doi.strip():
        doi_clean = doi.strip().lower()
        # Remover prefixos comuns do DOI
        if doi_clean.startswith("doi:"):
            doi_clean = doi_clean[4:]
        if doi_clean.startswith("https://doi.org/"):
            doi_clean = doi_clean[16:]
        if doi_clean.startswith("http://doi.org/"):
            doi_clean = doi_clean[15:]
        return f"doi_{hashlib.sha256(doi_clean.encode('utf-8')).hexdigest()}"
    
    # 2. Usar PMID para PubMed se disponível
    if pmid and str(pmid).strip() and source == "PubMed":
        return f"pmid_{hashlib.sha256(str(pmid).strip().encode('utf-8')).hexdigest()}"
    
    # 3. Usar Semantic Scholar ID se disponível
    if semantic_id and str(semantic_id).strip() and source == "Semantic Scholar":
        return f"s2_{hashlib.sha256(str(semantic_id).strip().encode('utf-8')).hexdigest()}"
    
    # 4. Usar URL para level1 se disponível
    if url and url.strip() and source == "level1":
        url_clean = url.strip().lower()
        return f"url_{hashlib.sha256(url_clean.encode('utf-8')).hexdigest()}"
    
    # 5. Fallback: usar hash do conteúdo com prefixo da fonte
    combined = f"{source}_{title_clean}_{text_clean}"
    content_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    return f"content_{content_hash}"


def extract_paper_attributes(paper, source):
    """Extract paper attributes based on the source API."""
    if source == "PubMed":
        year = paper.get("year", 0)
        if year == "No Year Available":
            year = 0
        return {
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "year": int(year),
            "source": "PubMed",
            "abstract": paper.get("abstract", ""),
            "keywords": paper.get("keywords", []),
            "doi": paper.get("doi", ""),
            "pmid": paper.get("pmid", ""),
            "journal": paper.get("journal", ""),
            "last_updated": paper.get("last_updated", "")
        }
    elif source == "Europe PMC":
        authors = paper.get("authorList", {}).get("author", [])
        authors = [f"{author.get('firstName', '')} {author.get('lastName', '')}" for author in authors]
        return {
            "title": paper.get("title", ""),
            "authors": authors,
            "year": int(paper.get("pubYear", 0) or 0),
            "source": "Europe PMC",
            "abstract": paper.get("abstractText", ""),
            "keywords": paper.get("keywordList", {}).get("keyword", []),
            "doi": paper.get("doi", ""),
            "pmid": paper.get("pmid", ""),  # Europe PMC também pode ter PMID
            "pmcid": paper.get("pmcid", ""),  # ID específico do PMC
            "journal": paper.get("journalInfo", {}).get("journal", {}).get("title", ""),
            "last_updated": paper.get("firstPublicationDate", "")
        }
    elif source == "Semantic Scholar":
        return {
            "title": paper.get("title", ""),
            "authors": [author.get("name", "") for author in paper.get("authors", [])],
            "year": int(paper.get("year", 0) or 0),
            "source": "Semantic Scholar",
            "abstract": paper.get("abstract", ""),
            "keywords": [],
            "doi": paper.get("externalIds", {}).get("DOI", ""),
            "pmid": paper.get("externalIds", {}).get("PubMed", ""),
            "semantic_id": paper.get("paperId", ""),
            "journal": paper.get("journal", {}).get("name", "") if paper.get("journal") else "",
            "last_updated": ""
        }
    elif source == "Google Scholar":
        authors = paper.get("authors", "No Authors")
        if isinstance(authors, list):
            authors = ", ".join(authors)
        return {
            "title": paper.get("title", ""),
            "authors": authors,
            "year": int(paper.get("year", 0) or 0),
            "source": "Google Scholar",
            "abstract": paper.get("abstract", ""),
            "keywords": paper.get("keywords", []),
            "doi": paper.get("doi", ""),
            "journal": paper.get("journal", ""),
            "last_updated": ""
        }
    elif source == "level1":
        return {
            "title": paper.get("title", ""),
            "source": paper.get("source", "Unknown Source"),
            "link": paper.get("link", ""),
            "content": paper.get("content", ""),
            "scraped_at": paper.get("accessed_at", "") or paper.get("date", "") or ""
        }
    else:
        raise ValueError(f"Unsupported source: {source}")


def save_doc_metadata_locally(doc_id, paper_data, filepath="data/inserted_docs.jsonl"):
    """Guarda os metadados principais do documento num ficheiro JSONL para verificação futura."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    record = {
        "doc_id": doc_id,
        "title": paper_data.get("title", ""),
        "year": paper_data.get("year", ""),
        "source": paper_data.get("source", ""),
        "doi": paper_data.get("doi", ""),
        "pmid": paper_data.get("pmid", ""),
        "semantic_id": paper_data.get("semantic_id", ""),
        "pmcid": paper_data.get("pmcid", ""),
        "timestamp": paper_data.get("scraped_at", "")
    }
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_local_doc_ids(filepath="data/inserted_docs.jsonl"):
    """Carrega os doc_ids já inseridos do ficheiro local."""
    if not os.path.exists(filepath):
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return {json.loads(line)["doc_id"] for line in f}


def check_cross_source_duplicates(paper_data, local_doc_ids):
    """
    Verifica duplicados entre diferentes fontes usando múltiplos identificadores.
    Retorna True se o documento já existe, False caso contrário.
    """
    identifiers_to_check = []
    
    # Gerar possíveis IDs que este documento poderia ter
    title = paper_data.get("title", "")
    abstract = paper_data.get("abstract", "") or paper_data.get("content", "")
    doi = paper_data.get("doi", "")
    pmid = paper_data.get("pmid", "")
    semantic_id = paper_data.get("semantic_id", "")
    url = paper_data.get("link", "")
    
    # Adicionar possíveis IDs baseados em diferentes identificadores
    if doi:
        identifiers_to_check.append(generate_doc_id(title, abstract, "any", doi=doi))
    if pmid:
        identifiers_to_check.append(generate_doc_id(title, abstract, "PubMed", pmid=pmid))
    if semantic_id:
        identifiers_to_check.append(generate_doc_id(title, abstract, "Semantic Scholar", semantic_id=semantic_id))
    
    # Verificar se algum destes IDs já existe
    for identifier in identifiers_to_check:
        if identifier in local_doc_ids:
            return True, identifier
    
    return False, None


def save_paper_to_pinecone(paper, source, index, local_doc_ids):
    """Save a single paper to Pinecone with improved duplication check."""
    paper_data = extract_paper_attributes(paper, source)

    if source == "level1":
        raw_text = paper_data["content"]
    else:
        raw_text = paper_data["abstract"]

    # Gerar ID usando a nova lógica melhorada
    doc_id = generate_doc_id(
        title=paper_data["title"],
        text=raw_text,
        source=source,
        doi=paper_data.get("doi"),
        pmid=paper_data.get("pmid"),
        semantic_id=paper_data.get("semantic_id"),
        url=paper_data.get("link")
    )

    # Verificação local básica
    if doc_id in local_doc_ids:
        print(f"Documento duplicado localmente: {doc_id} — será ignorado.")
        return

    # Verificação de duplicados entre fontes
    is_duplicate, existing_id = check_cross_source_duplicates(paper_data, local_doc_ids)
    if is_duplicate:
        print(f"Documento duplicado entre fontes: {doc_id} (já existe como {existing_id}) — será ignorado.")
        return

    # Verificação no Pinecone
    existing = index.fetch(ids=[f"{doc_id}_chunk_0"], namespace="ns1")
    if existing.vectors:
        print(f"Documento duplicado no Pinecone: {doc_id} — será ignorado.")
        return

    # Processar texto
    spacy_results = process_text(raw_text) if raw_text else {
        "entities": [], "matched_terms": {}, "chunks": [], "embeddings": np.zeros((0, 1024))
    }

    chunks = spacy_results["chunks"]
    embeddings = spacy_results["embeddings"]
    if len(chunks) != len(embeddings):
        print(f"Mismatch entre chunks ({len(chunks)}) e embeddings ({len(embeddings)}). Ignorado.")
        return

    vectors = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if embedding.shape != (1024,):
            print(f"Embedding inválido no chunk {i} de {doc_id}: {embedding.shape}")
            continue

        chunk_id = f"{doc_id}_chunk_{i}"
        hierarchy_level = 1 if source == "level1" else 2

        if source == "level1":
            metadata = {
                "hierarchy": hierarchy_level,
                "link": paper_data["link"],
                "text": chunk,
                "title": paper_data["title"],
                "topic": paper_data["title"],
                "year": ""
            }
        else:
            metadata = {
                "hierarchy": 2,
                "link": paper_data.get("doi", ""),
                "text": chunk,
                "title": paper_data["title"],
                "topic": paper_data.get("keywords", [])[0] if paper_data.get("keywords") else "",
                "year": str(paper_data["year"]) if paper_data["year"] else ""
            }

        vectors.append({
            "id": chunk_id,
            "values": embedding.tolist(),
            "metadata": metadata
        })

    if vectors:
        index.upsert(vectors=vectors, namespace="ns1")
        save_doc_metadata_locally(doc_id, paper_data)
        # Atualizar o conjunto local para incluir o novo doc_id
        local_doc_ids.add(doc_id)
        print(f"{len(vectors)} chunks inseridos para doc_id: {doc_id}")
    else:
        print(f"Nenhum chunk válido para doc_id: {doc_id}")


def save_to_pinecone(papers, source):
    """Save a list of papers to Pinecone with improved duplication protection."""
    if not papers:
        print("Nenhum artigo para guardar.")
        return

    index = configure_pinecone_connection()
    local_doc_ids = load_local_doc_ids()

    print(f"Iniciando processamento de {len(papers)} artigos de {source}")
    print(f"Documentos já existentes localmente: {len(local_doc_ids)}")

    for paper in tqdm(papers, desc=f"Salvando artigos de {source}"):
        save_paper_to_pinecone(paper, source, index, local_doc_ids)

    print(f"Todos os artigos de {source} foram processados.")


def analyze_duplicates(filepath="data/inserted_docs.jsonl"):
    """Função auxiliar para analisar duplicados existentes."""
    if not os.path.exists(filepath):
        print("Ficheiro de metadados não encontrado.")
        return

    docs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            docs.append(json.loads(line))

    print(f"Total de documentos: {len(docs)}")
    
    # Agrupar por DOI
    doi_groups = {}
    for doc in docs:
        doi = doc.get("doi", "").strip()
        if doi:
            if doi not in doi_groups:
                doi_groups[doi] = []
            doi_groups[doi].append(doc)
    
    # Encontrar DOIs com múltiplas entradas
    duplicates = {doi: docs_list for doi, docs_list in doi_groups.items() if len(docs_list) > 1}
    
    if duplicates:
        print(f"\nEncontrados {len(duplicates)} DOIs com duplicados:")
        for doi, docs_list in duplicates.items():
            print(f"DOI {doi}: {len(docs_list)} documentos de fontes: {[d['source'] for d in docs_list]}")
    else:
        print("Nenhum duplicado encontrado por DOI.")