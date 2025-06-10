import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime

BASE_URL = "https://medlineplus.gov/druginfo/"
HERBS_INDEX_URL = BASE_URL + "herb_All.html#{}"

class MedlinePlusSupplementsExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.processed_links = set()
    
    def is_medlineplus_link(self, url):
        parsed_url = urlparse(url)
        # Aceita apenas links relativos ou do domínio medlineplus.gov
        return not parsed_url.netloc or parsed_url.netloc == 'medlineplus.gov'
    
    def search_supplement_links(self, supplement_name):
        """Procura links para um suplemento específico no MedlinePlus"""
        letter = supplement_name[0].upper()
        url = HERBS_INDEX_URL.format(letter)
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            normalized_name = supplement_name.strip().lower()
            found_links = set()
            
            # Procurar na lista de suplementos
            for li in soup.find_all("li"):
                a_tag = li.find("a")
                
                if not a_tag:
                    continue
                
                href = a_tag.get("href", "")
                link_text = a_tag.text.strip().lower()
                
                # Verificar se é um link do MedlinePlus
                if not self.is_medlineplus_link(href):
                    continue
                
                # Comparação exata do nome
                if link_text == normalized_name:
                    full_url = urljoin(BASE_URL, href)
                    # Só adiciona se não foi processado antes
                    if full_url not in self.processed_links:
                        found_links.add(full_url)
                    continue
                
                span = li.find("span")
                if span:
                    span_text = span.text.strip().lower()
                    if span_text.replace(" ", "") == normalized_name + "see":
                        full_url = urljoin(BASE_URL, href)
                        if full_url not in self.processed_links:
                            found_links.add(full_url)
            
            return sorted(found_links)
        
        except Exception as e:
            return []
    
    def extract_page_information(self, url):
        """Extrai informações estruturadas de uma página do suplemento do MedlinePlus"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extrair título principal
            title = ''
            title_tag = soup.find('h1', class_='with-also')
            if title_tag:
                title = title_tag.text.strip()
            
            # Extrair apenas o conteúdo relevante (sem referências)
            content = self._extract_relevant_content(soup)
            
            # Extrair data de revisão
            date = self._extract_and_format_date(soup)
            
            information = {
                'title': title,
                'link': url,
                'source': 'MedlinePlus',
                'date': date,
                'content': content
            }
            
            return information
            
        except Exception as e:
            print(f"Erro ao extrair informações de {url}: {e}")
            return None
    
    def _extract_and_format_date(self, soup):
        """Extrai e formata a data de revisão"""
        lastreview_div = soup.find('div', class_='lastreview')
        
        if lastreview_div:
            full_text = lastreview_div.get_text(strip=True)
            date_pattern = r'(\d{2}/\d{2}/\d{4})'
            match = re.search(date_pattern, full_text)
            
            if match:
                original_date = match.group(1)
                try:
                    # Converter de MM/DD/YYYY para DD/MM/YYYY
                    date_obj = datetime.strptime(original_date, '%m/%d/%Y')
                    formatted_date = date_obj.strftime('%d/%m/%Y')
                    return formatted_date
                except ValueError as e:
                    return original_date
        return datetime.now().strftime('%d/%m/%Y')


    def _extract_relevant_content(self, soup):
        """Extrai apenas o conteúdo relevante, excluindo referências e secções desnecessárias"""
        content = ""
        
        sections_to_exclude = [
            'brand-name-1', 'brand-name-2', 'brand-name-combination-products-1',
            'References', 'method', 'OtherNames'  
        ]
        
        section_ids_to_exclude = [
            'References', 'method', 'OtherNames'
        ]
        
        sections = soup.find_all('section')
        
        for section in sections:
            # Verificar se é uma secção a excluir por ID
            section_div = section.find('div', class_='section')
            if section_div:
                section_id = section_div.get('id', '')
                if section_id in section_ids_to_exclude:
                    continue
            
            # Verificar se o título da secção está na lista de exclusão
            title_tag = section.find('h2')
            if title_tag:
                title_text = title_tag.text.strip()
                if title_text in sections_to_exclude:
                    continue
                
                # Incluir apenas secções relevantes
                relevant_sections = [
                    'What is it?', 'How effective is it?', 'Is it safe?',
                    'Are there interactions with medications?',
                    'Are there interactions with herbs and supplements?',
                    'Are there interactions with foods?',
                    'How is it typically used?'
                ]
                
                if title_text in relevant_sections:
                    content += f"{title_text}: "
                    
                    section_body = section.find('div', class_='section-body')
                    if section_body:
                        content += self._process_content_elements(section_body)
        
        return self._clean_text(content)
    
    def _process_content_elements(self, container):
        text = ""
        
        direct_text = self._extract_direct_text(container)
        if direct_text.strip():
            text += direct_text + " "
        
        for element in container.find_all(['h3', 'ul', 'ol', 'dl'], recursive=False):
            if element.name == 'h3':
                title = element.get_text(strip=True)
                if title:
                    text += f"{title}: "
            
            elif element.name == 'ul':
                for li in element.find_all('li'):
                    item = li.get_text(strip=True)
                    if item:
                        text += f"{item} "
            
            elif element.name == 'ol':
                for i, li in enumerate(element.find_all('li'), 1):
                    item = li.get_text(strip=True)
                    if item:
                        text += f"{i}. {item} "
            
            elif element.name == 'dl':
                for dt in element.find_all('dt'):
                    term = dt.get_text(strip=True)
                    if term:
                        text += f"{term}: "
                    
                    dd = dt.find_next_sibling('dd')
                    if dd:
                        definition = dd.get_text(strip=True)
                        if definition:
                            text += f"{definition} "
        
        return text
    
    def _extract_direct_text(self, container):
        temp_container = container.__copy__()
        
        for element in temp_container.find_all(['h3', 'ul', 'ol', 'dl']):
            element.decompose()
        
        text = temp_container.get_text(separator=' ', strip=True)
        return text
    
    
    def _clean_text(self, text):
        "Limpa o texto extraído"
        if not text:
            return ""
        
        text = re.sub(r'<br\s*/?>', ' ', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
        text = re.sub(r' {2,}', ' ', text)        
        text = re.sub(r'[\t\f\v]', ' ', text)
        
        text = text.strip()
        
        return text
    
    def process_supplement(self, supplement_name, results_list):
        """Processa um suplemento: procura links e extrai informações"""
        
        print(f"\n=== A processar suplemento: {supplement_name} ===")
        
        # Buscar links
        links = self.search_supplement_links(supplement_name)
        
        if not links:
            print(f"Nenhum link encontrado para: {supplement_name}")
            return
        
        print(f"Links encontrados para {supplement_name}:")
        for link in links:
            print(f"  - {link}")
            
        
        # Processar todos os links encontrados
        for link in links:
            information = self.extract_page_information(link)
            
            if information:
                # Adicionar às informações da lista
                results_list.append(information)
                
                # Marcar link como processado
                self.processed_links.add(link)
            else:
                print(f"✗ Falha ao extrair informações")
            
            # Pequena pausa para não sobrecarregar o servidor
            time.sleep(1)
    
    def save_information(self, supplements_list, filename):
        try:
            final_data = {
                "supplements": supplements_list
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
            print(f"\nInformações guardadas em: {filename}")
            print(f"Total de suplementos processados: {len(supplements_list)}")
        except Exception as e:
            print(f"Erro ao guardar ficheiro: {e}")

if __name__ == "__main__":
    extractor = MedlinePlusSupplementsExtractor()
    
    # Lê os suplementos do ficheiro JSON
    try:
        with open("../terms/supplement.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            supplements_list = data.get("supplement_terms", [])
    except Exception as e:
        print(f"Erro ao ler o ficheiro supplement.json: {e}")

    # Lista única para todos os resultados
    supplements_results = []
    
    print(f"A processar {len(supplements_list)} suplementos...")
    
    for supplement in supplements_list:
        extractor.process_supplement(supplement, supplements_results)
    
    if supplements_results:
        extractor.save_information(supplements_results, "suplementos_medlineplus.json")
    else:
        print("Nenhuma informação foi extraída.")