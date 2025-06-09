from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from modules.europePMC_utils import search_europe_pmc
from modules.googleScholar_utils import search_google_scholar
from modules.pubmed_utils import search_pubmed
from modules.semanticscholar_utils import search_semanticscholar
from modules.wikipedia_utils import search_wikipedia
from modules.menu_utils import (
    VITAMIN_QUERIES, 
    display_vitamin_queries, 
    select_query, 
    display_enhanced_menu,
    display_source_selection_menu,
    get_source_map,
    get_sources_dict,
    display_batch_confirmation
)

def search_google_scholar_batch(query, num_documents=10):
    """Searches Google Scholar for a specified number of documents with timeout and error handling."""
    console = Console()
    console.print(f"\n[bold cyan]🔎 Searching Google Scholar for {num_documents} documents...[/bold cyan]")
    console.print(f"[bold white]Query:[/bold white] {query}")
    
    try:
        # Add timeout and better error handling
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Google Scholar search timed out")
        
        # Set timeout of 30 seconds
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)
        
        try:
            results = search_google_scholar(query, num_documents, (2020, 2025))
            signal.alarm(0)  # Cancel timeout
            
            if results:
                console.print(f"\n[bold green]✅ Found {len(results)} results from Google Scholar[/bold green]")
                for i, result in enumerate(results, 1):
                    console.print(f"\n[bold yellow]📄 Document {i}:[/bold yellow]")
                    console.print(f"[bold]Title:[/bold] {result.get('title', 'N/A')}")
                    console.print(f"[bold]Authors:[/bold] {result.get('authors', 'N/A')}")
                    console.print(f"[bold]Year:[/bold] {result.get('year', 'N/A')}")
                    console.print(f"[bold]Citation Count:[/bold] {result.get('citation_count', 'N/A')}")
                    console.print(f"[bold]URL:[/bold] [blue]{result.get('url', 'N/A')}[/blue]")
                    if result.get('abstract'):
                        console.print(f"[bold]Abstract:[/bold] {result['abstract'][:200]}...")
            else:
                console.print("[bold red]❌ No results found[/bold red]")
                
        except TimeoutError:
            signal.alarm(0)
            console.print("[bold red]⏰ Search timed out (30 seconds). Try a simpler query or check your connection.[/bold red]")
            return []
            
        return results if results else []
        
    except Exception as e:
        console.print(f"[bold red]❌ Error searching Google Scholar: {str(e)}[/bold red]")
        console.print("[bold yellow]💡 Try using a different source or simplifying your query[/bold yellow]")
        return []

def test_google_scholar_connection():
    """Tests if Google Scholar is accessible."""
    console = Console()
    console.print("[bold cyan]🔍 Testing Google Scholar connection...[/bold cyan]")
    
    try:
        # Simple test query
        test_query = "vitamin D"
        results = search_google_scholar(test_query, 1, (2020, 2025))
        
        if results:
            console.print("[bold green]✅ Google Scholar connection successful[/bold green]")
            return True
        else:
            console.print("[bold yellow]⚠️ Google Scholar returned no results for test query[/bold yellow]")
            return False
            
    except Exception as e:
        console.print(f"[bold red]❌ Google Scholar connection failed: {str(e)}[/bold red]")
        console.print("[bold yellow]💡 Suggestions:[/bold yellow]")
        console.print("  - Check your internet connection")
        console.print("  - Try using PubMed or other sources instead")
        console.print("  - Google Scholar may be temporarily unavailable")
        return False

def search_all_vitamin_queries(num_documents_per_query=5, source_choice="google_scholar"):
    """Executes all vitamin queries at once."""
    console = Console()
    
    console.print(f"\n[bold magenta]🚀 Starting batch search of ALL {len(VITAMIN_QUERIES)} research queries![/bold magenta]")
    console.print(f"[bold white]Documents per query:[/bold white] {num_documents_per_query}")
    console.print(f"[bold white]Source:[/bold white] {source_choice.replace('_', ' ').title()}")
    
    all_results = {}
    total_found = 0
    
    # Progress tracking
    console.print(f"\n[bold cyan]📊 Progress: 0/{len(VITAMIN_QUERIES)} queries completed[/bold cyan]")
    
    for i, query in enumerate(VITAMIN_QUERIES, 1):
        console.print(f"\n[bold blue]{'='*60}[/bold blue]")
        console.print(f"[bold white]Query {i}/{len(VITAMIN_QUERIES)}:[/bold white] {query}")
        console.print(f"[bold blue]{'='*60}[/bold blue]")
        
        try:
            if source_choice == "google_scholar":
                results = search_google_scholar(query, num_documents_per_query, (2020, 2025))
            elif source_choice == "pubmed":
                results = search_pubmed(query, num_documents_per_query, (2020, 2025))
            elif source_choice == "europe_pmc":
                results = search_europe_pmc(query, num_documents_per_query, (2020, 2025))
            elif source_choice == "semantic_scholar":
                results = search_semanticscholar(query, num_documents_per_query, (2020, 2025))
            else:
                results = []
            
            query_key = f"Query_{i:02d}"
            all_results[query_key] = {
                'query': query,
                'results': results if results else [],
                'count': len(results) if results else 0
            }
            
            found_count = len(results) if results else 0
            total_found += found_count
            
            if found_count > 0:
                console.print(f"[bold green]✅ Found {found_count} documents[/bold green]")
                # Show just titles for summary
                for j, result in enumerate(results[:3], 1):  # Show only first 3 titles
                    console.print(f"  {j}. {result.get('title', 'N/A')[:80]}...")
                if found_count > 3:
                    console.print(f"  ... and {found_count - 3} more documents")
            else:
                console.print("[bold red]❌ No results found[/bold red]")
        
        except Exception as e:
            console.print(f"[bold red]❌ Error with query {i}: {str(e)}[/bold red]")
            all_results[f"Query_{i:02d}"] = {
                'query': query,
                'results': [],
                'count': 0,
                'error': str(e)
            }
        
        # Update progress
        console.print(f"[bold cyan]📊 Progress: {i}/{len(VITAMIN_QUERIES)} queries completed | Total documents found: {total_found}[/bold cyan]")
        
        # Optional: Add a small delay to avoid overwhelming the API
        import time
        time.sleep(1)
    
    # Final summary
    console.print(f"\n[bold green]🎉 BATCH SEARCH COMPLETED![/bold green]")
    console.print(f"[bold white]Total queries processed:[/bold white] {len(VITAMIN_QUERIES)}")
    console.print(f"[bold white]Total documents found:[/bold white] {total_found}")
    
    # Summary table
    summary_table = Table(title="📈 Search Results Summary", show_header=True, header_style="bold green")
    summary_table.add_column("Query #", style="dim", width=8)
    summary_table.add_column("Documents Found", style="cyan", width=15)
    summary_table.add_column("Query Preview", style="white")
    
    for key, data in all_results.items():
        query_num = key.split('_')[1]
        preview = data['query'][:60] + "..." if len(data['query']) > 60 else data['query']
        count_str = str(data['count']) if 'error' not in data else f"ERROR: {data.get('count', 0)}"
        summary_table.add_row(query_num, count_str, preview)
    
    console.print(summary_table)
    
    # Option to save results
    save_option = Prompt.ask("\n[bold white]Do you want to save results to a file? (y/n)[/bold white]", default="n")
    if save_option.lower() == 'y':
        save_batch_results(all_results, source_choice)
    
    return all_results

def save_batch_results(results, source_name):
    """Saves batch search results to a file."""
    import json
    from datetime import datetime
    
    console = Console()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"research_batch_{source_name}_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        console.print(f"[bold green]💾 Results saved to: {filename}[/bold green]")
        
        # Also create a summary CSV
        csv_filename = f"research_summary_{source_name}_{timestamp}.csv"
        import csv
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Query_Number', 'Query', 'Documents_Found', 'Status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for key, data in results.items():
                writer.writerow({
                    'Query_Number': key.split('_')[1],
                    'Query': data['query'],
                    'Documents_Found': data['count'],
                    'Status': 'ERROR' if 'error' in data else 'SUCCESS'
                })
        
        console.print(f"[bold green]📊 Summary saved to: {csv_filename}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error saving files: {str(e)}[/bold red]")

def search_and_print(source, func, query, max_articles=1, year_range=(2020, 2025)):
    """Performs the search and prints the results."""
    console = Console()
    console.print(f"\n[bold cyan]🔎 Searching on {source}...[/bold cyan]")
    
    try:
        results = func(query) if source == "Wikipedia" else func(query, max_articles, year_range)
        
        if source == "Wikipedia" and results:
            console.print(f"\n[bold yellow]📖 Wikipedia: {results['title']}[/bold yellow]")
            console.print(f"🔗 [blue]{results['url']}[/blue]")
            console.print(f"📝 {results['summary']}")
        elif results:
            console.print(f"[bold green]✅ Found {len(results) if isinstance(results, list) else 1} results from {source}[/bold green]")
        else:
            console.print(f"[bold red]❌ No results found on {source}[/bold red]")
    
    except Exception as e:
        console.print(f"[bold red]❌ Error searching {source}: {str(e)}[/bold red]")
        results = []
    
    return results

def handle_batch_mode():
    """Handles the batch mode execution logic."""
    console = Console()
    console.print("\n[bold magenta]🚀 BATCH MODE: Execute All Research Queries[/bold magenta]")
    
    # Choose source
    source_options = display_source_selection_menu()
    source_choice = Prompt.ask("[bold white]Select source for batch search[/bold white]", default="1")
    source_map = get_source_map()
    
    if source_choice in source_map:
        selected_source = source_map[source_choice]
        num_docs_per_query = int(Prompt.ask("[bold white]Documents per query (recommended: 3-5)[/bold white]", default="5"))
        
        # Confirmation
        confirm = display_batch_confirmation(len(VITAMIN_QUERIES), selected_source, num_docs_per_query)
        if confirm.lower() == 'y':
            search_all_vitamin_queries(num_docs_per_query, selected_source)
        else:
            console.print("[bold yellow]🔄 Batch search cancelled[/bold yellow]")
    else:
        console.print("[bold red]❌ Invalid source selection[/bold red]")

def handle_single_source_search(choice, sources):
    """Handles single source search logic."""
    source_name, search_func = sources[choice]
     
    if source_name == "Wikipedia":
        query = Prompt.ask("[bold white]Enter a search term:[/bold white]")
        search_and_print(source_name, search_func, query)
    else:
        query = select_query()
        max_articles = int(Prompt.ask("[bold white]How many articles?[/bold white]", default="1"))
        search_and_print(source_name, search_func, query, max_articles)

def handle_all_sources_search(sources):
    """Handles searching all sources."""
    query = select_query()
    max_articles = int(Prompt.ask("[bold white]How many articles per source?[/bold white]", default="1"))
    
    for key, (source_name, search_func) in sources.items():
        if key != "4" and key != "6":  # Exclude Wikipedia and All Sources
            search_and_print(source_name, search_func, query, max_articles)

def main():
    """Runs searches based on user choice."""
    console = Console()
    console.print("\n[bold green]🧬 Welcome to the Enhanced Research Tool for Preventive Pharmacology![/bold green]\n")
    
    sources = get_sources_dict()
    
    while True:
        choice = display_enhanced_menu()
        
        if choice.lower() == 'q':
            console.print("\n[bold red]🚪 Exiting... Thank you for using the Research Tool![/bold red]")
            break
            
        elif choice.lower() == 't':
            # Test Google Scholar connection
            test_google_scholar_connection()
            
        elif choice == "7":
            # Google Scholar batch search with queries
            query = select_query()
            num_docs = int(Prompt.ask("[bold white]How many documents to retrieve?[/bold white]", default="10"))
            search_google_scholar_batch(query, num_docs)
            
        elif choice == "9":
            # Execute ALL research queries at once
            handle_batch_mode()
            
        elif choice == "8":
            # View research queries list
            display_vitamin_queries()
            
        elif choice in sources:
            if choice == "6":
                # Search all sources
                handle_all_sources_search(sources)
            else:
                # Individual source search
                handle_single_source_search(choice, sources)
        else:
            console.print("\n[bold red]❌ Invalid choice! Please select a valid option.[/bold red]")

if __name__ == "__main__":
    main()