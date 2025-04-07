import requests

from modules.mongoDB_utils import save_to_mongo_and_pinecone

def fetch_papers(query, num_results):
    """Fetch articles from the Semantic Scholar API."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": num_results,
        "fields": "title,authors,year,abstract,journal,externalIds" 
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

def search_semanticscholar(query, num_results, year_range=None):
    """Fetch articles from the Semantic Scholar API and save them to MongoDB."""
    papers = fetch_papers(query, num_results)
    save_to_mongo_and_pinecone(papers, "Semantic Scholar")
    return papers
