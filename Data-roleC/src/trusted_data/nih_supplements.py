import time
from datetime import datetime
import json
import re
import requests
from bs4 import BeautifulSoup
import traceback

def format_url_name(name):
    formatted = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    formatted = ''.join(word.capitalize() for word in formatted.split())
    return formatted

def check_page_exists(response):
    try:
        if response.status_code != 200:
            print(f"Página retornou status code: {response.status_code}")
            return False
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Verificar pelo título
        title_element = soup.find('title')
        if title_element and "404" in title_element.text:
            print(f"Error in page title: {title_element.text}")
            return False
            
        error_elements = soup.find_all(class_="error-page")
        if error_elements:
            print("Found error page container")
            return False
            
        content_elements = soup.find_all("article")
        if content_elements:
            return True
            
        fact_sheet = soup.find(id="fact-sheet")
        if fact_sheet:
            return True
            
        h1_elements = soup.find_all("h1")
        if h1_elements and len(h1_elements[0].text.strip()) > 0:
            return True
            
        main_content = soup.find("main")
        if main_content:
            return True
            
        return False
            
    except Exception as e:
        print(f"Error checking page existence: {str(e)}")
        traceback.print_exc()
        return False

def clean_text(text):
    """Remove citações e \n """
    cleaned_text = re.sub(r'\[\s*\d+(?:\s*,\s*\d+)*\s*\]', '', text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    cleaned_text = cleaned_text.replace('\n', ' ')
    return cleaned_text

def process_table(table_element):
    caption = table_element.find('caption')
    table_caption = caption.get_text().strip() if caption else "Tabela"
    
    # Linhas do cabeçalho
    headers = []
    thead = table_element.find('thead')
    if thead:
        for th in thead.find_all('th'):
            headers.append(clean_text(th.get_text().strip()))
    
    # Linhas de dados
    rows = []
    tbody = table_element.find('tbody')
    if tbody:
        tr_elements = tbody.find_all('tr')
    else:
        tr_elements = table_element.find_all('tr')
    
    for tr in tr_elements:
        row_data = [clean_text(td.get_text().strip()) for td in tr.find_all('td')]
        if not row_data:
            continue
        rows.append(row_data)
    
    text_output = [clean_text(table_caption)]
        
    # Converter cada linha em texto natural
    for row in rows:
        if len(row) >= 2:
            item_name = row[0]
            value_parts = []
            for i, cell in enumerate(row[1:], start=1):
                if i < len(headers):
                    value_parts.append(f"{headers[i]}: {cell}")
                else:
                    value_parts.append(cell)
            sentence = f"{item_name}: {', '.join(value_parts)}"
            text_output.append(sentence)
        else:
            text_output.append(f"{row[0]}")
    
    return " ".join(text_output)

def extract_all_text(article):
    text_parts = []
    
    for element in article.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li', 'table']):
        if element.name == 'table':
            text_parts.append(process_table(element))
        else:
            text = clean_text(element.get_text().strip())
            if text:
                text_parts.append(text)
    
    return " ".join(text_parts)

def scrape_article_content(soup):
    article = soup.find('article') or soup.find('div', id='fact-sheet')
    
    if not article:
        return None
    
    article_copy = BeautifulSoup(str(article), 'html.parser')
    
    for section_id in ['ref', 'disc', 'divCitations', 'divDisclaimer']:
        reference_sections = article_copy.find_all(['section', 'div'], id=lambda x: x and section_id in x)
        for section in reference_sections:
            section.extract()
    
    for header in article_copy.find_all(['h2']):
        header_text = header.get_text().lower()
        if 'reference' in header_text or 'disclaimer' in header_text or 'table of contents' in header_text:
            current = header
            while current and current.name != 'h2':
                next_elem = current.find_next_sibling()
                current.extract()
                current = next_elem
            header.extract()
    
    return extract_all_text(article_copy)

def scrape_supplement_page(url, supplement_name):
    print(f"\nURL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        final_url = response.url

        if not check_page_exists(response):
            print(f"A página para {supplement_name} não existe.")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        content = scrape_article_content(soup)
        
        if content:
            simplified_content = {
                "title": supplement_name,
                "link": final_url,
                "source": "NIH",
                "accessed_at": datetime.now().isoformat(),  
                "content": content
            }
            return simplified_content
        else:
            print(f"Não foi possível extrair o conteúdo para {supplement_name}")
            return None
            
    except Exception as e:
        print(f"Erro durante o scraping: {str(e)}")
        traceback.print_exc()
        return None

def process_supplements(supplement_file, output_file="supplements_NIH.json.json"):
    with open(supplement_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    import os
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
    else:
        saved_data = {"supplements": []}

    processed_names = {s['title'] for s in saved_data.get("supplements", [])}

    supplements = data.get("supplement_terms", [])
    success_count = 0
    fail_count = 0

    try:
        for i, supplement in enumerate(supplements):
            if supplement in processed_names:
                print(f"\n[{i+1}/{len(supplements)}] Já processado: {supplement}.")
                continue

            print(f"\n[{i+1}/{len(supplements)}] A processar: {supplement}")
            url_name = format_url_name(supplement)
            url = f"https://ods.od.nih.gov/factsheets/{url_name}-HealthProfessional"

            content = scrape_supplement_page(url, supplement)

            if content:
                saved_data["supplements"].append(content)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(saved_data, f, ensure_ascii=False, indent=2)

                success_count += 1
                print(f"Scraping feito para {supplement}.")
            else:
                fail_count += 1
                print(f"Falha ao fazer o scraping de {supplement}.")

            time.sleep(2)

    except Exception as e:
        print(f"Erro ao processar suplementos: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    supplement_file = "../terms/supplement.json"
    output_file = "supplements_NIH.json"
    
    process_supplements(supplement_file, output_file)