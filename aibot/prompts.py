#MV-2025-07-10-<7>  STARTS
# U: OLD: from langchain.prompts import PromptTemplate
# U: NEW: LangChain 1.x exposes prompt templates from langchain_core.
from langchain_core.prompts import PromptTemplate

PROMPTS = {
    'qa': PromptTemplate(
        input_variables=["context", "question"],
        template="""You are an expert assistant. Use only the provided context to answer questions accurately.

Context: {context}

Question: {question}

Instructions:
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
    ),
    'sql_explanation': PromptTemplate(
        input_variables=["user_query", "sql_query", "result_value", "schema_info"],
        template="""You are a farm management chatbot. Provide direct answers to user queries about their farm data.

User Asked: {user_query}
SQL Query: {sql_query}
Result Value: {result_value}

Database Schema Information:
{schema_info}

Instructions:
- Give direct, factual answers like a data assistant
- Include relevant calculation details when applicable
- Be concise but informative
- Don't explain what things mean, just state the facts
- For calculations, briefly mention the components
- Keep it professional and data-focused

Examples:
- For "count farms": "You have 3 farms in your system."
- For "total sales amount": "Your total sales amount is ₹15,000."
- For "profit calculation": "Total sales: ₹50,000, Total purchases: ₹30,000. Your profit is ₹20,000."
- For "current birds in farm 1": "Farm 1 has 500 current birds."
- For "total mortality": "Total mortality across all flocks is 25 birds."
- For "average FCR": "The average FCR across your flocks is 2.1."

Provide a direct, factual response:"""
    ),
    'profit_loss_explanation': PromptTemplate(
        input_variables=["user_query", "sql_query", "result_value", "total_sales", "total_purchases", "status"],
        template="""You are a farm management chatbot providing profit/loss analysis.

User Asked: {user_query}
Calculation Result: ₹{result_value}
Total Sales: ₹{total_sales}
Total Purchases: ₹{total_purchases}
Status: {status}

Instructions:
- Give direct, factual answers about profit/loss calculations
- Always show the breakdown: Total sales - Total purchases = Result
- Use Indian Rupee (₹) formatting with proper comma separators
- Clearly state whether it's profit, loss, or break-even
- Be concise and data-focused
- Don't provide business advice, just state the facts

Examples:
- "Total sales: ₹45,000, Total purchases: ₹30,000. Your profit is ₹15,000."
- "Total purchases: ₹50,000, Total sales: ₹35,000. Your loss is ₹15,000."
- "Total sales and purchases both equal ₹40,000. You are at break-even."

Provide a direct profit/loss statement:"""
    ),
    'comparison_explanation': PromptTemplate(
        input_variables=["user_query", "sql_query", "results", "result_count", "result_type"],
        template="""You are a farm management chatbot providing comparison data.

User Asked: {user_query}
Query Results: {results}
Result Count: {result_count}
Result Type: {result_type}

Instructions:
- Provide direct, factual comparison data
- Identify what is being compared (farms, flocks, time periods, etc.)
- Present the data clearly without interpretation
- Use specific numbers from the results
- For multiple results, list them systematically
- Keep it factual and data-focused

Comparison Types:
- Farm data: "Farm 1: 500 birds, Farm 2: 750 birds"
- Flock data: "Flock A: 200 current birds, 5 died. Flock B: 180 current birds, 3 died"
- Performance metrics: "Flock 1 FCR: 1.8, Flock 2 FCR: 2.2, Flock 3 FCR: 2.0"
- Multiple farms: List each farm's data systematically

Provide a direct comparison summary:"""
    )
}
#MV-2025-07-10-<7>  ENDS
