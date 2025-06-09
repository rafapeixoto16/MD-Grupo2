import pinecone
from pinecone import Pinecone
import os
from typing import List, Optional, Dict
from collections import defaultdict
from datetime import datetime
import json

def setup_pinecone(api_key: str) -> Pinecone:
    """
    Configura a conexão com o Pinecone
    """
    pc = Pinecone(api_key=api_key)
    return pc

def generate_debug_report(duplicates: dict, output_file: str = None) -> str:
    """
    Gera um relatório detalhado dos duplicados em formato texto
    
    Args:
        duplicates: Dicionário com os duplicados encontrados
        output_file: Nome do arquivo (opcional, senão gera automaticamente)
    
    Returns:
        str: Caminho do arquivo gerado
    """
    
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"pinecone_duplicates_debug_{timestamp}.txt"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Cabeçalho do relatório
            f.write("=" * 80 + "\n")
            f.write("RELATÓRIO DETALHADO DE REGISTOS DUPLICADOS - PINECONE\n")
            f.write("=" * 80 + "\n")
            f.write(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total de grupos duplicados: {len(duplicates)}\n")
            
            total_to_delete = sum(len(info['to_delete']) for info in duplicates.values())
            f.write(f"Total de registos a apagar: {total_to_delete}\n")
            f.write("=" * 80 + "\n\n")
            
            # Sumário executivo
            f.write("SUMÁRIO EXECUTIVO\n")
            f.write("-" * 40 + "\n")
            for i, (text, info) in enumerate(duplicates.items(), 1):
                preview = text[:100].replace('\n', ' ').replace('\r', ' ')
                f.write(f"{i:3d}. Texto: \"{preview}{'...' if len(text) > 100 else ''}\"\n")
                f.write(f"     Cópias: {info['count']} | A apagar: {len(info['to_delete'])}\n\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write("DETALHES COMPLETOS POR GRUPO\n")
            f.write("=" * 80 + "\n\n")
            
            # Detalhes de cada grupo duplicado
            for i, (text, info) in enumerate(duplicates.items(), 1):
                f.write(f"GRUPO DUPLICADO #{i:03d}\n")
                f.write("-" * 60 + "\n")
                f.write(f"Total de cópias encontradas: {info['count']}\n")
                f.write(f"Registos a apagar: {len(info['to_delete'])}\n")
                f.write(f"Registo a manter: 1\n\n")
                
                # Texto completo
                f.write("TEXTO COMPLETO:\n")
                f.write("~" * 40 + "\n")
                f.write(f"{text}\n")
                f.write("~" * 40 + "\n\n")
                
                # Registo a manter
                keep_record = info['to_keep']
                f.write("🔒 REGISTO A MANTER:\n")
                f.write(f"   ID: {keep_record['id']}\n")
                f.write(f"   Score: {keep_record['score']:.6f}\n")
                
                if keep_record.get('full_metadata'):
                    f.write("   Metadata completa:\n")
                    for key, value in keep_record['full_metadata'].items():
                        if key != 'text':  # Texto já mostrado acima
                            f.write(f"      {key}: {value}\n")
                f.write("\n")
                
                # Registos a apagar
                f.write("🗑️  REGISTOS A APAGAR:\n")
                for j, record in enumerate(info['to_delete'], 1):
                    f.write(f"   [{j}] ID: {record['id']}\n")
                    f.write(f"       Score: {record['score']:.6f}\n")
                    if record.get('full_metadata'):
                        f.write("       Metadata completa:\n")
                        for key, value in record['full_metadata'].items():
                            if key != 'text':  # Texto já mostrado acima
                                f.write(f"          {key}: {value}\n")
                    f.write("\n")
                
                f.write("\n" + "=" * 60 + "\n\n")
            
            # Rodapé com comandos para eliminação
            f.write("COMANDOS PARA ELIMINAÇÃO\n")
            f.write("-" * 40 + "\n")
            f.write("IDs a apagar (para uso manual):\n")
            all_ids_to_delete = []
            for info in duplicates.values():
                for record in info['to_delete']:
                    all_ids_to_delete.append(record['id'])
            
            f.write("[\n")
            for id_val in all_ids_to_delete:
                f.write(f"  '{id_val}',\n")
            f.write("]\n\n")
            
            f.write(f"Total de IDs: {len(all_ids_to_delete)}\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("FIM DO RELATÓRIO\n")
            f.write("=" * 80 + "\n")
        
        print(f"📄 Relatório detalhado gerado: {output_file}")
        return output_file
    
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {str(e)}")
        return None

def find_duplicate_records_with_debug(
    index_name: str,
    api_key: str,
    namespace: str = "",
    max_results: int = 10000,
    generate_debug_file: bool = True,
    debug_filename: str = None
) -> dict:
    """
    Encontra todos os registos duplicados e gera relatório detalhado
    
    Args:
        index_name: Nome do índice Pinecone
        api_key: Chave API do Pinecone
        namespace: Namespace (opcional)
        max_results: Número máximo de resultados a processar
        generate_debug_file: Se deve gerar arquivo de debug
        debug_filename: Nome personalizado para o arquivo de debug
    
    Returns:
        dict: Informação sobre duplicados encontrados + caminho do arquivo debug
    """
    
    # Configurar Pinecone
    pc = setup_pinecone(api_key)
    index = pc.Index(index_name)
    
    text_groups = defaultdict(list)  # Agrupa registos por texto
    total_processed = 0
    
    try:
        # Obter estatísticas do índice
        stats = index.describe_index_stats()
        total_vectors = stats.total_vector_count
        
        # Tentar obter a dimensão do índice (método mais seguro)
        try:
            index_info = pc.describe_index(index_name)
            dimension = index_info.dimension
            print(f"📐 Dimensão do índice detectada: {dimension}")
        except:
            # Fallback para dimensão comum
            dimension = 1024
            print(f"📐 Usando dimensão padrão: {dimension}")
        
        print(f"📊 Total de vetores no índice: {total_vectors}")
        print(f"🔍 A procurar registos duplicados...")
        print("-" * 50)
        
        # Criar um vetor dummy para query
        dummy_vector = [0.0] * dimension
        
        # Query para obter todos os registos
        query_response = index.query(
            vector=dummy_vector,
            top_k=max_results,
            include_metadata=True,
            namespace=namespace
        )
        
        # Agrupar registos por texto
        for match in query_response.matches:
            total_processed += 1
            
            if match.metadata and 'text' in match.metadata:
                text_content = match.metadata['text']
                
                record_info = {
                    'id': match.id,
                    'score': match.score,
                    'text': text_content,
                    'full_metadata': match.metadata
                }
                
                text_groups[text_content].append(record_info)
        
        # Encontrar duplicados
        duplicates = {}
        total_duplicates = 0
        
        for text, records in text_groups.items():
            if len(records) > 1:
                # Ordenar por score (maior primeiro) para escolha melhor do que manter
                records.sort(key=lambda x: x['score'], reverse=True)
                
                duplicates[text] = {
                    'records': records,
                    'count': len(records),
                    'to_delete': records[1:],  # Manter o primeiro (maior score), apagar os outros
                    'to_keep': records[0]
                }
                total_duplicates += len(records) - 1  # -1 porque mantemos um
        
        # Gerar arquivo de debug se solicitado
        debug_file_path = None
        if generate_debug_file and duplicates:
            print(f"\n📄 A gerar relatório detalhado de debug...")
            debug_file_path = generate_debug_report(duplicates, debug_filename)
        
        # Mostrar resultados na consola
        if not duplicates:
            print("✅ Nenhum registo duplicado encontrado!")
        else:
            print(f"⚠️  DUPLICADOS ENCONTRADOS:")
            print(f"   • Textos únicos com duplicados: {len(duplicates)}")
            print(f"   • Total de registos duplicados a apagar: {total_duplicates}")
            
            if debug_file_path:
                print(f"   • Relatório detalhado salvo em: {debug_file_path}")
            
            print("-" * 50)
            
            # Preview dos primeiros duplicados
            print("\n🔍 PREVIEW DOS PRIMEIROS DUPLICADOS:")
            for i, (text, info) in enumerate(list(duplicates.items())[:3], 1):
                print(f"\n📝 DUPLICADO #{i}:")
                preview = text[:150].replace('\n', ' ').replace('\r', ' ')
                print(f"   Texto: \"{preview}{'...' if len(text) > 150 else ''}\"")
                print(f"   Total de cópias: {info['count']}")
                print(f"   🔒 MANTER: ID {info['to_keep']['id']} (score: {info['to_keep']['score']:.4f})")
                print(f"   🗑️  APAGAR: {len(info['to_delete'])} registos")
            
            if len(duplicates) > 3:
                print(f"\n... e mais {len(duplicates) - 3} grupos duplicados.")
                print(f"📄 Veja o arquivo '{debug_file_path}' para detalhes completos.")
        
        return {
            "success": True,
            "duplicates": duplicates,
            "total_duplicate_groups": len(duplicates),
            "total_records_to_delete": total_duplicates,
            "total_processed": total_processed,
            "debug_file": debug_file_path
        }
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "duplicates": {},
            "total_records_to_delete": 0,
            "debug_file": None
        }

def delete_duplicate_records(
    index_name: str,
    api_key: str,
    namespace: str = "",
    batch_size: int = 100,
    confirm: bool = False,
    keep_strategy: str = "highest_score"  # Mudamos default para highest_score
) -> dict:
    """
    Apaga registos duplicados mantendo apenas um de cada texto
    ATENÇÃO: Esta função APAGA os registos permanentemente!
    
    Args:
        index_name: Nome do índice Pinecone
        api_key: Chave API do Pinecone
        namespace: Namespace (opcional)
        batch_size: Tamanho do lote para processamento
        confirm: Deve ser True para confirmar a eliminação
        keep_strategy: Qual registo manter ("first", "last", "highest_score")
    
    Returns:
        dict: Resultado da operação com estatísticas
    """
    
    if not confirm:
        return {
            "success": False,
            "message": "❌ Operação cancelada. Use confirm=True para confirmar a eliminação.",
            "deleted_count": 0
        }
    
    # Primeiro encontrar os duplicados (com debug)
    duplicates_info = find_duplicate_records_with_debug(index_name, api_key, namespace)
    
    if not duplicates_info["success"]:
        return duplicates_info
    
    if duplicates_info["total_records_to_delete"] == 0:
        return {
            "success": True,
            "message": "✅ Nenhum duplicado encontrado para apagar!",
            "deleted_count": 0
        }
    
    # Configurar Pinecone
    pc = setup_pinecone(api_key)
    index = pc.Index(index_name)
    
    deleted_count = 0
    ids_to_delete = []
    
    try:
        print("🚨 ATENÇÃO: A ELIMINAR REGISTOS DUPLICADOS PERMANENTEMENTE!")
        print("-" * 50)
        
        # Preparar lista de IDs para apagar baseado na estratégia
        for text, info in duplicates_info["duplicates"].items():
            records = info['records']
            
            # Escolher qual manter baseado na estratégia
            if keep_strategy == "first":
                to_keep = records[0]
                to_delete = records[1:]
            elif keep_strategy == "last":
                to_keep = records[-1]
                to_delete = records[:-1]
            elif keep_strategy == "highest_score":
                to_keep = max(records, key=lambda x: x['score'])
                to_delete = [r for r in records if r['id'] != to_keep['id']]
            else:
                to_keep = records[0]  # fallback
                to_delete = records[1:]
            
            preview = text[:50].replace('\n', ' ').replace('\r', ' ')
            print(f"📝 Texto: \"{preview}...\"")
            print(f"   🔒 MANTER: {to_keep['id']} (score: {to_keep['score']:.4f})")
            
            for record in to_delete:
                ids_to_delete.append(record['id'])
                print(f"   🗑️  APAGAR: {record['id']} (score: {record['score']:.4f})")
        
        # Apagar registos em lotes
        if ids_to_delete:
            print(f"\n🔥 A apagar {len(ids_to_delete)} registos duplicados...")
            
            for i in range(0, len(ids_to_delete), batch_size):
                batch = ids_to_delete[i:i + batch_size]
                
                delete_response = index.delete(
                    ids=batch,
                    namespace=namespace
                )
                
                deleted_count += len(batch)
                print(f"✅ Apagados {len(batch)} registos (lote {i//batch_size + 1})")
        
        result = {
            "success": True,
            "deleted_count": deleted_count,
            "duplicate_groups": duplicates_info["total_duplicate_groups"],
            "keep_strategy": keep_strategy,
            "debug_file": duplicates_info.get("debug_file"),
            "message": f"✅ Operação concluída! {deleted_count} registos duplicados apagados, mantendo {duplicates_info['total_duplicate_groups']} únicos."
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "deleted_count": deleted_count,
            "message": f"❌ Erro durante a operação: {str(e)}"
        }

# Exemplo de uso
if __name__ == "__main__":
    # Configurações - substitua pelos seus valores
    PINECONE_API_KEY = "pcsk_6qf8kj_9w61ctrpQNzrNVadceiUsV5sW2cbnTv9qLw9H4n14B1sgWyDxpmZComrJCsWNLu"
    INDEX_NAME = "project"
    NAMESPACE = "ns1"  # deixe vazio se não usar namespaces
    
    # PASSO 1: ANÁLISE COMPLETA COM DEBUG
    print("🔍 PASSO 1: ANÁLISE COMPLETA DE DUPLICADOS (COM DEBUG)")
    print("=" * 70)
    
    duplicates_result = find_duplicate_records_with_debug(
        index_name=INDEX_NAME,
        api_key=PINECONE_API_KEY,
        namespace=NAMESPACE,
        max_results=10000,
        generate_debug_file=True,
        debug_filename=None  # Gera nome automático
    )
    
    if duplicates_result["success"] and duplicates_result["total_records_to_delete"] > 0:
        print(f"\n⚠️  ATENÇÃO: {duplicates_result['total_records_to_delete']} registos duplicados encontrados!")
        print(f"📊 {duplicates_result['total_duplicate_groups']} grupos de textos duplicados.")
        
        if duplicates_result["debug_file"]:
            print(f"📄 Relatório detalhado salvo em: {duplicates_result['debug_file']}")
            print(f"   👀 REVISE O ARQUIVO ANTES DE PROSSEGUIR!")
        
        # Escolher estratégia
        print("\n🎯 ESTRATÉGIAS DISPONÍVEIS:")
        print("   1. 'first' - Manter o primeiro registo de cada grupo")
        print("   2. 'last' - Manter o último registo de cada grupo") 
        print("   3. 'highest_score' - Manter o registo com maior score (RECOMENDADO)")
        
        strategy = input("\n🤔 Escolha a estratégia (first/last/highest_score) [default: highest_score]: ").strip()
        if strategy not in ["first", "last", "highest_score"]:
            strategy = "highest_score"
        
        # Pedir confirmação do utilizador
        print(f"\n❓ Quer mesmo apagar os duplicados usando estratégia '{strategy}'?")
        print(f"   📄 Revise o arquivo '{duplicates_result['debug_file']}' primeiro!")
        confirmation = input("   Escreva 'SIM' para confirmar: ")
        
        if confirmation.upper() == "SIM":
            # PASSO 2: APAGAR OS DUPLICADOS
            print("\n🗑️  PASSO 2: A APAGAR DUPLICADOS")
            print("=" * 70)
            
            delete_result = delete_duplicate_records(
                index_name=INDEX_NAME,
                api_key=PINECONE_API_KEY,
                namespace=NAMESPACE,
                confirm=True,
                keep_strategy=strategy
            )
            
            print(f"\n{delete_result['message']}")
            
            if delete_result.get('debug_file'):
                print(f"📄 Relatório de debug mantido em: {delete_result['debug_file']}")
            
        else:
            print("❌ Operação cancelada. Nenhum registo foi apagado.")
            print(f"📄 O relatório de debug continua disponível em: {duplicates_result['debug_file']}")
    
    elif duplicates_result["success"]:
        print("✅ Nenhum registo duplicado encontrado. O seu índice já está limpo!")
    
    else:
        print(f"❌ Erro ao procurar duplicados: {duplicates_result.get('error', 'Erro desconhecido')}")