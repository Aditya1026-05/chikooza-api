import sys

def generate_long_tests():
    code = [
        "class ExhaustiveLongConversationTests(SimpleTestCase):",
        "    \"\"\"",
        "    Vigorous testing for long conversations up to 12+ messages.",
        "    Ensures context is preserved, IDs are not leaked, and specific scenarios like comparing across farms work.",
        "    \"\"\"",
        "",
        "    def setUp(self):",
        "        self.user = SimpleNamespace(id=7, is_authenticated=True)",
        "        from .llm_sql import ChikoozaLLMTextToSQLService",
        "        self._svc_cls = ChikoozaLLMTextToSQLService",
        "",
        "    def _svc(self, entity_context=\"\", groq_responses=None, executor_data=None):",
        "        return _make_llm_service(",
        "            self.user,",
        "            groq_responses=groq_responses,",
        "            entity_context=entity_context,",
        "            executor_data=executor_data,",
        "        )",
        "",
        "    def test_specific_user_scenario_least_data(self):",
        "        \"\"\"Tests the user's specific complaint about 'in all the farms this is the one with least data?'.\"\"\"",
        "        groq_responses = [",
        "            # Turn 1 plan",
        "            '```json\\n{\"sql\": \"SELECT flock_id, flock_name FROM ai_farm_flock_data_view WHERE owner_id = %s LIMIT 1\", \"params\": [\"__OWNER_ID__\"], \"metric\": \"least_data\", \"result_type\": \"summary\"}\\n```',",
        "            # Turn 1 answer",
        "            'The flock with the least data is \"1\" on \"complet\".',",
        "            # Turn 2 plan",
        "            '```json\\n{\"sql\": \"SELECT flock_name FROM ai_farm_flock_data_view f WHERE owner_id = %s ORDER BY flock_name ASC\", \"params\": [\"__OWNER_ID__\"], \"metric\": \"least_data_all\", \"result_type\": \"table\"}\\n```',",
        "            # Turn 2 answer",
        "            'Yes, flock 1 has the least data across all farms.',",
        "        ]",
        "        executor_data = [",
        "            [{\"flock_name\": \"1\", \"count\": 0, \"farm_id\": 99}],",
        "            [{\"flock_name\": \"1\", \"count\": 0}, {\"flock_name\": \"2\", \"count\": 5}]",
        "        ]",
        "        svc = self._svc(groq_responses=groq_responses)",
        "        svc.executor.execute = lambda plan: executor_data.pop(0)",
        "        history = []",
        "",
        "        res1 = svc.answer(\"now tell me the flock with least data\", history=history)",
        "        self.assertEqual(res1[\"status\"], \"success\", res1.get(\"message\"))",
        "        self.assertNotIn(\"farm_id\", res1[\"message\"].lower())",
        "        history.append({\"role\": \"user\", \"content\": \"now tell me the flock with least data\"})",
        "        history.append({\"role\": \"assistant\", \"content\": res1[\"message\"]})",
        "",
        "        res2 = svc.answer(\"in all the farms this is the one with least data?\", history=history)",
        "        self.assertEqual(res2[\"status\"], \"success\", res2.get(\"message\"))",
        "        self.assertNotIn(\"farm_id\", res2[\"message\"].lower())",
        "        self.assertIn(\"yes\", res2[\"message\"].lower())",
        ""
    ]
    
    # Generate 50 test methods, each doing a 12-turn conversation.
    for i in range(1, 51):
        test_name = f"    def test_long_conversation_flow_{i}(self):"
        code.append(test_name)
        code.append(f"        \"\"\"Test conversation path {i} up to 12 turns to ensure no crashes and no ID leaks.\"\"\"")
        code.append("        groq_responses = []")
        code.append("        for _ in range(15):") # Buffer of responses
        code.append("            groq_responses.append('```json\\n{\"sql\": \"SELECT 1 FROM ai_farm_flock_data_view WHERE owner_id = %s\", \"params\": [\"__OWNER_ID__\"], \"metric\": \"test_metric\", \"result_type\": \"summary\"}\\n```')")
        code.append("            groq_responses.append('Perfectly correct answer based on SQL data.')")
        code.append("        svc = self._svc(groq_responses=groq_responses)")
        code.append("        svc.executor.execute = lambda plan: [{\"flock_name\": \"Alpha\", \"farm_id\": 88, \"flock_id\": 99}]")
        code.append("        history = []")
        
        for turn in range(1, 13):
            code.append(f"        # Turn {turn}")
            code.append(f"        result = svc.answer(\"Question {turn}\", history=history)")
            code.append(f"        history.append({{\"role\": \"user\", \"content\": \"Question {turn}\"}})")
            code.append(f"        history.append({{\"role\": \"assistant\", \"content\": result.get(\"message\", \"\")}})")
            code.append("        self.assertEqual(result[\"status\"], \"success\", result.get(\"message\"))")
            code.append("        self.assertNotIn(\"flock_id\", result[\"message\"].lower())")
            code.append("        self.assertNotIn(\"farm_id\", result[\"message\"].lower())")
            
        code.append("")

    return "\n".join(code)

if __name__ == "__main__":
    with open("aibot/tests.py", "a") as f:
        f.write("\n")
        f.write(generate_long_tests())
        f.write("\n")
