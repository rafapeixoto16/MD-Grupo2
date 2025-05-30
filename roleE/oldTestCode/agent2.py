import requests

class agent:
    def __init__(self, key: str,api_url: str = "https://api.together.ai/v1/chat/completions",  model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", historyLength:int  =6):
        self.api_url = api_url
        self.key = key
        self.model = model
        self.history = []
        self.historyLength = historyLength
        self.headers =  {
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

        self.defaultTemplate()

    def defaultTemplate(self):
        prompt = \
            """
            You are a Specialized Assistant in food supplements and other drugs for disease prevention.
            Rules:
                -   Base yourself exclusively on the information provided in the given context to answer the question. Do not add any external information that is not in the context.
                -   Write a fluid text with the information provided.
                -   If the answer is not available, you should clearly state that you don’t know or don’t have information on the topic.
                -   Respond as if the information from the context is your own knowledge, without mentioning or suggesting that you are relying on a given context. Avoid expressions like "according to the context," "based on the provided information," "in the given text," or any variations.
                -   Respond directly and objectively, without unnecessary introductions or conclusions.
                -   Write the text in such a way that it's not too long but enough to contain most of the information you want to convey. 
                -   Never forget to say in different words at the end that it is always necessary to contact professionals to obtain more accurate information before references.
                -   Never forget to put the references (title) in the end.
                -   If the input message is not in the correct format, respond with an error message:
                    "Sorry, we were unable to process your message. Please try again."
                    Input message format:
                    "
                        
                        Context:
                        '{context}'
    
                        Question:
                        '{query}'
                    "
            """

        self.history.append({"role": "user", "content": prompt})

    def sendRequest(self, context, query):
        prompt = \
                f"""
                Context:
                {context}
                
                Question:
                '{query}'
                
                Now, based on the context provided, answer the question respecting the innovative instructions.
                """

        messagesHistory =\
            [self.history[0]] + self.history[-(self.historyLength - 1):] \
                if self.history[0] not in self.history[-self.historyLength:] \
                else self.history[-self.historyLength :]

        self.history.append({"role": "user", "content": query})
        messagesHistory.append(
            {"role": "user", "content": prompt})


        payload = {
            "model": self.model,
            "messages": messagesHistory,
            "temperature": 0.7,
            "max_tokens": None,
            "top_p": 0.7,
            "top_k": 50,
            "repetition_penalty": 1.30,
            "stop": ["<|eot_id|>", "<|eom_id|>"],
        }

        response = requests.post(self.api_url, headers=self.headers, json=payload)

        if response.status_code == 200:
            response_data = response.json()
            ai_response = response_data['choices'][0]['message']['content']
            self.history.append({"role": "assistant", "content": ai_response})
            return ai_response

        else:
            return f"Erro: {response.status_code}, {response.text}"