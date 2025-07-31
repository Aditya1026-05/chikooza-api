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
import os
import re
from django.conf import settings
from django.db import connection
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

logger = logging.getLogger(__name__)

class AISQLService:
    def __init__(self, user=None):
        self.user = user
        # Define the 3 separate views
        self.views = {
            'purchase': 'ai_purchase_data_view',
            'dailydata': 'ai_dailydata_data_view',
            'sale': 'ai_sale_data_view'
        }
        
        # Keep track of initialization state
        self.initialized = False
        self.initialization_error = None
        
        # Build keyword mappings first
        self._build_keyword_mappings()
        
        # Get schema info
        self.schema_info = self._get_schema_info()
        
        # Setup SQL generation
        self._setup_sql_generator()
        
    def _build_keyword_mappings(self):
        """Build comprehensive keyword mappings for rule-based processing"""
        self.keyword_mappings = {
            # Sales-related keywords
            "total sales": {"view": "sale", "operation": "COALESCE(SUM(sale_amount), 0)", "filter": None},
            "sales amount": {"view": "sale", "operation": "COALESCE(SUM(sale_amount), 0)", "filter": None},
            "count sales": {"view": "sale", "operation": "COUNT(DISTINCT sale_id)", "filter": "sale_id IS NOT NULL"},
            "sales": {"view": "sale", "operation": "COUNT(DISTINCT sale_id)", "filter": "sale_id IS NOT NULL"},
            
            # Purchase-related keywords
            "total purchases": {"view": "purchase", "operation": "COALESCE(SUM(purchase_amount), 0)", "filter": None},
            "purchase amount": {"view": "purchase", "operation": "COALESCE(SUM(purchase_amount), 0)", "filter": None},
            "count purchases": {"view": "purchase", "operation": "COUNT(DISTINCT purchase_date)", "filter": "purchase_amount IS NOT NULL"},
            "purchases": {"view": "purchase", "operation": "COUNT(DISTINCT purchase_date)", "filter": "purchase_amount IS NOT NULL"},
            
            # Daily data - Birds
            "current birds": {"view": "dailydata", "operation": "COALESCE(SUM(birds_current), 0)", "filter": "birds_current IS NOT NULL"},
            "birds": {"view": "dailydata", "operation": "COALESCE(SUM(birds_current), 0)", "filter": "birds_current IS NOT NULL"},
            "total mortality": {"view": "dailydata", "operation": "COALESCE(SUM(birds_died), 0)", "filter": "birds_died IS NOT NULL"},
            "mortality": {"view": "dailydata", "operation": "COALESCE(SUM(birds_died), 0)", "filter": "birds_died IS NOT NULL"},
            "birds died": {"view": "dailydata", "operation": "COALESCE(SUM(birds_died), 0)", "filter": "birds_died IS NOT NULL"},
            
            # Feed-related
            "feed consumed": {"view": "dailydata", "operation": "COALESCE(SUM(feed_consumed_kg), 0)", "filter": "feed_consumed_kg IS NOT NULL"},
            "total feed": {"view": "dailydata", "operation": "COALESCE(SUM(total_feed), 0)", "filter": "total_feed IS NOT NULL"},
            "feed": {"view": "dailydata", "operation": "COALESCE(SUM(feed_consumed_kg), 0)", "filter": "feed_consumed_kg IS NOT NULL"},
            
            # Performance metrics
            "average weight": {"view": "dailydata", "operation": "COALESCE(AVG(average_bird_weight), 0)", "filter": "average_bird_weight IS NOT NULL"},
            "weight": {"view": "dailydata", "operation": "COALESCE(AVG(average_bird_weight), 0)", "filter": "average_bird_weight IS NOT NULL"},
            "average fcr": {"view": "dailydata", "operation": "COALESCE(AVG(fcr), 0)", "filter": "fcr IS NOT NULL"},
            "fcr": {"view": "dailydata", "operation": "COALESCE(AVG(fcr), 0)", "filter": "fcr IS NOT NULL"},
            
            # Counts
            "count farms": {"view": "dailydata", "operation": "COUNT(DISTINCT farm_id)", "filter": None},
            "count flocks": {"view": "dailydata", "operation": "COUNT(DISTINCT flock_id)", "filter": None},
            "farms": {"view": "dailydata", "operation": "COUNT(DISTINCT farm_id)", "filter": None},
            "flocks": {"view": "dailydata", "operation": "COUNT(DISTINCT flock_id)", "filter": None},
        }
        
    def _get_schema_info(self):
        """Get comprehensive database schema information for all 3 views"""
        return {
            "views": self.views,
            "security_filter": f"owner_id = {self.user.id if self.user else 0}",
            "sample_queries": [
                "Count total sales",
                "Sum of all sale amounts", 
                "Sum of all purchase amounts",
                "Current birds in farm 1",
                "Total mortality in flock 2", 
                "Average FCR for all flocks",
            ]
        }

    def _setup_sql_generator(self):
        """Initialize Ollama LLM for SQL generation"""
        try:
            ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            
            # Test connection first
            self.llm = OllamaLLM(
                model="gemma3:1b",
                base_url=f"{ollama_base_url}",
                temperature=0,
                timeout=30  # Add timeout
            )
            
            # Create simple SQL generation prompt
            self.sql_prompt = PromptTemplate(
                input_variables=["user_query", "security_filter"],
                template="""Generate a SQL query for: {user_query}

Available views:
- ai_sale_data_view: sale_id, sale_date, sale_amount, farm_id, flock_id
- ai_purchase_data_view: purchase_date, purchase_amount, farm_id, flock_id  
- ai_dailydata_data_view: record_date, birds_current, birds_died, feed_consumed_kg, fcr, average_bird_weight, farm_id, flock_id

MANDATORY: Include WHERE {security_filter} in every query.

Common patterns:
- "count sales" → SELECT COUNT(DISTINCT sale_id) FROM ai_sale_data_view WHERE {security_filter}
- "total sales" → SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE {security_filter}
- "birds in farm 1" → SELECT COALESCE(SUM(birds_current), 0) FROM ai_dailydata_data_view WHERE {security_filter} AND farm_id = 1

Return only the SQL query:"""
            )
            
            # Create LLM chain
            self.sql_chain = LLMChain(
                llm=self.llm, 
                prompt=self.sql_prompt,
                verbose=False  # Reduce verbosity
            )
            
            # Test the chain with a simple query
            test_result = self.sql_chain.run({
                "user_query": "count sales",
                "security_filter": self.schema_info['security_filter']
            })
            
            print(f"[✅] AI SQL Service: Initialized successfully. Test result: {test_result[:100]}...")
            self.initialized = True
            
        except Exception as e:
            self.initialization_error = str(e)
            print(f"[❌] SQL Generator setup failed: {str(e)}")
            self.llm = None
            self.sql_chain = None
            self.initialized = False

    def generate_sql(self, query_text):
        """Generate SQL query from natural language input"""
        try:
            # Input validation
            if not query_text or not query_text.strip():
                return {"status": "error", "message": "Empty query provided"}
            
            if not self.user:
                return {"status": "error", "message": "User authentication required"}
                
            query_text = query_text.strip()
            print(f"[DEBUG] Processing query: '{query_text}'")
            
            # Try rule-based approach first (faster and more reliable)
            rule_result = self._try_rule_based_generation(query_text)
            if rule_result["status"] == "success":
                print(f"[DEBUG] Rule-based successful: {rule_result['query']}")
                return self._execute_query(rule_result["query"], query_text)
            
            # Check if LLM is available
            if not self.initialized:
                return {
                    "status": "error", 
                    "message": "SQL Generator not available",
                    "details": self.initialization_error,
                    "suggestion": "Try: 'count sales', 'total birds', 'birds in farm 1'"
                }
            
            # Try LLM-based generation
            llm_result = self._try_llm_generation(query_text)
            if llm_result["status"] == "success":
                print(f"[DEBUG] LLM successful: {llm_result['query']}")
                return self._execute_query(llm_result["query"], query_text)
            
            # Both approaches failed
            return {
                "status": "error",
                "message": "Could not understand the query",
                "suggestion": "Try: 'count sales', 'total purchases', 'birds in farm 1', 'mortality in flock 2'",
                "rule_error": rule_result.get("message"),
                "llm_error": llm_result.get("message")
            }
            
        except Exception as e:
            print(f"[ERROR] Query processing failed: {str(e)}")
            logger.exception("SQL generation failed")
            return {
                "status": "error", 
                "message": "Query processing failed",
                "error_details": str(e)
            }

    def _try_rule_based_generation(self, query_text):
        """Try to generate SQL using rule-based keyword matching"""
        try:
            query_lower = query_text.lower().strip()
            
            # Handle profit/loss calculation
            if any(keyword in query_lower for keyword in ['profit', 'loss', 'profit loss', 'profit and loss']):
                return self._generate_profit_loss_query(query_lower)
            
            # Extract farm and flock filters
            farm_id = self._extract_number(query_lower, 'farm')
            flock_id = self._extract_number(query_lower, 'flock')
            
            # Build WHERE clause
            where_clause = self.schema_info['security_filter']
            if farm_id:
                where_clause += f" AND farm_id = {farm_id}"
            if flock_id:
                where_clause += f" AND flock_id = {flock_id}"
            
            # Find the best matching keyword
            best_match = self._find_best_keyword_match(query_lower)
            
            if best_match:
                mapping = self.keyword_mappings[best_match]
                view_name = self.views[mapping["view"]]
                operation = mapping["operation"]
                filter_clause = mapping.get("filter")
                
                if filter_clause:
                    where_clause += f" AND {filter_clause}"
                
                sql = f"SELECT {operation} FROM {view_name} WHERE {where_clause}"
                
                return {"status": "success", "query": sql, "method": "rule-based"}
            
            return {"status": "error", "message": "No matching keywords found"}
            
        except Exception as e:
            return {"status": "error", "message": f"Rule-based generation failed: {str(e)}"}

    def _generate_profit_loss_query(self, query_lower):
        """Generate profit/loss calculation query"""
        try:
            # Extract farm and flock filters
            farm_id = self._extract_number(query_lower, 'farm')
            flock_id = self._extract_number(query_lower, 'flock')
            
            # Build filter clause for both subqueries
            base_filter = self.schema_info['security_filter']
            additional_filters = ""
            
            if farm_id:
                additional_filters += f" AND farm_id = {farm_id}"
            if flock_id:
                additional_filters += f" AND flock_id = {flock_id}"
            
            full_filter = base_filter + additional_filters
            
            # Build profit/loss calculation query
            sql = f"""SELECT 
                (SELECT COALESCE(SUM(sale_amount), 0) FROM {self.views['sale']} WHERE {full_filter}) - 
                (SELECT COALESCE(SUM(purchase_amount), 0) FROM {self.views['purchase']} WHERE {full_filter}) - (SELECT DISTINCT flock_cost FROM {self.views['purchase']} 
                WHERE {full_filter})"""
            
            return {"status": "success", "query": sql, "method": "profit-loss"}
            
        except Exception as e:
            return {"status": "error", "message": f"Profit/loss generation failed: {str(e)}"}

    def _try_llm_generation(self, query_text):
        """Try to generate SQL using LLM"""
        try:
            if not self.sql_chain:
                return {"status": "error", "message": "LLM not available"}
            
            # Generate SQL using LLM
            raw_sql = self.sql_chain.run({
                "user_query": query_text,
                "security_filter": self.schema_info['security_filter']
            })
            
            # Clean the response
            cleaned_sql = self._clean_sql_response(raw_sql)
            
            if not cleaned_sql:
                return {"status": "error", "message": "Failed to extract valid SQL from LLM response"}
            
            # Ensure security filter is present
            secured_sql = self._ensure_security_filter(cleaned_sql)
            
            # Validate the query
            if not self._is_safe_query(secured_sql):
                return {"status": "error", "message": "Generated SQL failed security validation"}
            
            return {"status": "success", "query": secured_sql, "method": "llm"}
            
        except Exception as e:
            return {"status": "error", "message": f"LLM generation failed: {str(e)}"}

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
        
        return None

    def _clean_sql_response(self, raw_sql):
        """Clean and extract SQL from LLM response"""
        if not raw_sql:
            return None
        
        sql = raw_sql.strip()
        
        # Remove markdown code blocks
        if '```' in sql:
            parts = sql.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Odd indices contain code
                    lines = part.strip().split('\n')
                    if lines and not lines[0].upper().startswith('SELECT'):
                        lines = lines[1:]  # Skip language identifier
                    sql = '\n'.join(lines).strip()
                    break
        
        # Find the SELECT statement
        lines = sql.split('\n')
        for line in lines:
            line = line.strip()
            if line.upper().startswith('SELECT'):
                # Remove trailing semicolon if present
                if line.endswith(';'):
                    line = line[:-1]
                return line
        
        # Fallback: if the entire response looks like SQL
        if sql.upper().startswith('SELECT'):
            if sql.endswith(';'):
                sql = sql[:-1]
            return sql.strip()
        
        return None

    def _ensure_security_filter(self, sql_query):
        """Ensure the security filter is present in the SQL query"""
        if not sql_query:
            return sql_query
        
        sql_lower = sql_query.lower()
        required_filter = f"owner_id = {self.user.id}"
        
        # Check if security filter is already present
        if required_filter.lower() in sql_lower:
            return sql_query
        
        # Add security filter if missing
        if 'where' in sql_lower:
            # Find the WHERE clause and add the security filter
            where_index = sql_lower.find('where')
            before_where = sql_query[:where_index + 5]  # Include 'WHERE'
            after_where = sql_query[where_index + 5:].strip()
            
            if after_where:
                fixed_sql = f"{before_where} {required_filter} AND {after_where}"
            else:
                fixed_sql = f"{before_where} {required_filter}"
        else:
            # Add WHERE clause with security filter
            fixed_sql = f"{sql_query} WHERE {required_filter}"
        
        return fixed_sql

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
        
        # Must use one of our views
        valid_views = [view.lower() for view in self.views.values()]
        if not any(view in sql_lower for view in valid_views):
            return False
        
        # Must include owner security filter
        if f"owner_id = {self.user.id}" not in sql_query:
            return False
        
        return True

    def _execute_query(self, sql_query, original_query):
        """Execute SQL query safely and return the result"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchone()
                
                # Generate simple human response
                result_value = result[0] if result and result[0] is not None else 0
                human_response = self._generate_simple_explanation(original_query, result_value)
                
                return {
                    "status": "success",
                    "data": result_value,
                    "query": sql_query,
                    "human_response": human_response,
                    "message": "Query executed successfully"
                }
                    
        except Exception as e:
            print(f"[ERROR] SQL execution failed: {str(e)}")
            logger.exception("SQL execution failed")
            return {
                "status": "error", 
                "message": "Query execution failed",
                "query": sql_query,
                "error_details": str(e)
            }

    def _generate_simple_explanation(self, query, result):
        """Generate a simple human-readable explanation"""
        query_lower = query.lower()
        
        if 'profit' in query_lower or 'loss' in query_lower:
            if result > 0:
                return f"You have a profit of ₹{result:,.2f}"
            elif result < 0:
                return f"You have a loss of ₹{abs(result):,.2f}"
            else:
                return "You are at break-even (no profit or loss)"
        elif 'count' in query_lower or 'how many' in query_lower:
            return f"Total count: {int(result)}"
        elif 'total' in query_lower or 'sum' in query_lower:
            if 'amount' in query_lower or 'sales' in query_lower or 'purchase' in query_lower:
                return f"Total amount: ₹{result:,.2f}"
            else:
                return f"Total: {result:,.0f}"
        elif 'average' in query_lower:
            return f"Average: {result:.2f}"
        else:
            return f"Result: {result}"

    def test_connection(self):
        """Test the service connection and functionality"""
        try:
            if not self.initialized:
                return {
                    "status": "error", 
                    "message": "Service not initialized",
                    "details": self.initialization_error
                }
            
            # Test with a simple query
            test_result = self.generate_sql("count sales")
            
            return {
                "status": "success" if test_result["status"] == "success" else "error",
                "message": "Service working properly" if test_result["status"] == "success" else "Service test failed",
                "test_query": "count sales",
                "test_result": test_result
            }
                
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Connection test failed: {str(e)}"
            }

    # Alias for backward compatibility
    def query(self, query_text):
        """Alias for generate_sql method"""
        return self.generate_sql(query_text)