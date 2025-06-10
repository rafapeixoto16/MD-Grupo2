import json
from pathlib import Path
from dotenv import load_dotenv
from modules.pinecone_utils import save_to_pinecone

def load_json_list(json_file_path: Path) -> list:
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {json_file_path} not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: File {json_file_path} contains invalid JSON.")
        return []
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return []

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                return value

    return []

def process_and_index(json_file_path: Path, source_level: str):
    load_dotenv()
    items = load_json_list(json_file_path)
    if not items:
        return []

    print(f"   ✅ Encontrados {len(items)} itens em {json_file_path.name}.")
    save_to_pinecone(items, source_level)
    return items

def main():
    base = Path(__file__).parent / "trusted_data"

    all_items = []
    for fname in ["supplements_NIH.json", "data.json","farmacos_medlineplus.json","suplementos_medlineplus.json"]:
        path = base / fname
        items = process_and_index(path, source_level="level1")
        all_items.extend(items)

    print(f"Total: {len(all_items)}")

if __name__ == "__main__":
    main()
