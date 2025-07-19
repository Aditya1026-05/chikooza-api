# services.py
import re
import logging
from django.conf import settings
from pathlib import Path
from django.db import connection
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_community.llms import Ollama
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.agents import AgentExecutor, AgentType

logger = logging.getLogger(__name__)

class SQLAgentService:
    def __init__(self, user=None, view_name="ai_farm_data_view"):
        self.user = user
        self.db_path = Path(settings.DATABASES['default']['NAME'])
        self.view_name = view_name
        
        # Initialize LLM with more conservative settings
        self.llm = Ollama(
            model=getattr(settings, 'AI_MODEL', 'gemma3:1b'),
            temperature=0,
            top_p=0.9,
            num_ctx=2048,  # Reduced for stability
        )
        
        # Initialize database connection
        self.db = SQLDatabase.from_uri(
            f"sqlite:///{self.db_path}",
            include_tables=[self.view_name],
            sample_rows_in_table_info=2,
            view_support=True
        )
        
        self._initialize_agent()

    def _initialize_agent(self):
        """Initialize agent with minimal configuration"""
        self.toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)
        
        # Very simple and direct system message
        system_message = f"""You are a SQL assistant. Use the {self.view_name} view and always filter by owner_id = {self.user.id if self.user else 'NULL'}.

Rules:
- Only SELECT queries
- Always include WHERE owner_id = {self.user.id if self.user else 'NULL'}
- Be direct and concise"""
        
        self.agent_executor = create_sql_agent(
            llm=self.llm,
            toolkit=self.toolkit,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,  # Reduce verbosity
            max_iterations=2,  # Very limited iterations
            handle_parsing_errors=True,
            agent_executor_kwargs={
                "handle_parsing_errors": True,
                "return_intermediate_steps": True
            },
            prefix=system_message
        )

    def query(self, query_text):
        """Handle queries with intelligent fallback system"""
        try:
            query = query_text.strip()
            if not query:
                return {"status": "error", "message": "Empty query"}
            
            if not self.user:
                return {"status": "error", "message": "Authentication required"}
            
            # Step 1: Try smart SQL generation first
            smart_sql = self._generate_smart_sql(query)
            if smart_sql:
                result = self._execute_query(smart_sql)
                if result["status"] == "success":
                    return result
            
            # Step 2: Try agent with very simple prompt
            try:
                simple_prompt = f"Answer: {query}"
                result = self.agent_executor.invoke({"input": simple_prompt})
                processed = self._process_output(result)
                if processed["status"] == "success":
                    return processed
            except Exception as e:
                logger.warning(f"Agent failed: {str(e)}")
            
            # Step 3: Fallback to basic schema-based SQL generation
            fallback_sql = self._generate_fallback_sql(query)
            if fallback_sql:
                return self._execute_query(fallback_sql)
            
            return {
                "status": "error",
                "message": "Could not understand the query",
                "suggestion": "Try asking: 'How many farms do I have?' or 'What is my total sales?'"
            }
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return {
                "status": "error",
                "message": "Query processing failed",
                "details": str(e)
            }

    def _generate_smart_sql(self, query):
        """Generate SQL using pattern matching for common queries"""
        query_lower = query.lower().strip()
        user_id = self.user.id
        
        # Pattern-based SQL generation
        patterns = {
            # Farm counting patterns
            r'(how many|count|number of).*(farm|farms)': 
                f"SELECT COUNT(DISTINCT farm_id) FROM {self.view_name} WHERE owner_id = {user_id}",
            
            # Flock counting patterns  
            r'(how many|count|number of).*(flock|flocks)':
                f"SELECT COUNT(DISTINCT flock_id) FROM {self.view_name} WHERE owner_id = {user_id}",
            
            # Sales patterns
            r'(total|sum|all).*(sale|sales|revenue)':
                f"SELECT COALESCE(SUM(sale_amount), 0) FROM {self.view_name} WHERE owner_id = {user_id}",
            
            # Purchase patterns
            r'(total|sum|all).*(purchase|cost|expense)':
                f"SELECT COALESCE(SUM(purchase_amount), 0) FROM {self.view_name} WHERE owner_id = {user_id}",
            
            # Current birds
            r'(how many|total|current).*(bird|birds|chicken)':
                f"SELECT COALESCE(SUM(birds_current), 0) FROM {self.view_name} WHERE owner_id = {user_id}",
            
            # Mortality
            r'(total|sum).*(mort|death|died)':
                f"SELECT COALESCE(SUM(birds_died), 0) FROM {self.view_name} WHERE owner_id = {user_id}",
            
            # Feed consumption
            r'(total|sum).*(feed|consumption)':
                f"SELECT COALESCE(SUM(feed_consumed_kg), 0) FROM {self.view_name} WHERE owner_id = {user_id}",
        }
        
        for pattern, sql in patterns.items():
            if re.search(pattern, query_lower):
                return sql
        
        return None

    def _generate_fallback_sql(self, query):
        """Generate basic SQL for common column queries"""
        query_lower = query.lower()
        user_id = self.user.id
        
        # Map common terms to columns
        column_mappings = {
            'farm': 'farm_id',
            'flock': 'flock_id', 
            'sale': 'sale_amount',
            'purchase': 'purchase_amount',
            'bird': 'birds_current',
            'feed': 'feed_consumed_kg',
            'weight': 'average_bird_weight'
        }
        
        # Check for counting queries
        if any(word in query_lower for word in ['count', 'how many', 'number']):
            for term, column in column_mappings.items():
                if term in query_lower:
                    if term in ['farm', 'flock']:
                        return f"SELECT COUNT(DISTINCT {column}) FROM {self.view_name} WHERE owner_id = {user_id}"
                    else:
                        return f"SELECT COUNT(*) FROM {self.view_name} WHERE owner_id = {user_id} AND {column} IS NOT NULL"
        
        # Check for sum/total queries
        if any(word in query_lower for word in ['total', 'sum', 'all']):
            for term, column in column_mappings.items():
                if term in query_lower and column not in ['farm_id', 'flock_id']:
                    return f"SELECT COALESCE(SUM({column}), 0) FROM {self.view_name} WHERE owner_id = {user_id}"
        
        return None

    def _process_output(self, agent_result):
        """Enhanced output processing with better extraction"""
        output = agent_result.get("output", "").strip()
        intermediate_steps = agent_result.get("intermediate_steps", [])
        
        # Try to get SQL from intermediate steps first
        for step in intermediate_steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                if hasattr(action, 'tool') and action.tool == 'sql_db_query':
                    sql_query = self._clean_sql_query(str(action.tool_input))
                    if sql_query:
                        validation = self._validate_query(sql_query)
                        if validation["valid"]:
                            try:
                                raw_result = self.db.run(sql_query)
                                return {
                                    "status": "success",
                                    "data": self._format_result(raw_result),
                                    "query": sql_query
                                }
                            except Exception as e:
                                logger.error(f"Intermediate step execution failed: {str(e)}")
                                continue
                
                # Also check observation for direct results
                if isinstance(observation, str) and observation.strip().isdigit():
                    return {
                        "status": "success",
                        "data": int(observation.strip()),
                        "query": "From agent observation"
                    }
        
        # Extract SQL from output text
        sql_patterns = [
            r"```sql\s*(.*?)\s*```",
            r"```\s*(SELECT.*?)\s*```",
            r"(SELECT\s+.*?(?:;|\n|$))",
        ]
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, output, re.DOTALL | re.IGNORECASE)
            for match in matches:
                cleaned_sql = self._clean_sql_query(match)
                if cleaned_sql:
                    validation = self._validate_query(cleaned_sql)
                    if validation["valid"]:
                        try:
                            raw_result = self.db.run(cleaned_sql)
                            return {
                                "status": "success",
                                "data": self._format_result(raw_result),
                                "query": cleaned_sql
                            }
                        except Exception as e:
                            continue
        
        # Look for direct numeric answers
        number_patterns = [
            r"Final Answer:\s*(\d+)",
            r"Answer:\s*(\d+)",
            r"Result:\s*(\d+)",
            r"\b(\d+)\b"
        ]
        
        for pattern in number_patterns:
            match = re.search(pattern, output)
            if match:
                return {
                    "status": "success",
                    "data": int(match.group(1)),
                    "query": "Extracted from agent response"
                }
        
        return {
            "status": "error",
            "message": "Could not process response",
            "details": output[:200],
            "suggestion": "Try rephrasing your question more specifically"
        }

    def _clean_sql_query(self, sql_input):
        """Clean SQL query from agent output"""
        if not sql_input:
            return None
            
        sql = str(sql_input).strip()
        
        # Remove various prefixes that cause issues
        prefixes = [
            r"Action\s*Input:\s*",
            r"Action:\s*", 
            r"```sql\s*",
            r"```\s*",
            r"SQL:\s*",
            r"Query:\s*"
        ]
        
        for prefix in prefixes:
            sql = re.sub(prefix, "", sql, flags=re.IGNORECASE)
        
        # Remove trailing artifacts
        sql = re.sub(r"```.*$", "", sql, flags=re.DOTALL)
        sql = re.sub(r"Action:.*$", "", sql, flags=re.DOTALL)
        
        # Clean up
        sql = sql.strip()
        if sql and not sql.endswith(';'):
            sql += ';'
        
        # Must be a SELECT statement
        if sql and sql.upper().strip().startswith('SELECT'):
            return sql
        
        return None

    def _execute_query(self, sql_query):
        """Execute SQL query with validation"""
        validation = self._validate_query(sql_query)
        if not validation["valid"]:
            return {
                "status": "error",
                "message": validation["message"],
                "query": sql_query
            }
            
        try:
            raw_result = self.db.run(sql_query)
            return {
                "status": "success",
                "data": self._format_result(raw_result),
                "query": sql_query
            }
        except Exception as e:
            logger.error(f"SQL execution failed: {str(e)}")
            return {
                "status": "error",
                "message": f"Execution failed: {str(e)}",
                "query": sql_query
            }

    def _validate_query(self, sql_query):
        """Validate query security and requirements"""
        if not sql_query:
            return {"valid": False, "message": "Empty query"}
            
        sql_lower = sql_query.lower()
        user_id = str(self.user.id) if self.user else 'null'
        
        # Security checks
        forbidden = ['insert', 'update', 'delete', 'drop', 'create', 'alter', 'truncate']
        if any(op in sql_lower for op in forbidden):
            return {"valid": False, "message": "Forbidden operation"}
        
        # Must use the view
        if self.view_name.lower() not in sql_lower:
            return {"valid": False, "message": f"Must use {self.view_name}"}
        
        # Must filter by owner_id
        owner_patterns = [f"owner_id = {user_id}", f"owner_id={user_id}"]
        if not any(pattern in sql_lower.replace(" ", "") for pattern in owner_patterns):
            return {"valid": False, "message": "Must filter by owner_id"}
        
        return {"valid": True}

    def _format_result(self, raw_result):
        """Format SQL results consistently"""
        if raw_result is None or raw_result == "":
            return 0
            
        if isinstance(raw_result, str):
            raw_result = raw_result.strip()
            
            # Handle direct numbers
            if raw_result.isdigit():
                return int(raw_result)
            
            # Handle tuple format like "[(5,)]"
            if raw_result.startswith('[') and raw_result.endswith(']'):
                try:
                    parsed = eval(raw_result)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        if isinstance(parsed[0], tuple):
                            return parsed[0][0] if len(parsed[0]) > 0 else 0
                        return parsed[0]
                except Exception:
                    pass
            
            # Handle pipe-separated tables
            if '|' in raw_result and '\n' in raw_result:
                lines = [l.strip() for l in raw_result.split('\n') if l.strip()]
                if len(lines) >= 3:
                    headers = [h.strip() for h in lines[0].split('|') if h.strip()]
                    data_rows = []
                    for line in lines[2:]:
                        values = [v.strip() for v in line.split('|') if v.strip()]
                        if len(values) == len(headers):
                            data_rows.append(dict(zip(headers, values)))
                    return data_rows if len(data_rows) > 1 else (data_rows[0] if data_rows else 0)
            
            # Extract any number
            number_match = re.search(r'\b(\d+(?:\.\d+)?)\b', raw_result)
            if number_match:
                num_str = number_match.group(1)
                return float(num_str) if '.' in num_str else int(num_str)
        
        # Handle direct numeric types
        if isinstance(raw_result, (int, float)):
            return raw_result
        
        return raw_result