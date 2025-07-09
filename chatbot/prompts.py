from langchain.prompts import PromptTemplate

PROMPTS = {
    'qa': PromptTemplate(
        input_variables=["context", "question"],
        template="""You are an expert assistant. Use only the provided context to answer questions accurately.

Context: {context}

Question: {question}

Instructions:
- If the question is NOT about poultry, hatcheries, poultry diseases, or broilers, respond with: "I don't know."
- Answer naturally as if you know the information directly
- Never mention "the context", "according to", "based on", or similar phrases
- Be specific and detailed
- If information is not available, say "I don't have enough information to answer this"
- Focus on practical, actionable advice

Answer:"""
    ),
    'follow_up': PromptTemplate(
        input_variables=["context", "question"],
        template="""Based on the context provided, suggest relevant follow-up questions for: {question}

Context: {context}

Instructions:
- If the question is NOT about poultry, hatcheries, poultry diseases, or broilers, respond with: "I don't know."
- Generate 3-5 practical follow-up questions
- Focus on implementation, costs, or next steps
- Make questions specific and actionable

Follow-up Questions:"""
    ),
    'summary': PromptTemplate(
        input_variables=["context", "question"],
        template="""Provide a brief summary for: {question}

Context: {context}

Instructions:
- If the question is NOT about poultry, hatcheries, poultry diseases, or broilers, respond with: "I don't know."
- Create a concise summary in 2-3 sentences
- Include only the most important points
- Use simple, clear language

Summary:"""
    ),
    'clarification': PromptTemplate(
        input_variables=["context", "question"],
        template="""Clarify and explain the following question in simple terms: {question}

Context: {context}

Instructions:
- If the question is NOT about poultry, hatcheries, poultry diseases, or broilers, respond with: "I don't know."
- Break down complex terms into simple explanations
- Provide step-by-step explanations if needed
- Use examples when helpful
- If the question is unclear, ask for more details

Clarification:"""
    )
}