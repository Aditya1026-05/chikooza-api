import logging
import os
import re
from django.conf import settings
from django.db import connection
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)

class SQLAgentService:
    def __init__(self, user=None, view_name="ai_farm_data_view"):
        self.user = user
        self.view_name = view_name
        self.schema_info = self._get_schema_info()
        self.keyword_mappings = self._get_keyword_mappings()
        self._setup_ollama_chain()

    def _get_keyword_mappings(self):
        """Define clear keyword to column mappings"""
        return {
            # Count operations
            "sales": {"column": "sale_id", "operation": "COUNT(DISTINCT sale_id)", "filter": "sale_id IS NOT NULL"},
            "purchases": {"column": "purchase_date", "operation": "COUNT(DISTINCT purchase_date)", "filter": "purchase_amount IS NOT NULL"},
            "farms": {"column": "farm_id", "operation": "COUNT(DISTINCT farm_id)", "filter": None},
            "flocks": {"column": "flock_id", "operation": "COUNT(DISTINCT flock_id)", "filter": None},

            # Sum operations
            "total sales": {"column": "sale_amount", "operation": "COALESCE(SUM(sale_amount), 0)", "filter": None},
            "sales amount": {"column": "sale_amount", "operation": "COALESCE(SUM(sale_amount), 0)", "filter": None},
            "total purchases": {"column": "purchase_amount", "operation": "COALESCE(SUM(purchase_amount), 0)", "filter": None},
            "purchase amount": {"column": "purchase_amount", "operation": "COALESCE(SUM(purchase_amount), 0)", "filter": None},

            # Bird-related
            "birds": {"column": "birds_current", "operation": "COALESCE(SUM(birds_current), 0)", "filter": "birds_current IS NOT NULL"},
            "current birds": {"column": "birds_current", "operation": "COALESCE(SUM(birds_current), 0)", "filter": "birds_current IS NOT NULL"},
            "mortality": {"column": "birds_died", "operation": "COALESCE(SUM(birds_died), 0)", "filter": "birds_died IS NOT NULL"},
            "deaths": {"column": "birds_died", "operation": "COALESCE(SUM(birds_died), 0)", "filter": "birds_died IS NOT NULL"},
            "total mortality": {"column": "total_mort", "operation": "COALESCE(SUM(total_mort), 0)", "filter": "total_mort IS NOT NULL"},

            # Feed-related
            "feed": {"column": "feed_consumed_kg", "operation": "COALESCE(SUM(feed_consumed_kg), 0)", "filter": "feed_consumed_kg IS NOT NULL"},
            "feed consumed": {"column": "feed_consumed_kg", "operation": "COALESCE(SUM(feed_consumed_kg), 0)", "filter": "feed_consumed_kg IS NOT NULL"},
            "total feed": {"column": "total_feed", "operation": "COALESCE(SUM(total_feed), 0)", "filter": "total_feed IS NOT NULL"},

            # Weight-related
            "weight": {"column": "average_bird_weight", "operation": "COALESCE(AVG(average_bird_weight), 0)", "filter": "average_bird_weight IS NOT NULL"},
            "average weight": {"column": "average_bird_weight", "operation": "COALESCE(AVG(average_bird_weight), 0)", "filter": "average_bird_weight IS NOT NULL"},

            # FCR
            "fcr": {"column": "fcr", "operation": "COALESCE(AVG(fcr), 0)", "filter": "fcr IS NOT NULL"},
            "feed conversion": {"column": "fcr", "operation": "COALESCE(AVG(fcr), 0)", "filter": "fcr IS NOT NULL"},
        }

    def _get_schema_info(self):
        """Get database schema information"""
        return {
            "view_name": self.view_name,
            "columns": [
                "owner_id", "farm_id", "farm_name", "flock_id", "flock_name",
                "daily_data_id", "record_date", "birds_died", "total_mort",
                "birds_current", "feed_stock", "feed_consumed_kg", "total_feed",
                "average_bird_weight", "fcr", "sale_id", "sale_date",
                "sale_amount", "purchase_date", "purchase_amount"
            ],
            "security_requirements": f"owner_id = {self.user.id if self.user else 0}"
        }

    def _setup_ollama_chain(self):
        """Initialize Ollama LLM and prompt chain"""
        try:
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

            self.llm = OllamaLLM(
                model="gemma3:1b",
                base_url=f"{ollama_base_url}",
                temperature=0
            )

            # Simple prompt template
            self.sql_prompt = PromptTemplate(
                input_variables=["user_query", "view_name", "security_filter"],
                template="""Generate a SQL query for: {user_query}

Use table: {view_name}
Must include: WHERE {security_filter}

Examples:
- "count sales" → SELECT COUNT(DISTINCT sale_id) FROM {view_name} WHERE {security_filter} AND sale_id IS NOT NULL
- "total sales" → SELECT COALESCE(SUM(sale_amount), 0) FROM {view_name} WHERE {security_filter}
- "mortality in flock 2" → SELECT COALESCE(SUM(birds_died), 0) FROM {view_name} WHERE {security_filter} AND flock_id = 2
- "birds in farm 1" → SELECT COALESCE(SUM(birds_current), 0) FROM {view_name} WHERE {security_filter} AND farm_id = 1

Return only the SQL query:"""
            )

            self.sql_chain = LLMChain(llm=self.llm, prompt=self.sql_prompt)
            print("[✅] SQL Agent: Ollama initialized")

        except Exception as e:
            print(f"[❌] Ollama setup failed: {str(e)}")
            self.llm = None
            self.sql_chain = None

    def query(self, query_text):
        """Main query method - tries rule-based first, then Ollama as fallback"""
        try:
            if not query_text.strip():
                return {"status": "error", "message": "Empty query"}

            if not self.user:
                return {"status": "error", "message": "Authentication required"}

            print(f"[DEBUG] Processing: '{query_text}'")

            # Try rule-based approach first (faster and more reliable)
            sql = self._generate_sql_with_rules(query_text)

            if sql:
                print(f"[DEBUG] Rule-based SQL: {sql}")
                return self._execute_query(sql)

            # Fallback to Ollama if rules don't match
            if self.sql_chain:
                print("[DEBUG] Trying Ollama fallback...")
                sql = self._generate_sql_with_ollama(query_text)
                if sql:
                    print(f"[DEBUG] Ollama SQL: {sql}")
                    return self._execute_query(sql)

            return {
                "status": "error",
                "message": "Could not understand the query",
                "suggestion": "Try: 'count sales', 'total mortality', 'birds in flock 1', 'feed consumed'"
            }

        except Exception as e:
            print(f"[ERROR] Query failed: {str(e)}")
            return {"status": "error", "message": "Query processing failed"}

    def _generate_sql_with_rules(self, query_text):
        """Generate SQL using simple rules and keyword matching"""
        query_lower = query_text.lower().strip()
        base_where = self.schema_info['security_requirements']

        # Extract farm and flock filters
        farm_id = self._extract_number(query_lower, 'farm')
        flock_id = self._extract_number(query_lower, 'flock')

        # Build WHERE clause
        where_clause = base_where
        if farm_id:
            where_clause += f" AND farm_id = {farm_id}"
        if flock_id:
            where_clause += f" AND flock_id = {flock_id}"

        # Find the best matching keyword
        best_match = self._find_best_keyword_match(query_lower)

        if best_match:
            mapping = self.keyword_mappings[best_match]
            operation = mapping["operation"]
            filter_clause = mapping.get("filter")

            if filter_clause:
                where_clause += f" AND {filter_clause}"

            sql = f"SELECT {operation} FROM {self.view_name} WHERE {where_clause}"
            return sql

        return None

    def _extract_number(self, text, keyword):
        """Extract number after a keyword (e.g., 'farm 1' → 1)"""
        pattern = rf'{keyword}\s*(\d+)'
        match = re.search(pattern, text)
        return int(match.group(1)) if match else None

    def _find_best_keyword_match(self, query_text):
        """Find the best matching keyword from mappings"""
        # Sort by length (longest first) to match more specific terms first
        sorted_keywords = sorted(self.keyword_mappings.keys(), key=len, reverse=True)

        for keyword in sorted_keywords:
            if keyword in query_text:
                return keyword

        # Fallback patterns
        if any(word in query_text for word in ['count', 'how many', 'number of']):
            if 'sales' in query_text:
                return 'sales'
            elif 'purchase' in query_text:
                return 'purchases'
            elif 'bird' in query_text:
                return 'birds'
            elif 'farm' in query_text:
                return 'farms'
            elif 'flock' in query_text:
                return 'flocks'

        if any(word in query_text for word in ['total', 'sum']):
            if 'mortality' in query_text or 'death' in query_text:
                return 'total mortality'
            elif 'sales' in query_text:
                return 'total sales'
            elif 'purchase' in query_text:
                return 'total purchases'
            elif 'feed' in query_text:
                return 'total feed'

        return None

    def _generate_sql_with_ollama(self, user_query):
        """Generate SQL using Ollama as fallback"""
        try:
            if not self.sql_chain:
                return None

            result = self.sql_chain.run({
                "user_query": user_query,
                "view_name": self.view_name,
                "security_filter": self.schema_info['security_requirements']
            })

            # Clean the response
            sql = self._clean_sql_response(result)
            return sql

        except Exception as e:
            print(f"[ERROR] Ollama generation failed: {str(e)}")
            return None

    def _clean_sql_response(self, response):
        """Clean up SQL response from Ollama"""
        if not response:
            return None

        response = response.strip()

        # Remove markdown
        if response.startswith('```'):
            lines = response.split('\n')
            for line in lines[1:]:
                if line.strip() and not line.strip().endswith('```'):
                    response = line.strip()
                    break

        # Find SELECT statement
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.upper().startswith('SELECT'):
                return line

        return None

    def _execute_query(self, sql_query):
        """Execute SQL query safely"""
        if not self._is_safe_query(sql_query):
            return {"status": "error", "message": "Invalid or unsafe query"}

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchone()

                return {
                    "status": "success",
                    "data": result[0] if result and result[0] is not None else 0,
                    "query": sql_query
                }

        except Exception as e:
            print(f"[ERROR] SQL execution failed: {str(e)}")
            return {"status": "error", "message": "Query execution failed"}

    def _is_safe_query(self, sql_query):
        """Validate query safety"""
        if not sql_query:
            return False

        sql_lower = sql_query.lower().strip()

        # Must be SELECT only
        if not sql_lower.startswith('select'):
            return False

        # No dangerous operations
        forbidden = ['insert', 'update', 'delete', 'drop', 'create', 'alter', 'truncate', ';']
        if any(op in sql_lower for op in forbidden):
            return False

        # Must use our view
        if self.view_name.lower() not in sql_lower:
            return False

        # Must include owner security filter
        if f"owner_id = {self.user.id}" not in sql_query:
            return False

        return True

import logging
from django.db import connection
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)

class AISQLService:
    def __init__(self, user=None):
        self.user = user
        self.initialized = False
        self._setup_ai()

    def _setup_ai(self):
        try:
            self.llm = OllamaLLM(model="gemma3:1b", temperature=0.1, timeout=60)
            self.ai_chain = LLMChain(
                llm=self.llm,
                prompt=PromptTemplate(input_variables=["prompt"], template="{prompt}")
            )
            self.initialized = True
            print("[✅] AI Service initialized")
        except Exception as e:
            print(f"[❌] AI setup failed: {str(e)}")
            self.initialized = False

    def _get_actual_schema(self):
        """Get the actual column names from your database views"""
        try:
            with connection.cursor() as cursor:
                schema_text = "ACTUAL DATABASE TABLES AND COLUMNS:\n\n"

                views = ['ai_sale_data_view', 'ai_purchase_data_view', 'ai_dailydata_data_view']

                for view_name in views:
                    try:
                        cursor.execute(f"PRAGMA table_info({view_name})")
                        columns = cursor.fetchall()
                        if columns:
                            column_names = [col[1] for col in columns]
                            schema_text += f"{view_name}:\n"
                            schema_text += f"  Columns: {', '.join(column_names)}\n\n"
                        else:
                            schema_text += f"{view_name}: TABLE NOT FOUND\n\n"
                    except Exception as e:
                        schema_text += f"{view_name}: ERROR - {str(e)}\n\n"

                return schema_text
        except Exception as e:
            return f"Schema introspection failed: {str(e)}"

    def query(self, query_text):
        if not self.initialized or not self.user:
            return {"status": "error", "message": "Service not available"}

        try:
            # First, let's get the actual schema from your database
            schema_info = self._get_actual_schema()

            prompt = f"""Generate SQL for farm database query.

ACTUAL DATABASE SCHEMA:
{schema_info}

SECURITY: ALWAYS include WHERE owner_id = {self.user.id}

COLUMN MAPPINGS (what data to access):

Sales-related keywords:
sales → sale_amount from ai_sale_data_view
sales revenue → sale_amount from ai_sale_data_view
sales amount → sale_amount from ai_sale_data_view
revenue → sale_amount from ai_sale_data_view
sales transactions → sale_id from ai_sale_data_view
sales count → sale_id from ai_sale_data_view

Purchase-related keywords:
purchases → purchase_amount from ai_purchase_data_view
purchase amount → purchase_amount from ai_purchase_data_view
expenses → purchase_amount from ai_purchase_data_view
costs → purchase_amount from ai_purchase_data_view
flock cost → flock_cost from ai_purchase_data_view
initial cost → flock_cost from ai_purchase_data_view

Daily data - Birds:
birds → birds_current from ai_dailydata_data_view
current birds → birds_current from ai_dailydata_data_view
bird count → birds_current from ai_dailydata_data_view
mortality → birds_died from ai_dailydata_data_view
birds died → birds_died from ai_dailydata_data_view
deaths → birds_died from ai_dailydata_data_view
dead birds → birds_died from ai_dailydata_data_view

Feed-related:
feed → feed_consumed_kg from ai_dailydata_data_view
feed consumed → feed_consumed_kg from ai_dailydata_data_view
feed consumption → feed_consumed_kg from ai_dailydata_data_view
feed intake → feed_consumed_kg from ai_dailydata_data_view

Performance metrics:
weight → average_bird_weight from ai_dailydata_data_view
bird weight → average_bird_weight from ai_dailydata_data_view
average weight → average_bird_weight from ai_dailydata_data_view
fcr → fcr from ai_dailydata_data_view
feed conversion → fcr from ai_dailydata_data_view
feed conversion ratio → fcr from ai_dailydata_data_view

Count-specific mappings:
farms → farm_id from ai_dailydata_data_view
flocks → flock_id from ai_dailydata_data_view

OPERATION MAPPINGS (how to process the data):

Aggregation operations:
total → SUM
sum → SUM
amount → SUM
count → COUNT
how many → COUNT
number of → COUNT
average → AVG
avg → AVG
mean → AVG

FOR PROFIT/LOSS/NET QUERIES:
1. First identify if the query contains: "profit", "loss", or "net"
2. For farm/flock specific queries, extract numbers after "farm" and "flock"
3. Use this EXACT formula:
   (Total Sales) - (Total Purchases) - (Flock Costs)
4. Structure as:
SELECT (
  (SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE owner_id = {self.user.id} [farm/flock filters]) -
  (SELECT COALESCE(SUM(purchase_amount), 0) FROM ai_purchase_data_view WHERE owner_id = {self.user.id} [farm/flock filters]) -
  (SELECT COALESCE(SUM(DISTINCT flock_cost), 0) FROM ai_purchase_data_view WHERE owner_id = {self.user.id} [farm/flock filters])
) AS result

EXAMPLE: "profit farm 1 flock 2" →
SELECT (
  (SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE owner_id = {self.user.id} AND farm_id = 1 AND flock_id = 2) -
  (SELECT COALESCE(SUM(purchase_amount), 0) FROM ai_purchase_data_view WHERE owner_id = {self.user.id} AND farm_id = 1 AND flock_id = 2) -
  (SELECT COALESCE(SUM(DISTINCT flock_cost), 0) FROM ai_purchase_data_view WHERE owner_id = {self.user.id} AND farm_id = 1 AND flock_id = 2)
)

Min/Max operations (context-dependent):
maximum → MAX
max → MAX
minimum → MIN
min → MIN
highest → MAX
lowest → MIN

FARM/FLOCK FILTERS (VERY IMPORTANT - Parse numbers correctly):
"farm 1" → AND farm_id = 1 (NOT farm_id = 2)
"flock 2" → AND flock_id = 2 (NOT flock_id = 1)
"farm 1 flock 2" → AND farm_id = 1 AND flock_id = 2
"farm 2 flock 3" → AND farm_id = 2 AND flock_id = 3

EXACT SQL PATTERNS:

SALES REVENUE:
SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE owner_id = {self.user.id} AND farm_id = X AND flock_id = Y

BIRDS COUNT:
SELECT COALESCE(SUM(birds_current), 0) FROM ai_dailydata_data_view WHERE owner_id = {self.user.id} AND farm_id = X AND flock_id = Y

MORTALITY:
SELECT COALESCE(SUM(birds_died), 0) FROM ai_dailydata_data_view WHERE owner_id = {self.user.id} AND farm_id = X AND flock_id = Y

EXAMPLES:
"sales revenue farm 1 flock 1" →
SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE owner_id = {self.user.id} AND farm_id = 1 AND flock_id = 1

"profit farm 2 flock 3" →
SELECT (
  (SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE owner_id = {self.user.id} AND farm_id = 2 AND flock_id = 3) -
  (SELECT COALESCE(SUM(purchase_amount), 0) FROM ai_purchase_data_view WHERE owner_id = {self.user.id} AND farm_id = 2 AND flock_id = 3) -
  (SELECT COALESCE(SUM(DISTINCT flock_cost), 0) FROM ai_purchase_data_view WHERE owner_id = {self.user.id} AND farm_id = 2 AND flock_id = 3)
)

USER QUERY: "{query_text}"
Generate only SQL using ACTUAL column names from the schema:"""

            # Generate and validate SQL
            sql_query = self.ai_chain.run({"prompt": prompt})
            cleaned_sql = self._extract_sql(sql_query)

            if not self._is_valid(cleaned_sql):
                return {"status": "error", "message": "Invalid SQL generated"}

            return self._execute_query(cleaned_sql, query_text)

        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return {"status": "error", "message": "Query processing failed"}

    def _extract_sql(self, raw_sql):
        if not raw_sql:
            return None

        sql = raw_sql.strip()

        # Remove markdown
        if '```' in sql:
            parts = sql.split('```')
            if len(parts) > 1:
                sql = parts[1].strip()
                if sql.lower().startswith('sql'):
                    sql = '\n'.join(sql.split('\n')[1:]).strip()

        # Clean and normalize
        if sql.upper().startswith('SELECT'):
            lines = [line.strip() for line in sql.split('\n') if line.strip()]
            return ' '.join(' '.join(lines).split()).rstrip(';')

        return None

    def _is_valid(self, sql):
        if not sql or not sql.lower().startswith('select'):
            return False

        # Security check
        if f"owner_id = {self.user.id}" not in sql:
            return False

        # Table check
        valid_tables = ['ai_sale_data_view', 'ai_purchase_data_view', 'ai_dailydata_data_view']
        if not any(table in sql.lower() for table in valid_tables):
            return False

        # No forbidden operations
        forbidden = ['insert', 'update', 'delete', 'drop', 'create', 'alter']
        if any(op in sql.lower() for op in forbidden):
            return False

        return True

    def _execute_query(self, sql_query, original_query):
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchone()

                result_value = result[0] if result and result[0] is not None else 0

                return {
                    "status": "success",
                    "data": result_value,
                    "query": sql_query,
                    "message": "Query executed successfully"
                }

        except Exception as e:
            logger.error(f"SQL execution failed: {str(e)}")
            return {"status": "error", "message": f"Query execution failed: {str(e)}"}