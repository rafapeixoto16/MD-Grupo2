import os
from dotenv import load_dotenv

import rag2
import agent2

load_dotenv()

query = "caffeine benefits"
#query2 = "creatine is good if I do nothing"
rag = rag2.rag2("papers",os.getenv("API_KEY_PINECONE"),3)
results = rag.query_pinecone(query)
print(results)
print()
agent = agent2.agent(os.getenv("API_KEY_TOGETHER"))
resposta = agent.sendRequest(query,results)
resposta = "\n".join(linha for linha in resposta.splitlines() if linha.strip())
print(resposta)


#argila
