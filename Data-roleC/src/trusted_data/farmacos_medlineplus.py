import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin
from datetime import datetime

BASE_URL = "https://medlineplus.gov/druginfo/"
INDEX_URL = BASE_URL + "drug_{}.html"

class MedlinePlusExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.processed_links = set()
    
    def search_drug_links(self, drug_name):
        """Procura links para um fármaco específico no MedlinePlus"""
        letter = drug_name[0].upper()
        page = f"{letter}a"
        url = INDEX_URL.format(page)
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            normalized_name = drug_name.strip().lower()
            found_links = set()
            
            for li in soup.find_all("li"):
                a_tag = li.find("a")
                span = li.find("span")
                
                if not a_tag:
                    continue
                
                href = a_tag.get("href", "")
                link_text = a_tag.text.strip().lower()
                
                if link_text == normalized_name:
                    full_url = urljoin(BASE_URL, href)
                    # Só adiciona se não foi processado antes
                    if full_url not in self.processed_links:
                        found_links.add(full_url)
                    continue
                
                if span:
                    span_text = span.text.strip().lower()
                    if span_text.replace(" ", "") == normalized_name + "see":
                        full_url = urljoin(BASE_URL, href)
                        # Só adiciona se não foi processado antes
                        if full_url not in self.processed_links:
                            found_links.add(full_url)
            
            return sorted(found_links)
        
        except Exception as e:
            print(f"Erro ao buscar links para {drug_name}: {e}")
            return []
    
    def extract_page_information(self, url):
        """Extrai informações estruturadas de uma página do farmaco do MedlinePlus"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extrair título principal
            title = ''
            title_tag = soup.find('h1', class_='with-also')
            if title_tag:
                title = title_tag.text.strip()
            
            # Extrair todo o conteúdo da página
            content = self._extract_complete_content(soup)
            
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
        date_spans = soup.find_all('span')
        for span in date_spans:
            if span.text.strip().startswith('Last Revised'):
                next_span = span.find_next_sibling('span')
                if next_span:
                    original_date = next_span.text.strip()
                    try:
                        date_obj = datetime.strptime(original_date, '%m/%d/%Y')
                        return date_obj.strftime('%d/%m/%Y')
                    except ValueError:
                        return original_date
        
        # Se não encontrar data, retorna data atual
        return datetime.now().strftime('%d/%m/%Y')
    
    def _extract_complete_content(self, soup):
        """Extrai todo o conteúdo corrido da página, como aparece no site"""
        content = ""
        
        # Encontrar todas as seções principais (excluindo brand names e other names)
        sections_to_exclude = ['brand-name-1','brand-name-2', 'brand-name-combination-products-1', 'other-name']
        
        sections = soup.find_all('section')
        
        for section in sections:
            section_div = section.find('div', class_='section')
            if section_div:
                section_id = section_div.get('id', '')
                if section_id in sections_to_exclude:
                    continue
            
            title_tag = section.find('h2')
            if title_tag:
                content += f"{title_tag.text.strip()} "
            
            section_body = section.find('div', class_='section-body')
            if section_body:
                content += self._process_content_elements(section_body)
        
        # Limpar o conteúdo final
        return self._clean_text(content)
    
    def _process_content_elements(self, container):
        """Processa elementos de conteúdo mantendo a estrutura original"""
        text = ""
        
        for element in container.find_all(['p', 'h3', 'ul', 'ol'], recursive=True):
            if element.name == 'p':
                paragraph = element.text.strip()
                if paragraph:  # Só adiciona se não estiver vazio
                    text += f"{paragraph} "
            
            elif element.name == 'h3':
                title = element.text.strip()
                if title:
                    text += f"{title}: "
            
            elif element.name == 'ul':
                for li in element.find_all('li'):
                    item = li.text.strip()
                    if item:
                        text += f"{item} "
            
            elif element.name == 'ol':
                for i, li in enumerate(element.find_all('li'), 1):
                    item = li.text.strip()
                    if item:
                        text += f"{i}. {item} "
        
        return text
    
    def _clean_text(self, text):
        """Limpa o texto extraído, removendo \n e espaços extras"""
        if not text:
            return ""
        
        text = text.replace('\n', ' ')
        text = re.sub(r' {2,}', ' ', text)        
        text = text.strip()
        
        return text
    
    def process_drug(self, drug_name, results_list):
        """Processa um fármaco completo: busca links e extrai informações"""
        
        # Buscar links
        links = self.search_drug_links(drug_name)
        
        if not links:
            return
        
        for link in links:
            print(f"  - {link}")
        
        # Processar todos os links encontrados
        for link in links:
            print(f"\nProcessando: {link}")
            information = self.extract_page_information(link)
            
            if information:
                # Adicionar às informações da lista
                results_list.append(information)
                
                # Marcar link como processado
                self.processed_links.add(link)
            
            # Pequena pausa para não sobrecarregar o servidor
            time.sleep(1)
    
    def save_information(self, pharmaceutical_list, filename):
        """Guarda as informações no formato JSON especificado"""
        try:
            final_data = {
                "pharmaceutical": pharmaceutical_list
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
            print(f"Informações guardadas em: {filename}")
        except Exception as e:
            print(f"Erro ao guardar ficheiro: {e}")

# Exemplo de uso
if __name__ == "__main__":
    extractor = MedlinePlusExtractor()
    
    # Lê os fármacos do ficheiro JSON
    try:
        with open("../terms/pharmaceutical.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            farmacos_list = data.get("pharmaceutical_terms", [])
    except Exception as e:
        print(f"Erro ao ler o ficheiro pharmaceutical.json: {e}")
        farmacos_list = []


    # Lista única para todos os resultados
    pharmaceutical_list = []
    
    for farmaco in farmacos_list:
        extractor.process_drug(farmaco, pharmaceutical_list)
    
    if pharmaceutical_list:
        extractor.save_information(pharmaceutical_list, "farmacos_medlineplus.json")
