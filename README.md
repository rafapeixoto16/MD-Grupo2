# Topico 2 - Suplementos alimentares e outros fármacos para prevenção de doenças (2024/2025)
Trabalho realizado pelo grupo referente ao tópico 2

# Elementos
- pg55966 : Jorge Nuno Gomes Rodrigues
- pg55963 : João Pedro Silva Carvalho Pastore
- pg56013 : Tiago Granja Rodrigues
- pg57867 : António Filipe Castro Silva
- pg55998 : Rafael Conde Peixoto
- pg55932 : Diogo Cardoso Ferreira

# Estrutura do Repositório
### `Data-roleC/` — Base de conhecimento

Contém os dados e scripts responsáveis pela construção da base de conhecimento

**Subpastas:**
- `src/modules/`: Scripts que integram APIs de fontes académicas (PubMed, EuropePMC, etc.) e ferramentas como SpaCy e Pinecone.
- `src/trusted_data/`: Scripts e ficheiros JSON com fontes de informação consideradas confiáveis.
- `src/terms/`: Conjunto de termos relacionados com suplementos, fármacos ...

**Scripts principais:**
- `python src/main.py` — Preenche a base de dados com *abstracts* de artigos científicos (nível 2). É possível escolher as fontes a utilizar.
- `python src/trust_data.py` — Preenche a base de dados com informação confiável (nível 1), a partir dos ficheiros JSON disponíveis em `src/trusted_data/`.

---

### `roleE/` — Agente e Validação

Contém o código descontinuado do agente especifico mais os ficheiros de perguntas/respostas utilizados para as duas fases de validação realizadas.

O agente é composto por um módulo de RAG, que utiliza a API do Pinecone para recuperação de contexto, e um componente de geração de texto, acionado via API do Together.ai.

A validação consistiu em questionar três modelos de linguagem distintos — ChatGPT, Claude (Sonnet-4) e Gemini — para avaliarem as perguntas. Como complemento, foi ainda solicitado a estes modelos que comparassem as respostas geradas. Na segunda fase da validação, foi realizada uma validação manual adicional como reforço ao processo automático.

