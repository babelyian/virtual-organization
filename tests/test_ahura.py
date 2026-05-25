from openai import OpenAI
from typing import List


def ask_llm(
        query:str,
        context:List[str]
):

    user_prompt = f"""
    context: {context}
    query: {query}
    """
    messages = [
        {
            "role" : "system",
            "content" : """You are a helpful virtual assistant.  
- Your job: answer the user’s question **only** using the facts that are present in the supplied context.  
- Do **not** hallucinate or bring in outside knowledge.  
- If the answer cannot be found, reply: “اطلاعات کافی نیست.”  
- Keep the reply concise (≤ 200 characters) and in Persian."""
        },
            {
                "role" : "user",
                "content" : user_prompt
            }
        ]
    # log.info(f"⏳ [ask_llm] Prompt: {user_prompt}")

    client = OpenAI(base_url='https://chat.aiahura.com/api', api_key='sk-d2b4e732fe994f8b914665b572612a40')
    completion = client.chat.completions.create(
        model = 'gpt-oss:20b',
        messages = messages,
        stream = False
    )
    response = completion.choices[0].message.content
    return response

print(ask_llm('hello','answer the following user query'))