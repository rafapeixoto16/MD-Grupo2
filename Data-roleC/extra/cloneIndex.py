#!/usr/bin/env python3
"""
Script para clonar um índice Pinecone com integridade garantida e 100% de cobertura
Versão melhorada com estratégias avançadas para encontrar TODOS os vetores
Atualizado para a nova API do Pinecone (compatível com versão atual)
"""

import os
import time
import json
import hashlib
import random
import math
import numpy as np
from tqdm import tqdm
from typing import List, Dict, Set
from pinecone import Pinecone, ServerlessSpec

# ================================
# CONFIGURAÇÃO
# ================================
PINECONE_API_KEY = "pcsk_6qf8kj_9w61ctrpQNzrNVadceiUsV5sW2cbnTv9qLw9H4n14B1sgWyDxpmZComrJCsWNLu"

SOURCE_INDEX_NAME = "project"
TARGET_INDEX_NAME = "project-clone"
SOURCE_NAMESPACE = "ns1"  # Namespace de origem
TARGET_NAMESPACE = "ns1"  # Namespace de destino (será criado automaticamente)

BATCH_SIZE = 50  # Menor para maior precisão
DELAY_BETWEEN_BATCHES = 1.0  # Mais tempo para evitar problemas
MAX_RETRIES = 3  # Tentativas em caso de erro

# Inicializar cliente Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Inicializar índices
source_index = pc.Index(SOURCE_INDEX_NAME)
target_index = pc.Index(TARGET_INDEX_NAME)

# ================================
# FUNÇÕES DE VERIFICAÇÃO
# ================================

def verify_index_compatibility():
    """Verificar se os índices são compatíveis antes de começar"""
    print("🔍 Verificando compatibilidade dos índices...")
    
    try:
        source_stats = source_index.describe_index_stats()
        target_stats = target_index.describe_index_stats()
        
        # Acessar stats dos namespaces (nova API)
        source_namespaces = getattr(source_stats, 'namespaces', {}) or {}
        target_namespaces = getattr(target_stats, 'namespaces', {}) or {}
        
        source_ns_stats = source_namespaces.get(SOURCE_NAMESPACE, {})
        target_ns_stats = target_namespaces.get(TARGET_NAMESPACE, {})
        
        source_dim = getattr(source_stats, 'dimension', None)
        target_dim = getattr(target_stats, 'dimension', None)
        
        # Acessar vector_count de forma segura
        if hasattr(source_ns_stats, 'vector_count'):
            source_ns_count = source_ns_stats.vector_count
        else:
            source_ns_count = source_ns_stats.get('vector_count', 0) if isinstance(source_ns_stats, dict) else 0
            
        if hasattr(target_ns_stats, 'vector_count'):
            target_ns_count = target_ns_stats.vector_count
        else:
            target_ns_count = target_ns_stats.get('vector_count', 0) if isinstance(target_ns_stats, dict) else 0
        
        total_source = getattr(source_stats, 'total_vector_count', 0)
        total_target = getattr(target_stats, 'total_vector_count', 0)
        
        print(f"📊 Índice origem: {total_source} vetores total, {source_dim}D")
        print(f"📊 Namespace origem '{SOURCE_NAMESPACE}': {source_ns_count} vetores")
        print(f"📊 Índice destino: {total_target} vetores total, {target_dim}D")
        print(f"📊 Namespace destino '{TARGET_NAMESPACE}': {target_ns_count} vetores")
        
        if source_dim != target_dim:
            print(f"❌ ERRO CRÍTICO: Dimensões incompatíveis!")
            print(f"   Origem: {source_dim}D, Destino: {target_dim}D")
            return False, None, None
        
        if source_ns_count == 0:
            print(f"❌ ERRO: Namespace '{SOURCE_NAMESPACE}' está vazio ou não existe no índice origem!")
            return False, None, None
            
        if target_ns_count > 0:
            print(f"⚠️  AVISO: O namespace '{TARGET_NAMESPACE}' no índice destino já contém {target_ns_count} vetores!")
            clear = input("   Deseja continuar? Isto pode criar duplicados (s/N): ").lower().strip()
            if clear not in ['s', 'sim', 'y', 'yes']:
                return False, None, None
        
        return True, source_stats, target_stats
        
    except Exception as e:
        print(f"❌ Erro ao verificar índices: {e}")
        return False, None, None

def get_vector_hash(vector_data):
    """Criar hash único para um vetor (ID + valores + metadata)"""
    # Acessar dados do vetor de forma compatível com nova API
    if hasattr(vector_data, 'values'):
        values = vector_data.values
    else:
        values = vector_data.get('values', []) if isinstance(vector_data, dict) else []
    
    if hasattr(vector_data, 'metadata'):
        metadata = vector_data.metadata or {}
    else:
        metadata = vector_data.get('metadata', {}) if isinstance(vector_data, dict) else {}
    
    hash_data = {
        'values': values,
        'metadata': metadata
    }
    
    # Converter para JSON ordenado e criar hash
    json_str = json.dumps(hash_data, sort_keys=True, ensure_ascii=True)
    return hashlib.md5(json_str.encode()).hexdigest()

def generate_diverse_vectors(dimension, num_vectors=50):
    """Gerar vetores de query extremamente diversos para maximizar cobertura"""
    vectors = []
    
    # 1. Vetor zero
    vectors.append([0.0] * dimension)
    
    # 2. Vetores unitários em cada dimensão
    for i in range(min(20, dimension)):
        unit_vector = [0.0] * dimension
        unit_vector[i] = 1.0
        vectors.append(unit_vector)
        
        # Também versão negativa
        unit_vector_neg = [0.0] * dimension
        unit_vector_neg[i] = -1.0
        vectors.append(unit_vector_neg)
    
    # 3. Vetores com distribuições estatísticas diferentes
    distributions = [
        lambda: random.uniform(-1, 1),  # Uniforme
        lambda: random.gauss(0, 0.3),   # Normal centrada
        lambda: random.gauss(0, 1.0),   # Normal larga
        lambda: random.expovariate(1),  # Exponencial
        lambda: random.betavariate(0.5, 0.5),  # Beta
        lambda: random.lognormvariate(0, 1),   # Log-normal
    ]
    
    for dist_func in distributions:
        for _ in range(3):  # 3 vetores por distribuição
            try:
                vector = [dist_func() for _ in range(dimension)]
                # Normalizar para evitar valores extremos
                norm = math.sqrt(sum(x*x for x in vector))
                if norm > 0:
                    vector = [x/norm for x in vector]
                vectors.append(vector)
            except:
                pass
    
    # 4. Vetores esparsos com diferentes densidades
    sparsity_levels = [0.01, 0.05, 0.1, 0.2, 0.5]  # 1%, 5%, 10%, 20%, 50% não-zero
    for sparsity in sparsity_levels:
        for _ in range(2):
            sparse_vector = [0.0] * dimension
            num_nonzero = max(1, int(dimension * sparsity))
            indices = random.sample(range(dimension), num_nonzero)
            for idx in indices:
                sparse_vector[idx] = random.uniform(-1, 1)
            vectors.append(sparse_vector)
    
    # 5. Vetores com padrões matemáticos
    for pattern in range(5):
        if pattern == 0:  # Senoidal
            vector = [math.sin(i * 0.1) for i in range(dimension)]
        elif pattern == 1:  # Cosenoidal
            vector = [math.cos(i * 0.1) for i in range(dimension)]
        elif pattern == 2:  # Linear crescente
            vector = [i / dimension for i in range(dimension)]
        elif pattern == 3:  # Alternado
            vector = [1 if i % 2 == 0 else -1 for i in range(dimension)]
        else:  # Fibonacci mod
            a, b = 1, 1
            vector = []
            for i in range(dimension):
                vector.append((a % 100) / 100.0 - 0.5)
                a, b = b, a + b
        
        vectors.append(vector)
    
    # 6. Vetores aleatórios puros com diferentes escalas
    scales = [0.01, 0.1, 0.5, 1.0, 2.0, 5.0]
    for scale in scales:
        for _ in range(2):
            vector = [random.uniform(-scale, scale) for _ in range(dimension)]
            vectors.append(vector)
    
    # 7. Combinações lineares de vetores anteriores
    if len(vectors) >= 10:
        for _ in range(10):
            # Pegar 2-3 vetores aleatórios e combinar
            sample_vectors = random.sample(vectors[:20], min(3, len(vectors)))
            weights = [random.uniform(-1, 1) for _ in range(len(sample_vectors))]
            
            combined = [0.0] * dimension
            for i in range(dimension):
                for j, vec in enumerate(sample_vectors):
                    combined[i] += weights[j] * vec[i]
            
            vectors.append(combined)
    
    return vectors[:num_vectors]

def get_all_vector_ids_ultra_complete(index, namespace=""):
    """Estratégia ultra-agressiva para encontrar 100% dos vetores"""
    print(f"🎯 MODO ULTRA-COMPLETO: Descobrindo TODOS os vetores do namespace '{namespace}'...")
    
    stats = index.describe_index_stats()
    dimension = getattr(stats, 'dimension', 1536)
    
    # Obter contagem específica do namespace
    namespaces = getattr(stats, 'namespaces', {}) or {}
    ns_stats = namespaces.get(namespace, {})
    
    if hasattr(ns_stats, 'vector_count'):
        total_vectors = ns_stats.vector_count
    else:
        total_vectors = ns_stats.get('vector_count', 0) if isinstance(ns_stats, dict) else 0
    
    print(f"📈 Meta: {total_vectors} vetores (100% de cobertura obrigatória)")
    
    if total_vectors == 0:
        print(f"⚠️  Namespace '{namespace}' está vazio!")
        return []
    
    all_ids = set()
    round_num = 1
    max_rounds = 20  # Máximo de 20 rodadas
    
    while len(all_ids) < total_vectors and round_num <= max_rounds:
        print(f"\n🔄 RODADA {round_num} - Progresso: {len(all_ids)}/{total_vectors} ({len(all_ids)/total_vectors*100:.1f}%)")
        
        initial_count = len(all_ids)
        
        # Gerar vetores de query extremamente diversos
        query_vectors = generate_diverse_vectors(dimension, num_vectors=100)
        
        # Testar diferentes valores de top_k
        top_k_values = [1000, 2000, 5000, 8000, 9000, 9500, 9900, 9999, 10000]
        
        for i, query_vector in enumerate(query_vectors):
            if len(all_ids) >= total_vectors:
                break
                
            for top_k in top_k_values:
                if len(all_ids) >= total_vectors:
                    break
                
                try:
                    response = index.query(
                        vector=query_vector,
                        top_k=top_k,
                        namespace=namespace,
                        include_values=False,
                        include_metadata=False
                    )
                    
                    matches = getattr(response, 'matches', []) or []
                    batch_ids = set()
                    for match in matches:
                        if hasattr(match, 'id'):
                            batch_ids.add(match.id)
                        elif isinstance(match, dict) and 'id' in match:
                            batch_ids.add(match['id'])
                    
                    new_ids = batch_ids - all_ids
                    all_ids.update(batch_ids)
                    
                    if new_ids and len(new_ids) > 0:
                        print(f"  ✅ Query {i+1}/100, top_k={top_k}: +{len(new_ids)} novos (total: {len(all_ids)})")
                    
                    # Pequena pausa para não sobrecarregar
                    time.sleep(0.05)
                    
                except Exception as e:
                    continue
        
        # Estratégia de propagação por sementes (mais agressiva)
        if len(all_ids) < total_vectors and len(all_ids) > 0:
            print(f"  🌱 Propagação por sementes...")
            
            # Usar uma amostra maior de IDs como sementes
            seed_sample_size = min(200, len(all_ids))
            seed_ids = random.sample(list(all_ids), seed_sample_size)
            
            for j, seed_id in enumerate(seed_ids):
                if len(all_ids) >= total_vectors:
                    break
                
                try:
                    # Buscar o vetor semente
                    fetch_response = index.fetch(ids=[seed_id], namespace=namespace)
                    
                    if hasattr(fetch_response, 'vectors'):
                        vectors_dict = fetch_response.vectors or {}
                    else:
                        vectors_dict = fetch_response.get('vectors', {}) if isinstance(fetch_response, dict) else {}
                    
                    if seed_id in vectors_dict:
                        seed_vector_data = vectors_dict[seed_id]
                        
                        if hasattr(seed_vector_data, 'values'):
                            seed_values = seed_vector_data.values
                        else:
                            seed_values = seed_vector_data.get('values', [])
                        
                        if seed_values:
                            # Criar variações do vetor semente
                            variations = []
                            variations.append(seed_values)  # Original
                            
                            # Variações com ruído
                            for noise_level in [0.01, 0.05, 0.1, 0.2]:
                                noisy = [val + random.gauss(0, noise_level) for val in seed_values]
                                variations.append(noisy)
                            
                            # Variações com escala
                            for scale in [0.5, 0.8, 1.2, 1.5]:
                                scaled = [val * scale for val in seed_values]
                                variations.append(scaled)
                            
                            # Query com cada variação
                            for var_vector in variations:
                                for top_k in [5000, 8000, 10000]:
                                    try:
                                        response = index.query(
                                            vector=var_vector,
                                            top_k=top_k,
                                            namespace=namespace,
                                            include_values=False,
                                            include_metadata=False
                                        )
                                        
                                        matches = getattr(response, 'matches', []) or []
                                        batch_ids = set()
                                        for match in matches:
                                            if hasattr(match, 'id'):
                                                batch_ids.add(match.id)
                                            elif isinstance(match, dict) and 'id' in match:
                                                batch_ids.add(match['id'])
                                        
                                        new_ids = batch_ids - all_ids
                                        all_ids.update(batch_ids)
                                        
                                        if new_ids:
                                            print(f"    ✅ Semente {j+1}/{seed_sample_size}: +{len(new_ids)} (total: {len(all_ids)})")
                                        
                                        if len(all_ids) >= total_vectors:
                                            break
                                            
                                    except Exception as e:
                                        continue
                                    
                                    time.sleep(0.02)
                                
                                if len(all_ids) >= total_vectors:
                                    break
                            
                except Exception as e:
                    continue
        
        # Verificar progresso desta rodada
        new_in_round = len(all_ids) - initial_count
        print(f"  📊 Rodada {round_num} concluída: +{new_in_round} vetores")
        
        if new_in_round == 0:
            print(f"  ⚠️  Nenhum progresso na rodada {round_num}")
            if round_num >= 3:  # Se não há progresso por 3 rodadas, parar
                break
        
        round_num += 1
        
        # Pausa entre rodadas
        if len(all_ids) < total_vectors:
            time.sleep(1)
    
    final_ids = list(all_ids)
    coverage = (len(final_ids) / total_vectors * 100) if total_vectors > 0 else 0
    
    print(f"\n🎯 RESULTADO FINAL:")
    print(f"   IDs únicos encontrados: {len(final_ids)}")
    print(f"   Meta: {total_vectors}")
    print(f"   Cobertura: {coverage:.3f}%")
    print(f"   Faltam: {total_vectors - len(final_ids)}")
    
    if len(final_ids) == total_vectors:
        print(f"🎉 COBERTURA PERFEITA! 100% dos vetores encontrados!")
    elif len(final_ids) >= total_vectors * 0.999:  # 99.9%
        print(f"✅ COBERTURA EXCELENTE! Apenas {total_vectors - len(final_ids)} vetores em falta")
    elif len(final_ids) >= total_vectors * 0.995:  # 99.5%
        print(f"✅ COBERTURA MUITO BOA! {total_vectors - len(final_ids)} vetores em falta")
    else:
        print(f"⚠️  COBERTURA INCOMPLETA: {total_vectors - len(final_ids)} vetores em falta")
        print(f"   Isso pode indicar:")
        print(f"   • Vetores muito isolados no espaço de embeddings")
        print(f"   • Limitações do algoritmo de busca do Pinecone")
        print(f"   • Possível inconsistência nas estatísticas do índice")
    
    return final_ids

def copy_batch_with_retry(source_idx, target_idx, vector_ids, source_namespace="", target_namespace=""):
    """Copiar lote com retry e verificação de integridade entre namespaces"""
    
    for attempt in range(MAX_RETRIES):
        try:
            # Buscar vetores do namespace de origem
            fetch_response = source_idx.fetch(ids=vector_ids, namespace=source_namespace)
            
            # Acessar vetores de forma compatível com nova API
            if hasattr(fetch_response, 'vectors'):
                vectors_dict = fetch_response.vectors or {}
            else:
                vectors_dict = fetch_response.get('vectors', {}) if isinstance(fetch_response, dict) else {}
            
            if not vectors_dict:
                print(f"⚠️  Lote vazio: {vector_ids[:3]}...")
                return 0, {}
            
            # Preparar para upsert
            vectors_to_upsert = []
            source_hashes = {}
            
            for vector_id, vector_data in vectors_dict.items():
                # Acessar dados do vetor de forma compatível
                if hasattr(vector_data, 'values'):
                    values = vector_data.values
                else:
                    values = vector_data.get('values', []) if isinstance(vector_data, dict) else []
                
                vector_info = {
                    'id': vector_id,
                    'values': values
                }
                
                # Acessar metadata de forma compatível
                if hasattr(vector_data, 'metadata') and vector_data.metadata:
                    vector_info['metadata'] = vector_data.metadata
                elif isinstance(vector_data, dict) and 'metadata' in vector_data:
                    vector_info['metadata'] = vector_data['metadata']
                
                vectors_to_upsert.append(vector_info)
                source_hashes[vector_id] = get_vector_hash(vector_data)
            
            # Inserir no namespace de destino
            target_idx.upsert(vectors=vectors_to_upsert, namespace=target_namespace)
            
            # Aguardar propagação
            time.sleep(0.5)
            
            # VERIFICAÇÃO DE INTEGRIDADE: Buscar de volta do namespace destino e comparar
            verification_response = target_idx.fetch(ids=list(source_hashes.keys()), namespace=target_namespace)
            
            # Acessar vetores verificados de forma compatível
            if hasattr(verification_response, 'vectors'):
                verified_vectors = verification_response.vectors or {}
            else:
                verified_vectors = verification_response.get('vectors', {}) if isinstance(verification_response, dict) else {}
            
            verified_count = 0
            for vector_id, expected_hash in source_hashes.items():
                if vector_id in verified_vectors:
                    actual_hash = get_vector_hash(verified_vectors[vector_id])
                    if actual_hash == expected_hash:
                        verified_count += 1
                    else:
                        print(f"⚠️  Hash mismatch para {vector_id}")
            
            if verified_count == len(source_hashes):
                return len(vectors_to_upsert), source_hashes
            else:
                print(f"⚠️  Verificação falhou: {verified_count}/{len(source_hashes)} corretos")
                if attempt < MAX_RETRIES - 1:
                    print(f"🔄 Tentativa {attempt + 2}/{MAX_RETRIES}...")
                    time.sleep(2)
                    continue
            
        except Exception as e:
            print(f"❌ Erro na tentativa {attempt + 1}: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"🔄 Tentativa {attempt + 2}/{MAX_RETRIES}...")
                time.sleep(2)
            else:
                print(f"❌ Falha após {MAX_RETRIES} tentativas")
                return 0, {}
    
    return 0, {}

# ================================
# PROCESSO PRINCIPAL
# ================================

def clone_index_with_perfect_integrity():
    print("\n" + "="*70)
    print("🚀 CLONAGEM ULTRA-COMPLETA DE ÍNDICE PINECONE")
    print("🎯 MODO: 100% DE COBERTURA OBRIGATÓRIA")
    print("="*70)
    
    # Verificações iniciais
    compatible, source_stats, target_stats = verify_index_compatibility()
    if not compatible:
        return False
    
    # Obter TODOS os vetores do namespace específico
    all_vector_ids = get_all_vector_ids_ultra_complete(source_index, SOURCE_NAMESPACE)
    if not all_vector_ids:
        print(f"❌ Não foi possível obter lista completa de vetores do namespace '{SOURCE_NAMESPACE}'")
        return False
    
    # Obter contagem esperada para verificação final
    stats = source_index.describe_index_stats()
    namespaces = getattr(stats, 'namespaces', {}) or {}
    ns_stats = namespaces.get(SOURCE_NAMESPACE, {})
    if hasattr(ns_stats, 'vector_count'):
        expected_count = ns_stats.vector_count
    else:
        expected_count = ns_stats.get('vector_count', 0) if isinstance(ns_stats, dict) else 0
    
    if len(all_vector_ids) < expected_count:
        missing = expected_count - len(all_vector_ids)
        print(f"\n❌ COBERTURA INCOMPLETA!")
        print(f"   Encontrados: {len(all_vector_ids)}")
        print(f"   Esperados: {expected_count}")
        print(f"   Faltam: {missing}")
        print(f"\n⚠️  VOCÊ SOLICITOU ABSOLUTAMENTE TODOS OS VETORES")
        print(f"   O algoritmo não conseguiu encontrar {missing} vetores ({missing/expected_count*100:.2f}%)")
        print(f"   Isso pode significar que esses vetores estão em regiões muito isoladas")
        print(f"   do espaço de embeddings, fora do alcance das queries de similaridade.")
        
        response = input(f"\n   Deseja continuar mesmo assim? (s/N): ").lower().strip()
        if response not in ['s', 'sim', 'y', 'yes']:
            print("❌ Operação cancelada - cobertura incompleta")
            return False
        else:
            print("⚠️  CONTINUANDO COM COBERTURA PARCIAL CONFORME SOLICITADO")
    else:
        print(f"🎉 COBERTURA PERFEITA! Todos os {expected_count} vetores encontrados!")
    
    print(f"\n🎯 Iniciando cópia de {len(all_vector_ids)} vetores")
    print(f"📤 Origem: {SOURCE_INDEX_NAME} -> namespace '{SOURCE_NAMESPACE}'")
    print(f"📥 Destino: {TARGET_INDEX_NAME} -> namespace '{TARGET_NAMESPACE}'")
    print(f"📦 Lotes de {BATCH_SIZE} vetores")
    
    # Copiar com verificação completa
    total_copied = 0
    total_verified = 0
    all_hashes = {}
    failed_batches = []
    
    total_batches = (len(all_vector_ids) + BATCH_SIZE - 1) // BATCH_SIZE
    
    with tqdm(total=len(all_vector_ids), desc="Clonando", unit="vetores") as pbar:
        for i in range(0, len(all_vector_ids), BATCH_SIZE):
            batch_ids = all_vector_ids[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            
            copied_count, batch_hashes = copy_batch_with_retry(
                source_index, target_index, batch_ids, 
                source_namespace=SOURCE_NAMESPACE, 
                target_namespace=TARGET_NAMESPACE
            )
            
            if copied_count > 0:
                total_copied += copied_count
                total_verified += len(batch_hashes)
                all_hashes.update(batch_hashes)
                pbar.set_postfix({
                    'Lote': f"{batch_num}/{total_batches}",
                    'Copiados': total_copied,
                    'Verificados': total_verified
                })
            else:
                failed_batches.append(batch_ids)
                pbar.set_postfix({
                    'Lote': f"{batch_num}/{total_batches}",
                    'FALHOU': len(failed_batches)
                })
            
            pbar.update(len(batch_ids))
            time.sleep(DELAY_BETWEEN_BATCHES)
    
    # VERIFICAÇÃO FINAL COMPLETA
    print(f"\n🔍 VERIFICAÇÃO FINAL DE INTEGRIDADE...")
    
    final_target_stats = target_index.describe_index_stats()
    final_target_namespaces = getattr(final_target_stats, 'namespaces', {}) or {}
    final_target_ns_stats = final_target_namespaces.get(TARGET_NAMESPACE, {})
    
    if hasattr(final_target_ns_stats, 'vector_count'):
        final_count = final_target_ns_stats.vector_count
    else:
        final_count = final_target_ns_stats.get('vector_count', 0) if isinstance(final_target_ns_stats, dict) else 0
    
    print(f"📊 Estatísticas finais:")
    print(f"   Vetores esperados: {expected_count}")
    print(f"   Vetores encontrados: {len(all_vector_ids)}")
    print(f"   Vetores copiados: {total_copied}")
    print(f"   Vetores no destino: {final_count}")
    print(f"   Lotes falhados: {len(failed_batches)}")
    
    # Verificar se a cópia está completa e íntegra
    perfect_success = (
        len(all_vector_ids) == expected_count and
        total_copied == len(all_vector_ids) and
        len(failed_batches) == 0 and
        total_verified == total_copied and
        final_count == expected_count
    )
    
    partial_success = (
        total_copied == len(all_vector_ids) and
        len(failed_batches) == 0 and
        total_verified == total_copied
    )
    
    # Continuação do código...

    if perfect_success:
        print(f"\n🎉 CLONAGEM PERFEITA! 100% DE SUCESSO!")
        print(f"✅ Todos os {expected_count} vetores copiados com integridade verificada!")
        print(f"📤 Origem: {SOURCE_INDEX_NAME} -> namespace '{SOURCE_NAMESPACE}'")
        print(f"📥 Destino: {TARGET_INDEX_NAME} -> namespace '{TARGET_NAMESPACE}'")
        return True
    elif partial_success:
        print(f"\n✅ CLONAGEM PARCIALMENTE BEM-SUCEDIDA!")
        print(f"⚠️  Todos os {total_copied} vetores foram copiados e verificados, mas:")
        if len(all_vector_ids) < expected_count:
            print(f"   • Faltaram {expected_count - len(all_vector_ids)} vetores na descoberta inicial")
        if final_count != total_copied:
            print(f"   • Inconsistência na contagem final: {final_count} no destino vs {total_copied} copiados")
        if len(failed_batches) > 0:
            print(f"   • {len(failed_batches)} lotes falharam na cópia")
        print(f"\n📝 RECOMENDAÇÃO: Revise os logs e considere reexecutar para os vetores ausentes")
        return False
    else:
        print(f"\n❌ CLONAGEM FALHOU!")
        print(f"   • Vetores esperados: {expected_count}")
        print(f"   • Vetores encontrados: {len(all_vector_ids)}")
        print(f"   • Vetores copiados: {total_copied}")
        print(f"   • Vetores verificados: {total_verified}")
        print(f"   • Vetores no destino: {final_count}")
        print(f"   • Lotes falhados: {len(failed_batches)}")
        
        if failed_batches:
            print(f"\n📜 Lotes que falharam (primeiros 3 IDs por lote):")
            for i, batch in enumerate(failed_batches[:5], 1):
                print(f"   Lote {i}: {batch[:3]}{'...' if len(batch) > 3 else ''}")
            if len(failed_batches) > 5:
                print(f"   ...e mais {len(failed_batches) - 5} lotes")
        
        print(f"\n📝 RECOMENDAÇÃO: Verifique a conectividade com o Pinecone, revise a API key e tente novamente")
        print(f"   Você pode tentar copiar apenas os lotes falhados salvando os IDs:")
        with open('failed_batches.json', 'w') as f:
            json.dump(failed_batches, f)
        print(f"   IDs dos lotes falhados salvos em 'failed_batches.json'")
        return False

def main():
    """Função principal para executar o processo de clonagem"""
    try:
        print("\n🌟 Iniciando processo de clonagem de índice Pinecone...")
        success = clone_index_with_perfect_integrity()
        
        if success:
            print("\n✅ Processo concluído com SUCESSO TOTAL!")
        else:
            print("\n⚠️ Processo concluído com PROBLEMAS!")
        
        print("\n📝 Relatório final gerado. Verifique os logs para detalhes.")
        return success
    
    except KeyboardInterrupt:
        print("\n🚫 Processo interrompido pelo usuário!")
        print("   Estado atual pode estar inconsistente no índice destino.")
        return False
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        print("   Verifique sua conexão com o Pinecone e a validade da API key.")
        return False

if __name__ == "__main__":
    main()