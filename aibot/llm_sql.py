import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import httpx
from flocks.models import Flock
from farm.models import Farm

from common.groq_client import GroqAllKeysFailed, GroqChatClient

from .modern_services import (
    SQLPlan,
    TEXT_TO_SQL,
    TenantSafeSQLExecutor,
    normalize_ai_query,
)

logger = logging.getLogger(__name__)

OWNER_PARAM = "__OWNER_ID__"
AIBOT_SQL_DEFAULT_MODEL = "llama-3.1-8b-instant"


CHIKOOZA_SQL_SCHEMA = """
Allowed SQL views and columns:

1. ai_farm_flock_data_view
   Purpose: farms and flock master data, including farms with no flocks.
   Columns:
   owner_id, farm_id, farm_name, farm_address, farm_city, farm_pin, shed_count,
   farm_status, flock_id, flock_name, hatch_date, flock_size, actual_birds,
   chick_weight, feed_sys, drinking_sys, ec_shed, flock_cost, flock_bird,
   flock_status, breed_name, hatchery_name, integrator_name.

2. ai_sale_data_view
   Purpose: flock sales/revenue/lifting records.
   Columns:
   owner_id, farm_id, farm_name, farm_city, flock_id, flock_name, flock_size,
   actual_birds, sale_id, sale_type, sale_date, lifting_count, total_weight,
   average_weight, rate_per_kg, sale_amount, buyer, vehicle_no, sale_remarks,
   feed_total, med_price, vacc_price, admin_charges, rearing_charges,
   performance_incentives, rate_incentives, production_cost_recovery, shortages,
   excess_mortality, fcr_recovery, integration_cost.

3. ai_purchase_data_view
   Purpose: feed, medicine, vaccination, equipment, labour and other purchases.
   Columns:
   owner_id, farm_id, farm_name, farm_city, flock_id, flock_name, flock_size,
   actual_birds, flock_cost, purchase_type, purchase_date, purchase_amount,
   quantity, purchased_item, item_type, unit, size, company_name, purchase_remarks,
   adjust, adjust_type.

4. ai_dailydata_data_view
   Purpose: daily flock performance, mortality, feed, weight, FCR and status.
   Columns:
   owner_id, farm_id, farm_name, farm_city, flock_id, flock_name, flock_size,
   actual_birds, daily_data_id, record_date, birds_died, total_mort,
   birds_current, feed_stock, feed_consumed_kg, total_feed,
   average_bird_weight, average_feed, total_average_feed, fcr, total_fcr,
   cooling, heating, seek, medicine, remarks, daily_data_status,
   darkness_time_name, feed_availability_name, flock_birds.
""".strip()


SQL_GENERATION_SYSTEM = f"""
You are Chikooza Farmer AI's SQL planner.
Return ONLY one valid JSON object. No markdown. No explanation.

JSON shape:
{{
  "sql": "SELECT ... WHERE owner_id = %s ...",
  "params": ["{OWNER_PARAM}", "..."],
  "metric": "short_metric_name",
  "result_type": "money|count|decimal|quantity|table|summary"
}}

Hard rules:
1. Use ONLY these views:
{CHIKOOZA_SQL_SCHEMA}
2. Every referenced view must be tenant-filtered with owner_id = %s.
3. Never put the numeric farmer/user id in SQL or params. For each owner_id = %s placeholder, put "{OWNER_PARAM}" at the same position in params. The backend replaces it with the authenticated farmer id.
3a. Params count must exactly match SQL placeholder count. If the SQL has 5 "%s" placeholders, return exactly 5 params. If all 5 are owner_id filters, return "{OWNER_PARAM}" five times.
4. Use %s placeholders for every dynamic value. Do not inline names, dates, ids, or text values.
5. Do not use SELECT *. Select only useful columns.
6. Generate exactly one SELECT statement. No INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, PRAGMA, ATTACH, DETACH, GRANT, REVOKE, or semicolon-separated statements.
7. Use SQLite/PostgreSQL-compatible SQL only: LOWER(col) LIKE LOWER(%s), SUBSTR(CAST(date_col AS TEXT), 1, 7) for month, SUBSTR(CAST(date_col AS TEXT), 1, 4) for year, LIMIT N.
8. For row-list queries, add LIMIT 100 unless the user asks for a smaller limit.
9. "my", "our", "me", "us", and "this farmer" mean the authenticated farmer only.
10. If the user asks for another farmer/user/customer's private data, return {{"blocked": true, "reason": "cross_tenant_request"}}.
11. If the question is not answerable from these views, return {{"blocked": true, "reason": "not_answerable_from_farm_data"}}.
12. If the user asks a follow-up like "what about that flock", "i meant daily data", "now in detail", "same farm", or "compare it", use Entity Context plus the recent conversation to resolve the farm/flock/metric context.
13. If Entity Context resolves a farm/flock mention, use the resolved internal farm_id/flock_id exactly in the WHERE clause (e.g. `farm_id = %s` or `flock_id = %s`). HOWEVER, if the question is comparative, ranking, or asks if 'this' entity is the best/worst/least among others (e.g. 'is this the one with least data in all farms?'), do NOT filter by the resolved entity ID in the SQL WHERE clause. Instead, generate a query that ranks/lists all entities so the AI can see where 'this' entity stands and answer the question correctly. Do NOT just return a different random entity.
14. Entity priority is: current explicit farm/flock mention first, then current resolved Entity Context, then the last referenced farm/flock from recent chat for unresolved follow-ups.
15. If the user asks "daily data only", query ai_dailydata_data_view only. Do not answer with only flock master data.
16. If the user asks "daily data and everything" after a selected flock, answer for that selected flock unless the user clearly asks for the whole account.
17. If the user asks "total flocks in each farm", group by farm_id/farm_name and count DISTINCT flock_id. Do not ask the user to choose one farm.
18. "active farm", "current farm", "selected farm", "active flock", "current flock", and "selected flock" mean the Active app farm/flock from Entity Context. Use those resolved ids when present.
19. Do not restrict broad, list, count, comparative, ranking, or extremum questions (e.g., best, worst, least, most, highest, lowest, top, bottom, compare, all, every, each, list, count) to the active or resolved app context. Answer across the authenticated farmer's full account (all farms and flocks) and do NOT filter by resolved farm_id or flock_id in the SQL WHERE clause, unless they explicitly name a specific farm or flock in their current question.
20. Prefer simple, explicit SQL over clever SQL. The production model is llama-3.1-8b-instant, so copy the exact SQL patterns below whenever the question matches them.
21. For one-field questions like "breed of active flock", "hatch date of first flock", or "farm city", return only that row/column plus the identifying farm/flock name.
22. For conversational text like "thanks", "okay", "nothing more", "huh", or "what do you mean", return {{"blocked": true, "reason": "conversation_only"}} unless the text clearly asks for farm data.
23. For spelling mistakes, infer the intended farm term when safe: "glock" means "flock", "poltry" means poultry only in the public bot, "sails" means sales.
24. If the user asks 'which days', 'when', 'what dates', 'on which date', or 'on which day' for any daily metric (e.g., mortality/deaths, feed, weight, FCR), select `record_date` and the metric columns from `ai_dailydata_data_view`. Do NOT use aggregate functions like SUM() or AVG() to squash the days into a single row unless they explicitly ask for a total or average. Order the individual days by the metric (ASC for lowest/best, DESC for highest/worst) to find the target days.

Common Chikooza mappings:
- revenue/sales/income -> SUM(sale_amount) from ai_sale_data_view.
- cost/expense/spent/purchase -> SUM(purchase_amount) from ai_purchase_data_view.
- profit/loss/net -> sales minus purchases minus flock_cost. Avoid duplicated flock_cost by aggregating it per flock first.
- mortality/deaths/dead birds -> SUM(birds_died), total_mort, or latest birds_current from ai_dailydata_data_view.
- FCR/feed conversion -> AVG(fcr), latest fcr, or total_fcr based on wording.
- current birds/current flock size -> latest birds_current ordered by record_date DESC.
- best flock -> compare low FCR, low mortality, high average weight, or high profit based on wording.
- latest/current -> ORDER BY the relevant date column DESC LIMIT 1.
- vague farmer English like "total things", "what all I have", "show my stuff", "my data", "my records", or incomplete grammar should map to a safe account summary, not a blocked answer.

Column ownership rules:
- sale_amount exists only in ai_sale_data_view.
- purchase_amount, purchased_item, company_name, purchase_type exist only in ai_purchase_data_view.
- fcr, total_fcr, birds_died, total_mort, birds_current, feed_consumed_kg, average_bird_weight exist only in ai_dailydata_data_view.
- farm_address, shed_count, hatch_date, flock_cost, breed_name, hatchery_name exist in ai_farm_flock_data_view.
- flock_cost also exists in ai_purchase_data_view, but prefer ai_farm_flock_data_view for flock-cost-only questions.
- When Entity Context gives a resolved farm_id/flock_id, filter with that id: `flock_id = %s` or `farm_id = %s`. Do not use the farmer's rough text as the id.

Exact SQL patterns to copy when relevant:
1. Profit for a flock or farm:
{{
  "sql": "SELECT base.flock_id, base.flock_name, COALESCE(sales.total_sales, 0) AS total_sales, COALESCE(purchases.total_purchases, 0) AS total_purchases, COALESCE(base.flock_cost, 0) AS flock_cost, COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS result FROM (SELECT flock_id, flock_name, MAX(flock_cost) AS flock_cost FROM ai_farm_flock_data_view WHERE owner_id = %s AND LOWER(flock_name) LIKE LOWER(%s) GROUP BY flock_id, flock_name) base LEFT JOIN (SELECT flock_id, SUM(sale_amount) AS total_sales FROM ai_sale_data_view WHERE owner_id = %s GROUP BY flock_id) sales ON sales.flock_id = base.flock_id LEFT JOIN (SELECT flock_id, SUM(purchase_amount) AS total_purchases FROM ai_purchase_data_view WHERE owner_id = %s GROUP BY flock_id) purchases ON purchases.flock_id = base.flock_id",
  "params": ["{OWNER_PARAM}", "%flock name%", "{OWNER_PARAM}", "{OWNER_PARAM}"],
  "metric": "profit_by_flock",
  "result_type": "money"
}}
2. Compare feed and sales by flock:
{{
  "sql": "SELECT d.flock_id, d.flock_name, COALESCE(d.feed_consumed_kg, 0) AS feed_consumed_kg, COALESCE(s.total_sales, 0) AS total_sales FROM (SELECT flock_id, flock_name, SUM(feed_consumed_kg) AS feed_consumed_kg FROM ai_dailydata_data_view WHERE owner_id = %s GROUP BY flock_id, flock_name) d LEFT JOIN (SELECT flock_id, SUM(sale_amount) AS total_sales FROM ai_sale_data_view WHERE owner_id = %s GROUP BY flock_id) s ON s.flock_id = d.flock_id ORDER BY d.flock_name LIMIT 100",
  "params": ["{OWNER_PARAM}", "{OWNER_PARAM}"],
  "metric": "feed_sales_by_flock",
  "result_type": "table"
}}
3. Latest mortality/current birds for one flock:
{{
  "sql": "SELECT record_date, flock_id, flock_name, birds_died, total_mort, birds_current, fcr, average_bird_weight FROM ai_dailydata_data_view WHERE owner_id = %s AND LOWER(flock_name) LIKE LOWER(%s) AND daily_data_id IS NOT NULL ORDER BY record_date DESC LIMIT 1",
  "params": ["{OWNER_PARAM}", "%flock name%"],
  "metric": "latest_flock_status",
  "result_type": "summary"
}}
4. Vague account summary / total things:
{{
  "sql": "SELECT (SELECT COUNT(DISTINCT farm_id) FROM ai_farm_flock_data_view WHERE owner_id = %s AND farm_id IS NOT NULL) AS farm_count, (SELECT COUNT(DISTINCT flock_id) FROM ai_farm_flock_data_view WHERE owner_id = %s AND flock_id IS NOT NULL) AS flock_count, (SELECT COALESCE(SUM(current_rows.birds_current), 0) FROM ai_dailydata_data_view current_rows WHERE current_rows.owner_id = %s AND current_rows.daily_data_id IS NOT NULL AND current_rows.record_date = (SELECT MAX(compare_rows.record_date) FROM ai_dailydata_data_view compare_rows WHERE compare_rows.owner_id = %s AND compare_rows.flock_id = current_rows.flock_id AND compare_rows.daily_data_id IS NOT NULL)) AS current_birds, (SELECT COALESCE(SUM(sale_amount), 0) FROM ai_sale_data_view WHERE owner_id = %s) AS total_sales, (SELECT COALESCE(SUM(purchase_amount), 0) FROM ai_purchase_data_view WHERE owner_id = %s) AS total_purchases, (SELECT COALESCE(SUM(feed_consumed_kg), 0) FROM ai_dailydata_data_view WHERE owner_id = %s) AS total_feed_consumed, (SELECT COALESCE(SUM(birds_died), 0) FROM ai_dailydata_data_view WHERE owner_id = %s) AS total_mortality, (SELECT COALESCE(AVG(fcr), 0) FROM ai_dailydata_data_view WHERE owner_id = %s AND fcr IS NOT NULL) AS average_fcr",
  "params": ["{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}"],
  "metric": "farm_record_summary",
  "result_type": "summary"
}}
5. Flock count in each farm:
{{
  "sql": "SELECT farm_id, farm_name, COUNT(DISTINCT flock_id) AS flock_count FROM ai_farm_flock_data_view WHERE owner_id = %s AND farm_id IS NOT NULL GROUP BY farm_id, farm_name ORDER BY farm_name LIMIT 100",
  "params": ["{OWNER_PARAM}"],
  "metric": "flock_count_by_farm",
  "result_type": "table"
}}
6. Daily data rows for one resolved flock:
{{
  "sql": "SELECT record_date, flock_id, flock_name, birds_died, total_mort, birds_current, feed_consumed_kg, total_feed, average_bird_weight, fcr, remarks, daily_data_status FROM ai_dailydata_data_view WHERE owner_id = %s AND flock_id = %s AND daily_data_id IS NOT NULL ORDER BY record_date DESC LIMIT 100",
  "params": ["{OWNER_PARAM}", 4],
  "metric": "daily_data_by_flock",
  "result_type": "table"
}}
7. Complete one-flock report with daily, sales, purchases and profit:
{{
  "sql": "SELECT base.flock_id, base.flock_name, base.farm_name, base.hatch_date, base.flock_size, base.actual_birds, base.breed_name, COALESCE(latest.birds_current, 0) AS current_birds, COALESCE(daily.total_mortality, 0) AS total_mortality, COALESCE(daily.total_feed_consumed, 0) AS total_feed_consumed, COALESCE(daily.average_weight, 0) AS average_weight, COALESCE(daily.average_fcr, 0) AS average_fcr, COALESCE(sales.total_sales, 0) AS total_sales, COALESCE(purchases.total_purchases, 0) AS total_purchases, COALESCE(base.flock_cost, 0) AS flock_cost, COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS profit_loss FROM (SELECT flock_id, flock_name, farm_name, hatch_date, flock_size, actual_birds, breed_name, MAX(flock_cost) AS flock_cost FROM ai_farm_flock_data_view WHERE owner_id = %s AND flock_id = %s GROUP BY flock_id, flock_name, farm_name, hatch_date, flock_size, actual_birds, breed_name) base LEFT JOIN (SELECT flock_id, SUM(birds_died) AS total_mortality, SUM(feed_consumed_kg) AS total_feed_consumed, AVG(average_bird_weight) AS average_weight, AVG(fcr) AS average_fcr FROM ai_dailydata_data_view WHERE owner_id = %s AND flock_id = %s AND daily_data_id IS NOT NULL GROUP BY flock_id) daily ON daily.flock_id = base.flock_id LEFT JOIN (SELECT current_rows.flock_id, current_rows.birds_current FROM ai_dailydata_data_view current_rows WHERE current_rows.owner_id = %s AND current_rows.flock_id = %s AND current_rows.daily_data_id IS NOT NULL AND current_rows.record_date = (SELECT MAX(compare_rows.record_date) FROM ai_dailydata_data_view compare_rows WHERE compare_rows.owner_id = %s AND compare_rows.flock_id = current_rows.flock_id AND compare_rows.daily_data_id IS NOT NULL)) latest ON latest.flock_id = base.flock_id LEFT JOIN (SELECT flock_id, SUM(sale_amount) AS total_sales FROM ai_sale_data_view WHERE owner_id = %s AND flock_id = %s GROUP BY flock_id) sales ON sales.flock_id = base.flock_id LEFT JOIN (SELECT flock_id, SUM(purchase_amount) AS total_purchases FROM ai_purchase_data_view WHERE owner_id = %s AND flock_id = %s GROUP BY flock_id) purchases ON purchases.flock_id = base.flock_id",
  "params": ["{OWNER_PARAM}", 4, "{OWNER_PARAM}", 4, "{OWNER_PARAM}", 4, "{OWNER_PARAM}", "{OWNER_PARAM}", 4, "{OWNER_PARAM}", 4],
  "metric": "complete_flock_report",
  "result_type": "summary"
}}
8. One direct field for a resolved/active flock:
{{
  "sql": "SELECT flock_id, flock_name, farm_name, breed_name FROM ai_farm_flock_data_view WHERE owner_id = %s AND flock_id = %s LIMIT 1",
  "params": ["{OWNER_PARAM}", 4],
  "metric": "active_flock_breed",
  "result_type": "summary"
}}
9. Performance / health summary for all flocks:
{{
  "sql": "SELECT base.flock_id, base.flock_name, base.farm_name, COALESCE(daily.total_feed_consumed, 0) AS total_feed, COALESCE(daily.total_mortality, 0) AS total_mortality, COALESCE(daily.average_weight, 0) AS avg_weight, COALESCE(daily.average_fcr, 0) AS avg_fcr, COALESCE(sales.total_sales, 0) AS total_sales, COALESCE(purchases.total_purchases, 0) AS total_purchases, COALESCE(base.flock_cost, 0) AS flock_cost, COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS profit_loss, COALESCE(daily.daily_data_status, 0) AS daily_data_status FROM (SELECT flock_id, flock_name, farm_name, MAX(flock_cost) AS flock_cost FROM ai_farm_flock_data_view WHERE owner_id = %s AND flock_id IS NOT NULL GROUP BY flock_id, flock_name, farm_name) base LEFT JOIN (SELECT flock_id, SUM(feed_consumed_kg) AS total_feed_consumed, SUM(birds_died) AS total_mortality, AVG(average_bird_weight) AS average_weight, AVG(fcr) AS average_fcr, MAX(daily_data_status) AS daily_data_status FROM ai_dailydata_data_view WHERE owner_id = %s AND daily_data_id IS NOT NULL GROUP BY flock_id) daily ON daily.flock_id = base.flock_id LEFT JOIN (SELECT flock_id, SUM(sale_amount) AS total_sales FROM ai_sale_data_view WHERE owner_id = %s GROUP BY flock_id) sales ON sales.flock_id = base.flock_id LEFT JOIN (SELECT flock_id, SUM(purchase_amount) AS total_purchases FROM ai_purchase_data_view WHERE owner_id = %s GROUP BY flock_id) purchases ON purchases.flock_id = base.flock_id ORDER BY base.farm_name, base.flock_name LIMIT 100",
  "params": ["{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}", "{OWNER_PARAM}"],
  "metric": "flock_performance",
  "result_type": "table"
}}
10. List all flocks (master data):
{{
  "sql": "SELECT flock_id, flock_name, farm_name, hatch_date, flock_size, actual_birds, breed_name, flock_status FROM ai_farm_flock_data_view WHERE owner_id = %s AND flock_id IS NOT NULL GROUP BY flock_id, flock_name, farm_name, hatch_date, flock_size, actual_birds, breed_name, flock_status ORDER BY farm_name, flock_name LIMIT 100",
  "params": ["{OWNER_PARAM}"],
  "metric": "flock_list",
  "result_type": "table"
}}

11. Days with lowest/highest mortality, feed, weight, or FCR for a flock:
{{
  "sql": "SELECT record_date, flock_name, farm_name, birds_died FROM ai_dailydata_data_view WHERE owner_id = %s AND flock_id = %s AND daily_data_id IS NOT NULL ORDER BY birds_died ASC LIMIT 10",
  "params": ["{OWNER_PARAM}", 4],
  "metric": "lowest_mortality_days",
  "result_type": "table"
}}

Do not mix aggregate functions like SUM/AVG with plain row columns unless you also GROUP BY those row columns. For latest/current questions, prefer latest row fields over SUM. Do not use CTE/WITH because the validator accepts one SELECT statement over approved views only. If the query asks for 'which days', 'when', 'what dates', 'on which date', or 'on which day' for daily metrics (like mortality, FCR, weight, feed, etc.), select `record_date` and the metric columns from `ai_dailydata_data_view`. Order by the metric (ASC for lowest/best, DESC for highest/worst) and do NOT use aggregate functions like SUM() or AVG().
24. "performance", "how are my flocks doing", "how is my farm doing", "flock health", "farm performance", or "flock stats" always map to pattern 9 (flock_performance) for the full account, or pattern 7 (complete_flock_report) for a single resolved flock. Never block these.
""".strip()


ANSWER_SYSTEM = """
You are Chikooza Farmer AI.
Explain the SQL result in simple farmer-friendly English.
Do not mention SQL, database tables, JSON, prompts, or implementation details.
Do not mention internal numeric ids such as farm_id, flock_id, sale_id, purchase_id, daily_data_id, owner_id, or public_id unless the farmer explicitly asks for ids. CRITICAL ID BAN: Never, under any circumstances, output raw database ID values (like farm_id=9, flock_id=4, owner_id=1, etc.) in your conversational response. Strip them entirely from the final text. Refer to farms and flocks only by their names (e.g., 'Demo Farm 1').
When id columns are present in result rows, use them only to keep records separate internally; show farm/flock names to the farmer.
Be precise with numbers and units. Use Rs. for money.
If a result column is feed_consumed_kg, call it kg of feed, not generic units.
If records are missing, say what data is missing and what the farmer should enter.
For comparison answers, state the winner and the main reason. If the question asks to compare, rank, or identify specific flocks (such as the best, worst, highest, lowest, or middle zone), you MUST analyze the rows, name the winning/losing/middle flocks, and explain your reasoning in the text answer. Do not leave the comparison to the table/cards. When discussing financial results, you MUST use the term 'net profit' if the value is positive or zero, and 'net loss' if the value is negative. NEVER use the combined phrases 'profit loss', 'profit/loss', or similar when referring to actual numeric figures (e.g., say 'net loss of Rs. 15,330', NOT 'profit loss of Rs. 15,330' or 'profit/loss of Rs. -15,330' or 'profit loss of Rs. -15,330').
Keep simple answers to 1-3 sentences. Use short bullets only for multi-row results.
For one direct fact, answer directly in one sentence.
For multi-row results, use one short intro and structured rows/bullets. Do not write a long paragraph.
If the metric is current_workspace, answer only the current/selected farm and flock names. Do not switch to another flock and do not add unrelated details.
If the metric is most_profitable_flock, name the flock and farm first, then show net profit = sales - purchases - flock cost. If the result is negative, say no flock is profitable yet and this is the least-loss flock among records that have both sales and cost data. If data_note is present, mention that the ranking may be incomplete because cost/purchase/sales records are missing.
If the metric is biggest_loss_flock, name the flock and farm first, then show net loss (the absolute/positive value of the negative result, e.g., 'net loss of Rs. 15,330' instead of a negative number or 'profit loss').
If the metric is best_performing_flock, use the row's result as net result. If result is negative, say this is the least-loss flock among complete financial records, not a profitable flock. Never invent higher sales or profit than the rows show.
If the metric is worst_performing_flock, use the row with the smallest result as the worst performer. Explain net loss, sales, purchases, flock cost, mortality, feed, FCR, and missing-data notes only from the rows.
If the metric starts with daily_metric_extreme_, answer only from the provided rows. Mention the exact record_date, flock_name, point_type (highest/lowest), metric_value, and units. Do not invent dates that are not in the rows.
If the metric is sales_count_leader or sales_amount_leader, name the flock and farm first, then mention sale count or total sales.
If the metric is most_used_breed, state the top breed and how many flocks use it.
If the metric is flock_breeds_by_flock, list each flock with its farm and breed. Do not collapse the answer to only unique breed names.
If the metric is improvement_advice, do not only restate the table. Give 3-5 practical priorities based on the rows: biggest loss, high mortality, high FCR, missing sales, missing purchases, or missing daily data.
If the question asks "which can I do to improve", answer as advice from saved records, not as a raw report.
If the farmer says thanks, okay, nothing more, huh, or similar conversational text, do not invent a data summary.
Never claim to know another farmer's private data.
""".strip()


@dataclass(frozen=True)
class LLMPlanPayload:
    sql: str
    params: list[Any]
    metric: str
    result_type: str


class ChikoozaSQLPromptBuilder:
    """Builds the strict SQL-generation messages sent to Groq."""

    def messages(
        self,
        question: str,
        history: list[dict] | None = None,
        entity_context: str = "",
    ) -> list[dict[str, str]]:
        history_text = self._history_text(history or [])
        user_prompt = f"""
Recent conversation:
{history_text or "No previous conversation in this chat."}

Entity Context:
{entity_context or "No farm/flock entity was pre-resolved."}

Current farmer question:
{question}

Return the JSON SQL plan now.
""".strip()
        return [
            {"role": "system", "content": SQL_GENERATION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

    def _history_text(self, history: list[dict]) -> str:
        parts = []
        # U: OLD: only eight messages were sent, which dropped part of a
        # U: six-turn chat. Keep six user turns + six assistant turns.
        for item in history[-16:]:
            role = item.get("role", "user")
            content = str(item.get("content", "")).strip()
            if content:
                metadata = self._safe_metadata_text(item)
                if metadata:
                    parts.append(f"{role.title()}: {content} [{metadata}]")
                else:
                    parts.append(f"{role.title()}: {content}")
        return "\n".join(parts)

    def _safe_metadata_text(self, item: dict) -> str:
        fields = []
        for key in (
            "resolved_farm_id",
            "resolved_flock_id",
            "intent_entity_type",
            "intent_entity_reference",
            "metric",
        ):
            value = item.get(key)
            if value not in (None, ""):
                fields.append(f"{key}={value}")
        return ", ".join(fields)


@dataclass(frozen=True)
class EntityResolution:
    context: str
    direct_response: dict | None = None


class ChikoozaEntityResolver:
    """
    U: NEW: Resolve rough farmer language such as "flock 1", "first flock", or
    U: a public id into the authenticated farmer's actual farm/flock before the
    U: LLM builds SQL. This prevents the LLM from treating "flock 1" as a raw
    U: database id that may not exist for this farmer.
    """

    FLOCK_NUMBER_PATTERN = re.compile(r"\bflock\s*(?:id|#)?\s*(\d+)\b")
    FARM_NUMBER_PATTERN = re.compile(r"\bfarm\s*(?:id|#)?\s*(\d+)\b")
    ORDINAL_WORDS = {
        "first": 1,
        "1st": 1,
        "second": 2,
        "2nd": 2,
        "third": 3,
        "3rd": 3,
        "fourth": 4,
        "4th": 4,
        "fifth": 5,
        "5th": 5,
    }

    def __init__(self, user):
        self.user = user

    def resolve(
        self,
        question: str,
        history: list[dict] | None = None,
        active_context: dict | None = None,
    ) -> EntityResolution:
        farms = self._farms()
        flocks = self._flocks()
        query = normalize_ai_query(question)
        active_farm, active_flock = self._active_entities(
            active_context or {},
            farms,
            flocks,
        )
        context_lines = [
            self._available_farms_context(farms),
            self._available_flocks_context(flocks),
        ]
        active_context_text = self._active_context_text(active_farm, active_flock)
        if active_context_text:
            context_lines.append(active_context_text)
        history_context = self._history_entity_context(history or [], farms, flocks)
        if history_context:
            context_lines.append(history_context)

        flock_resolution = self._resolve_flock(
            query,
            flocks,
            active_flock=active_flock,
        )
        if flock_resolution == "not_found":
            return EntityResolution(
                context="\n".join(context_lines),
                direct_response=self._missing_flock_response(query, flocks),
            )
        if flock_resolution == "active_missing":
            return EntityResolution(
                context="\n".join(context_lines),
                direct_response=self._active_missing_response("flock", flocks),
            )
        if flock_resolution:
            context_lines.append(
                "Resolved flock mention: "
                f"flock_id={flock_resolution.id}, "
                f"flock_public_id={flock_resolution.public_id}, "
                f"flock_name={flock_resolution.name}, "
                f"farm_id={flock_resolution.farm.id}, "
                f"farm_name={flock_resolution.farm.name}."
            )

        farm_resolution = self._resolve_farm(
            query,
            farms,
            active_farm=active_farm,
        )
        if farm_resolution == "not_found":
            return EntityResolution(
                context="\n".join(context_lines),
                direct_response=self._missing_farm_response(query, farms),
            )
        if farm_resolution == "active_missing":
            return EntityResolution(
                context="\n".join(context_lines),
                direct_response=self._active_missing_response("farm", farms),
            )
        if farm_resolution:
            context_lines.append(
                "Resolved farm mention: "
                f"farm_id={farm_resolution.id}, "
                f"farm_public_id={farm_resolution.public_id}, "
                f"farm_name={farm_resolution.name}."
            )

        return EntityResolution(context="\n".join(context_lines))

    def _active_entities(self, active_context: dict, farms: list, flocks: list):
        farm_public_id = self._safe_public_id(active_context.get("selected_farm_public_id"))
        flock_public_id = self._safe_public_id(active_context.get("selected_flock_public_id"))
        active_farm = self._find_by_public_id(farms, farm_public_id)
        active_flock = self._find_by_public_id(flocks, flock_public_id)
        if active_flock and not active_farm:
            active_farm = getattr(active_flock, "farm", None)
        return active_farm, active_flock

    def _active_context_text(self, active_farm, active_flock) -> str:
        lines = []
        if active_farm:
            lines.append(
                "Active app farm context: "
                f"farm_id={active_farm.id}, "
                f"farm_public_id={active_farm.public_id}, "
                f"farm_name={active_farm.name}."
            )
        if active_flock:
            lines.append(
                "Active app flock context: "
                f"flock_id={active_flock.id}, "
                f"flock_public_id={active_flock.public_id}, "
                f"flock_name={active_flock.name}, "
                f"farm_id={active_flock.farm.id}, "
                f"farm_name={active_flock.farm.name}."
            )
        return "\n".join(lines)

    def _history_entity_context(
        self,
        history: list[dict],
        farms: list,
        flocks: list,
    ) -> str:
        for item in reversed(history[-16:]):
            if item.get("role") != "assistant":
                continue
            flock_id = item.get("resolved_flock_id")
            if flock_id is not None:
                flock = self._find_by_id(flocks, flock_id)
                if flock:
                    return (
                        "Last referenced flock from recent chat: "
                        f"flock_id={flock.id}, "
                        f"flock_public_id={flock.public_id}, "
                        f"flock_name={flock.name}, "
                        f"farm_id={flock.farm.id}, "
                        f"farm_name={flock.farm.name}."
                    )
            farm_id = item.get("resolved_farm_id")
            if farm_id is not None:
                farm = self._find_by_id(farms, farm_id)
                if farm:
                    return (
                        "Last referenced farm from recent chat: "
                        f"farm_id={farm.id}, "
                        f"farm_public_id={farm.public_id}, "
                        f"farm_name={farm.name}."
                    )
        return ""

    def _farms(self):
        return list(Farm.objects.filter(user=self.user).order_by("id")[:30])

    def _flocks(self):
        return list(
            Flock.objects.filter(user=self.user)
            .select_related("farm")
            .order_by("id")[:50]
        )

    def _resolve_flock(self, query: str, flocks: list, active_flock=None):
        if not flocks:
            return None

        if self._active_flock_reference_requested(query):
            return active_flock or "active_missing"

        numeric_match = self.FLOCK_NUMBER_PATTERN.search(query)
        if numeric_match:
            number = int(numeric_match.group(1))
            exact = self._find_by_id_or_public_id(flocks, number)
            if exact:
                return exact
            if 1 <= number <= len(flocks):
                return flocks[number - 1]
            return "not_found"

        ordinal = self._ordinal_for_phrase(query, "flock")
        if ordinal:
            if 1 <= ordinal <= len(flocks):
                return flocks[ordinal - 1]
            return "not_found"

        for flock in flocks:
            if self._name_matches_query(flock.name, query):
                return flock

        if self._looks_like_named_flock_reference(query):
            return "not_found"

        return None

    def _resolve_farm(self, query: str, farms: list, active_farm=None):
        if not farms:
            return None

        if self._active_farm_reference_requested(query):
            return active_farm or "active_missing"

        numeric_match = self.FARM_NUMBER_PATTERN.search(query)
        if numeric_match:
            number = int(numeric_match.group(1))
            exact = self._find_by_id_or_public_id(farms, number)
            if exact:
                return exact
            if 1 <= number <= len(farms):
                return farms[number - 1]
            return "not_found"

        ordinal = self._ordinal_for_phrase(query, "farm")
        if ordinal:
            if 1 <= ordinal <= len(farms):
                return farms[ordinal - 1]
            return "not_found"

        for farm in farms:
            if self._name_matches_query(farm.name, query):
                return farm

        return None

    def _name_matches_query(self, name: str | None, query: str) -> bool:
        if not name:
            return False
        normalized_name = normalize_ai_query(str(name))
        if not normalized_name:
            return False
        if normalized_name == query:
            return True
        # U: NEW: avoid matching one-letter flock names such as "a" inside
        # U: normal sentences like "selected farm and flock".
        if len(normalized_name) < 3:
            return bool(
                re.search(
                    rf"\b(?:farm|flock|batch|named|called)\s+{re.escape(normalized_name)}\b",
                    query,
                )
            )
        return bool(re.search(rf"\b{re.escape(normalized_name)}\b", query))

    def _find_by_id_or_public_id(self, objects: list, number: int):
        return next(
            (
                obj
                for obj in objects
                if self._safe_public_id(obj.id) == number
                or self._safe_public_id(getattr(obj, "public_id", None)) == number
            ),
            None,
        )

    def _find_by_public_id(self, objects: list, public_id: int | None):
        if public_id is None:
            return None
        return next(
            (
                obj
                for obj in objects
                if self._safe_public_id(getattr(obj, "public_id", None)) == public_id
            ),
            None,
        )

    def _find_by_id(self, objects: list, object_id):
        try:
            object_id = int(object_id)
        except (TypeError, ValueError):
            return None
        return next((obj for obj in objects if int(obj.id) == object_id), None)

    def _ordinal_for_phrase(self, query: str, label: str) -> int | None:
        for word, value in self.ORDINAL_WORDS.items():
            if re.search(rf"\b(?:{word}\s+{label}|{label}\s+{word})\b", query):
                return value
        return None

    def _active_flock_reference_requested(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:active|current|selected)\b",
                query,
            )
            and re.search(r"\b(?:flock|batch)\b", query)
        )

    def _active_farm_reference_requested(self, query: str) -> bool:
        return bool(
            re.search(r"\b(?:active|current|selected)\b", query)
            and re.search(r"\bfarm\b", query)
        )

    def _safe_public_id(self, value) -> int | None:
        try:
            if value in (None, "", "0"):
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _looks_like_named_flock_reference(self, query: str) -> bool:
        if re.search(
            r"\b(?:all|every|each|which|what|list|others|other|rest|remaining|flocks|batches)\b",
            query,
        ):
            return False
        return bool(
            re.search(r"\b(?:for|of|in|about)\s+[a-z0-9 ]*(?:batch|flock)\b", query)
        )

    def _available_farms_context(self, farms: list) -> str:
        if not farms:
            return "Available farms for this farmer: none."
        farm_text = "; ".join(
            f"{index}. farm_id={farm.id}, farm_public_id={farm.public_id}, farm_name={farm.name}"
            for index, farm in enumerate(farms, start=1)
        )
        return f"Available farms for this farmer: {farm_text}."

    def _available_flocks_context(self, flocks: list) -> str:
        if not flocks:
            return "Available flocks for this farmer: none."
        flock_text = "; ".join(
            (
                f"{index}. flock_id={flock.id}, flock_public_id={flock.public_id}, "
                f"flock_name={flock.name}, farm_name={flock.farm.name}"
            )
            for index, flock in enumerate(flocks, start=1)
        )
        return f"Available flocks for this farmer: {flock_text}."

    def _missing_flock_response(self, query: str, flocks: list) -> dict:
        available = ", ".join(flock.name for flock in flocks) if flocks else "none yet"
        return {
            "status": "success",
            "data": {"available_flocks": [flock.name for flock in flocks]},
            "answer": (
                "I could not find that flock in your account. "
                f"Available flocks: {available}. "
                "Please ask using the flock name, or use first/second flock if you mean list position."
            ),
            "message": (
                "I could not find that flock in your account. "
                f"Available flocks: {available}."
            ),
            "rows": [],
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "metric": "missing_flock",
            "engine": "entity_resolver",
        }

    def _missing_farm_response(self, query: str, farms: list) -> dict:
        available = ", ".join(farm.name for farm in farms) if farms else "none yet"
        return {
            "status": "success",
            "data": {"available_farms": [farm.name for farm in farms]},
            "answer": (
                "I could not find that farm in your account. "
                f"Available farms: {available}. "
                "Please ask using the farm name, or use first/second farm if you mean list position."
            ),
            "message": (
                "I could not find that farm in your account. "
                f"Available farms: {available}."
            ),
            "rows": [],
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "metric": "missing_farm",
            "engine": "entity_resolver",
        }

    def _active_missing_response(self, entity_type: str, objects: list) -> dict:
        names = ", ".join(obj.name for obj in objects) if objects else "none yet"
        label = "flock" if entity_type == "flock" else "farm"
        return {
            "status": "success",
            "data": {f"available_{label}s": [obj.name for obj in objects]},
            "answer": (
                f"I do not know which {label} is active yet. "
                f"Available {label}s: {names}. "
                f"Select a {label} in the app or ask using its name."
            ),
            "message": (
                f"I do not know which {label} is active yet. "
                f"Available {label}s: {names}."
            ),
            "rows": [],
            "query": None,
            "params": [],
            "route": TEXT_TO_SQL,
            "metric": f"missing_active_{label}",
            "engine": "entity_resolver",
        }


class ChikoozaLLMTextToSQLService:
    """
    U: Groq-backed Farmer AI SQL service adapted from the separate chatbot repo.
    U: The live class has no old deterministic answer fallback. Common,
    U: high-volume farmer questions can still use tenant-safe SQL templates to
    U: reduce Groq planning calls, but answers are built from executed SQL rows
    U: plus Groq formatting, not the old rule-answer engine.
    """

    MAX_SQL_ATTEMPTS = 2

    def __init__(
        self,
        user,
        *,
        groq_client: GroqChatClient | None = None,
        entity_resolver: ChikoozaEntityResolver | None = None,
    ):
        self.user = user
        self.executor = TenantSafeSQLExecutor()
        self.prompt_builder = ChikoozaSQLPromptBuilder()
        self.entity_resolver = entity_resolver or ChikoozaEntityResolver(user=user)
        self.client = groq_client or GroqChatClient(
            # U: NEW: keep the private Farmer AI pinned to the approved 8B
            # U: Groq model so SQL planning and answer formatting are tested
            # U: against one predictable production model.
            model=AIBOT_SQL_DEFAULT_MODEL,
            fallback_model=AIBOT_SQL_DEFAULT_MODEL,
            timeout=float(os.getenv("AIBOT_SQL_TIMEOUT", "30")),
        )

    @property
    def is_available(self) -> bool:
        return self.client.has_keys

    def answer(
        self,
        question: str,
        history: list[dict] | None = None,
        active_context: dict | None = None,
    ) -> dict:
        if not self.is_available:
            return self._sql_error_response("Groq is not configured.")

        query_norm = normalize_ai_query(question)
        if re.search(r"\b(?:farm|flock|user|owner|sale|purchase|dailydata|record|lifting|buyer|data)\s*ids?\b", query_norm) or re.search(r"\b(?:what|show|give|tell|display|get)\b.*\bids?\b", query_norm):
            if not re.search(r"\b(?:how\s+many|count|number\s+of)\b", query_norm):
                return {
                    "status": "error",
                    "message": "I cannot display internal database IDs. Please ask about your farm names, flocks, sales, purchases, daily data, mortality, feed, FCR, or profit.",
                    "suggestion": "Try asking for your farm names, flock details, sales, or profit.",
                    "route": TEXT_TO_SQL,
                    "engine": "groq_sql",
                }

        conversation_answer = self._conversation_only_answer(question)
        if conversation_answer:
            return {
                "status": "success",
                "data": None,
                "answer": conversation_answer,
                "message": conversation_answer,
                "rows": [],
                "query": None,
                "params": [],
                "route": TEXT_TO_SQL,
                "metric": "conversation_only",
                "engine": "groq_sql_conversation_guard",
            }

        last_error: Exception | None = None
        error_feedback = ""
        entity_resolution = self.entity_resolver.resolve(
            question,
            history=history,
            active_context=active_context,
        )
        if entity_resolution.direct_response:
            return entity_resolution.direct_response

        known_plan = self._known_safe_plan(
            question,
            history=history,
            entity_context=entity_resolution.context,
        )
        if known_plan:
            try:
                return self._response_from_plan(
                    question,
                    known_plan,
                    history,
                    entity_context=entity_resolution.context,
                )
            except Exception as exc:
                last_error = exc
                error_feedback = str(exc)[:500]
                logger.warning("Known safe SQL plan failed: %s", exc)

        for _attempt in range(self.MAX_SQL_ATTEMPTS):
            try:
                plan = self._build_plan(
                    question,
                    history,
                    entity_context=entity_resolution.context,
                    error_feedback=error_feedback,
                )
                return self._response_from_plan(
                    question,
                    plan,
                    history,
                    entity_context=entity_resolution.context,
                )
            except BlockedAIQuery as exc:
                return {
                    "status": "error",
                    "message": self._blocked_message(str(exc)),
                    "suggestion": self._blocked_suggestion(str(exc)),
                    "route": TEXT_TO_SQL,
                    "engine": "groq_sql",
                }
            except Exception as exc:
                last_error = exc
                error_feedback = str(exc)[:500]
                logger.warning("Groq SQL attempt failed: %s", exc)

        return self._sql_error_response(str(last_error or "Unknown LLM SQL failure."))

    def _response_from_plan(
        self,
        question: str,
        plan: SQLPlan,
        history: list[dict] | None,
        *,
        entity_context: str = "",
    ) -> dict:
        rows = self.executor.execute(plan)
        answer = self._format_answer(
            question,
            plan,
            rows,
            history,
            entity_context=entity_context,
        )
        metadata = self._entity_metadata(entity_context)
        if rows and isinstance(rows, list) and len(rows) > 0:
            first_row = rows[0]
            if isinstance(first_row, dict):
                sql_flock_id = first_row.get("flock_id")
                sql_farm_id = first_row.get("farm_id")
                if sql_flock_id is not None and "resolved_flock_id" not in metadata:
                    try:
                        metadata["resolved_flock_id"] = int(sql_flock_id)
                        metadata["intent_entity_type"] = "flock"
                    except (TypeError, ValueError):
                        pass
                if sql_farm_id is not None and "resolved_farm_id" not in metadata:
                    try:
                        metadata["resolved_farm_id"] = int(sql_farm_id)
                        if "intent_entity_type" not in metadata:
                            metadata["intent_entity_type"] = "farm"
                    except (TypeError, ValueError):
                        pass
        display = self._display_payload(plan, rows)
        if (
            display
            and self._is_comparative_query(question)
            and not plan.metric.startswith("daily_metric_extreme_")
        ):
            display = None
        return {
            "status": "success",
            "data": rows[0] if len(rows) == 1 else rows,
            "answer": answer,
            "message": answer,
            "rows": rows,
            "query": plan.sql,
            "params": plan.params,
            "route": TEXT_TO_SQL,
            "metric": plan.metric,
            "engine": "groq_sql",
            "display": display,
            **metadata,
        }

    def _known_safe_plan(
        self,
        question: str,
        *,
        history: list[dict] | None,
        entity_context: str = "",
    ) -> SQLPlan | None:
        query = normalize_ai_query(question)
        # --- Priority -1: Compound / Jumbled queries fall through to LLM ---
        if self._is_compound_query(query):
            return None

        # U: NEW: These are not the old deterministic answer rules. They are
        # U: safety-first SQL plan shortcuts for common farmer questions that
        # U: llama-3.1-8b-instant was repeatedly planning incorrectly. Groq
        # U: still formats the executed SQL rows into natural language.
        if self._asks_current_workspace(query):
            active_farm_id, active_flock_id = self._active_context_ids(entity_context)
            if active_flock_id:
                return self._current_workspace_plan(active_flock_id=active_flock_id)
            if active_farm_id:
                return self._current_workspace_plan(active_farm_id=active_farm_id)

        # --- Priority 0: Generic follow-up scope inheritance ---
        if self._is_generic_flock_followup(query):
            generic_plan = self._generic_flock_followup_plan(
                query,
                history=history,
                context_flock_id=self._context_flock_id(entity_context),
            )
            if generic_plan:
                return generic_plan

        context_flock_id = self._context_flock_id(entity_context)

        # --- Priority 0.5: Daily metric extremes / follow-up date questions ---
        # U: "when is feed highest", "mortality lowest", "FCR lowest and highest"
        # U: must use daily rows for the current/resolved flock. Do not let broad
        # U: "highest/lowest" scope logic turn these into account aggregates.
        daily_metric_column = self._daily_time_series_metric(query)
        if self._asks_daily_time_series(query) and daily_metric_column:
            return self._daily_metric_extremes_plan(
                metric_column=daily_metric_column,
                direction=self._daily_extreme_direction(query),
                flock_id=(
                    None
                    if self._asks_all_daily_scope(query)
                    else context_flock_id
                ),
            )

        # --- Priority 0.6: Best/worst performing flock rankings ---
        # U: These are financial/performance rankings and must not be answered by
        # U: a generic "flock performance" table, because the LLM has previously
        # U: hallucinated profit values from that table.
        performance_extreme = self._performance_extreme_kind(query)
        if performance_extreme == "best":
            return self._flock_performance_ranking_plan(
                metric="best_performing_flock",
                order_direction="DESC",
                limit=1,
            )
        if performance_extreme == "worst":
            return self._flock_performance_ranking_plan(
                metric="worst_performing_flock",
                order_direction="ASC",
                limit=1,
            )

        # --- Priority 1: Advice / diagnostic (must beat performance) ---
        if self._asks_improvement_advice(query):
            return self._improvement_advice_plan()

        # --- Priority 2: Performance / health / stats ---
        # Must come BEFORE flock_list so "performance of my flocks" doesn't
        # accidentally match the flock-list detector.
        if self._asks_performance(query):
            is_plural_or_general = bool(
                re.search(r"\b(?:flocks|batches)\b", query)
                or (re.search(r"\bflock\s+performance\b", query) and not re.search(r"\b(?:my|this|current|active|selected|its)\b", query))
            )
            if context_flock_id and not self._asks_all_scope(query, history) and not is_plural_or_general:
                return self._complete_flock_report_plan(context_flock_id)
            return self._all_flocks_performance_plan()

        # --- Priority 3: FCR and Weight (before flock_list which also matches 'my flocks') ---
        # U: Skip aggregate plans when the user asks for specific days/dates.
        if self._asks_avg_fcr(query) and not self._asks_daily_time_series(query):
            return self._avg_fcr_plan(flock_id=context_flock_id if not self._asks_all_scope(query, history) else None)

        if self._asks_avg_weight(query) and not self._asks_daily_time_series(query):
            return self._avg_weight_plan(flock_id=context_flock_id if not self._asks_all_scope(query, history) else None)

        # --- Priority 4: Single-flock detail (before account summary: 'all details of this flock') ---
        if self._asks_one_flock_details(query) and context_flock_id:
            return self._complete_flock_report_plan(context_flock_id)

        # --- Priority 5: Account summary ---
        if self._asks_account_summary(query):
            return self._account_summary_plan()

        # --- Priority 5.5: Single active farm/flock details ---
        context_farm_id = self._context_farm_id(entity_context)
        if context_farm_id and self._asks_single_farm_query(query):
            return self._single_farm_plan(context_farm_id)

        if context_flock_id and self._asks_single_flock_query(query):
            return self._complete_flock_report_plan(context_flock_id)

        # --- Priority 6: Farm / flock list and count ---
        if self._asks_farm_list(query, entity_context):
            return self._farm_list_plan_llm()

        if self._asks_flock_list(query, entity_context) and not self._asks_flock_breed(query, broad=True):
            return self._flock_list_plan_llm()

        if self._asks_farm_count(query):
            return self._farm_count_plan()

        if self._asks_flock_count(query):
            return self._flock_count_plan()

        # --- Priority 7: Breed questions ---
        if self._asks_all_flock_breeds(query, history):
            return self._all_flock_breeds_plan()

        if self._asks_other_flock_breeds(query, history):
            return self._all_flock_breeds_plan(exclude_flock_id=context_flock_id)

        if self._asks_daily_data(query) and context_flock_id and not self._asks_all_scope(query, history):
            return self._daily_data_for_flock_plan(context_flock_id)

        if self._asks_flock_breed(query) and context_flock_id:
            return self._flock_breed_plan(context_flock_id)

        if self._asks_most_used_breed(query):
            return self._most_used_breed_plan()

        # --- Priority 8.5: Least Data / Comparative rankings ---
        if self._asks_flock_least_data(query) or self._asks_flock_least_data_comparison(query):
            return self._flock_least_data_plan()

        if self._asks_farm_least_data(query) or self._asks_farm_least_data_comparison(query):
            return self._farm_least_data_plan()

        # --- Priority 8: Profit rankings ---
        if self._asks_most_profitable_flock(query):
            return self._profit_ranking_plan(
                metric="most_profitable_flock",
                order_direction="DESC",
                limit=1,
            )

        if self._asks_biggest_loss(query):
            return self._profit_ranking_plan(
                metric="biggest_loss_flock",
                order_direction="ASC",
                limit=1,
                losses_only=True,
            )

        if self._asks_sales_count_leader(query):
            return self._sales_leader_plan(metric="sales_count_leader", by="count")

        if self._asks_sales_amount_leader(query, history):
            return self._sales_leader_plan(metric="sales_amount_leader", by="amount")

        # --- Priority 9: Profit/loss (must come BEFORE sales/purchases) ---
        if self._asks_profit_loss(query):
            if self._asks_all_scope(query, history):
                return self._profit_ranking_plan(
                    metric="profit_loss_by_flock",
                    order_direction="DESC",
                    limit=100,
                )
            if context_flock_id:
                return self._profit_for_flock_plan(context_flock_id)
            # Broad profit question without flock context — return all-flock summary
            return self._profit_ranking_plan(
                metric="profit_loss_by_flock",
                order_direction="DESC",
                limit=100,
            )

        # --- Priority 10: Simple aggregate metrics ---
        # U: Time-series / which-days questions are handled above by
        # U: _daily_metric_extremes_plan. Keep this flag only to prevent any
        # U: remaining aggregate fall-through for unsupported phrasing.
        is_time_series = self._asks_daily_time_series(query)

        if self._asks_current_birds(query) and not is_time_series:
            return self._current_birds_plan_llm(flock_id=context_flock_id if not self._asks_all_scope(query, history) else None)

        if self._asks_sales_total(query):
            return self._sales_total_plan(flock_id=context_flock_id if not self._asks_all_scope(query, history) else None)

        if self._asks_purchases_total(query):
            return self._purchases_total_plan(flock_id=context_flock_id if not self._asks_all_scope(query, history) else None)

        if self._asks_mortality(query) and not is_time_series:
            return self._mortality_total_plan(flock_id=context_flock_id if not self._asks_all_scope(query, history) else None)

        if self._asks_feed_total(query) and not is_time_series:
            return self._feed_total_plan(flock_id=context_flock_id if not self._asks_all_scope(query, history) else None)

        return None

    def _is_generic_flock_followup(self, query: str) -> bool:
        normalized = query.strip("? .!").lower()
        # Exclude queries that have specific metric/topic keywords, because those should go to their dedicated plans.
        # U: "flock"/"flocks"/"batch"/"batches" are also excluded: if the query explicitly names the entity
        # U: (e.g. "show all flocks", "list all my flocks"), it must route to the flock-list plan,
        # U: NOT inherit the previous topic (e.g. mortality) via the generic follow-up chain.
        if re.search(
            r"\b(?:daily|feed|fcr|weight|mortality|died|dead|death|sale|sales|purchase|purchases|breed|species|farm|farms|flock|flocks|batch|batches|performance|doing|improve|advice)\b",
            normalized,
        ):
            return False

        # Match phrases like:
        # "and for all of them", "for all of them", "what about others", "and others", "and for others", "and for all", "all of them", "and for other ones"
        # Must contain at least one pronoun/scope word: all, other, others, rest, remaining, them
        has_followup_pronoun = bool(
            re.search(r"\b(?:all|other|others|rest|remaining|them)\b", normalized)
        )
        # Must have a preposition/conjunction, or be extremely short (1-3 words)
        has_preposition = bool(
            re.search(r"\b(?:and|for|what|about|with|how)\b", normalized)
        )
        return has_followup_pronoun and (has_preposition or len(normalized.split()) <= 3)

    def _generic_flock_followup_plan(
        self,
        query: str,
        *,
        history: list[dict] | None,
        context_flock_id: int | None,
    ) -> SQLPlan | None:
        history_metric = self._last_history_metric(history)
        if not history_metric:
            return None

        is_all = bool(re.search(r"\ball\b", query))
        is_other = bool(re.search(r"\b(?:other|others|rest|remaining)\b", query))

        # 1. Breed-related
        if history_metric in {"flock_breed", "flock_breeds_by_flock", "most_used_breed"}:
            if is_other and context_flock_id:
                return self._all_flock_breeds_plan(exclude_flock_id=context_flock_id)
            return self._all_flock_breeds_plan()

        # 2. FCR
        if history_metric in {"average_fcr"}:
            return self._avg_fcr_plan(flock_id=None)

        # 3. Weight
        if history_metric in {"average_weight"}:
            return self._avg_weight_plan(flock_id=None)

        # 4. Sales
        if history_metric in {"total_sales"}:
            return self._sales_total_plan(flock_id=None)

        # 5. Purchases
        if history_metric in {"total_purchases"}:
            return self._purchases_total_plan(flock_id=None)

        # 6. Mortality
        if history_metric in {"mortality"}:
            return self._mortality_total_plan(flock_id=None)

        # 7. Feed consumed
        if history_metric in {"feed_consumed"}:
            return self._feed_total_plan(flock_id=None)

        # 8. Current birds
        if history_metric in {"current_birds"}:
            return self._current_birds_plan_llm(flock_id=None)

        # 9. Profit / Loss
        if history_metric in {"profit_by_flock", "profit_for_flock", "profit_loss_by_flock"}:
            return self._profit_ranking_plan(
                metric="profit_loss_by_flock",
                order_direction="DESC",
                limit=100,
            )

        return None

    def _is_compound_query(self, query: str) -> bool:
        # A query is compound if it asks for multiple distinct metric categories:
        # Categories:
        # 1. sales / revenue
        # 2. purchases / expenses
        # 3. fcr / average fcr
        # 4. weight / average bird weight
        # 5. mortality / deaths
        # 6. feed / feed consumed
        # 7. breed / species

        normalized = query.lower()

        has_sales = bool(re.search(r"\b(?:sale|sales|revenue|income|sold|earning|earnings|lifting|liftings)\b", normalized))
        has_purchase = bool(re.search(r"\b(?:purchase|purchases|expense|expenses|spent|spend|spending|expenditure|feed cost|labour|labor|equipment)\b", normalized))
        has_fcr = bool(re.search(r"\b(?:fcr|feed\s+conversion|conversion\s+ratio)\b", normalized))
        has_weight = bool(re.search(r"\b(?:weight|weights|body\s+weight|bird\s+weight|avg\s+weight|average\s+weight)\b", normalized))
        has_mortality = bool(re.search(r"\b(?:mortality|mortalities|death|deaths|dead|died)\b", normalized))
        has_feed = bool(re.search(r"\bfeed\b", normalized) and not re.search(r"\b(?:fcr|feed cost|feed\s+conversion)\b", normalized))
        has_breed = bool(re.search(r"\b(?:breed|species)\b", normalized))

        categories = 0
        if has_sales:
            categories += 1
        if has_purchase:
            categories += 1
        if has_fcr:
            categories += 1
        if has_weight:
            categories += 1
        if has_mortality:
            categories += 1
        if has_feed:
            categories += 1
        if has_breed:
            categories += 1

        # Exception: Map jumbled sales-and-purchases queries directly to _account_summary_plan
        # (metric "farm_record_summary"), which naturally returns both.
        if categories == 2 and has_sales and has_purchase:
            return False

        return categories >= 2

    def _asks_current_workspace(self, query: str) -> bool:
        has_action = bool(re.search(r"\b(?:which|what|show|tell|give|only|just)\b", query))
        has_current = bool(re.search(r"\b(?:current|active|selected)\b", query))
        has_entity = bool(re.search(r"\b(?:farm|flock|batch|one|workspace)\b", query))
        if has_current and (has_entity or "only" in query or "just" in query) and (has_action or "workspace" in query):
            has_metric = bool(re.search(r"\b(?:data|record|records|performance|fcr|weight|feed|mortality|sales|purchase|profit|loss)\b", query))
            if has_metric and "workspace" not in query:
                return False
            return True
        return False

    def _asks_one_flock_details(self, query: str) -> bool:
        if re.search(r"\b(?:all|every|each)\s+(?:the\s+)?(?:flocks|farms|batches)\b", query):
            return False
        # Pronoun 'it'/'its'/'that'/'this' + data/details = single flock report
        has_detail_word = bool(
            re.search(
                r"\b(?:detail|details|everything|data|all data|all its data|its data|every data|all info|all about|what data|what all data)\b",
                query,
            )
        )
        has_flock_ref = bool(
            re.search(r"\b(?:it|its|that|this|flock|batch|current|active|selected)\b", query)
        )
        has_metric = bool(
            re.search(
                r"\b(?:daily|feed|fcr|weight|mortality|died|dead|death|sale|sales|purchase|purchases|breed|species)\b",
                query,
            )
        )
        return has_detail_word and has_flock_ref and not has_metric

    def _asks_daily_data(self, query: str) -> bool:
        return "daily data" in query or re.search(r"\bdaily\b", query)

    def _asks_flock_breed(self, query: str, broad: bool = False) -> bool:
        """Detect breed questions. broad=True returns True even without a specific flock reference."""
        has_breed = bool(re.search(r"\b(?:breed|species)\b", query))
        if broad:
            return has_breed
        return bool(
            has_breed
            and re.search(r"\b(?:flock|batch|current|active|selected|first|second|third|it|that|this)\b", query)
        )

    def _asks_all_flock_breeds(self, query: str, history: list[dict] | None) -> bool:
        has_breed = bool(re.search(r"\b(?:breed|species)\b", query))
        has_collection = bool(
            re.search(r"\b(?:all|every|each|list)\b", query)
            and re.search(r"\b(?:flocks?|batches?)\b", query)
        )
        # 'which breed is for which flock' or 'breed in all flocks'
        has_breed_for_flock_phrasing = bool(
            re.search(r"\b(?:which\s+breed\s+is\s+for\s+which\s+flock|breed\s+in\s+all\s+(?:the\s+)?flocks)\b", query)
        )
        # Do NOT capture 'most used breed' / 'top breed' / 'popular breed'
        has_most_used = bool(
            re.search(r"\b(?:most\s+used|most\s+common|commonest|popular|primary|frequent)\b", query)
        )
        if has_breed and (has_collection or has_breed_for_flock_phrasing) and not has_most_used:
            return True
        # Follow-up: 'specify properly which breed for which flock'
        history_metric = self._last_history_metric(history)
        followup_to_breed = history_metric in {"most_used_breed", "flock_breeds_by_flock", "flock_breed"}
        return bool(
            followup_to_breed
            and re.search(r"\b(?:specify|properly|which|which\s+flock|for\s+which\s+flock)\b", query)
            and re.search(r"\b(?:breed|species|flock|batch)\b", query)
        )

    def _asks_other_flock_breeds(self, query: str, history: list[dict] | None) -> bool:
        history_metric = self._last_history_metric(history)
        return bool(
            history_metric in {"flock_breed", "flock_breeds_by_flock", "most_used_breed"}
            and re.search(r"\b(?:other|others|rest|remaining|and\s+for\s+others|what\s+about\s+others)\b", query)
        )

    def _asks_most_used_breed(self, query: str) -> bool:
        """Detect 'most used/common/popular breed' questions.
        NOTE: 'top breed in my flocks' has both 'top' and 'breed', so we must
        ensure it hits this detector, not _asks_all_flock_breeds.
        """
        return bool(
            re.search(r"\b(?:most\s+used|most\s+common|commonest|popular|top|main|primary|frequent)\b", query)
            and re.search(r"\b(?:breed|species)\b", query)
            # Must NOT also have a collection word that would indicate _asks_all_flock_breeds
            and not re.search(r"\b(?:all|every|each|which|list)\s+(?:the\s+)?(?:flocks?|batches?)\b", query)
        )

    def _asks_most_profitable_flock(self, query: str) -> bool:
        return bool(
            re.search(r"\b(?:most|highest|top|best)\b", query)
            and re.search(r"\b(?:profit|profitable|earning|net)\b", query)
            and re.search(r"\b(?:flock|batch)\b", query)
        )

    def _asks_biggest_loss(self, query: str) -> bool:
        return bool(
            re.search(r"\b(?:biggest|buggest|largest|highest|maximum|most|worst)\b", query)
            and re.search(r"\b(?:loss|negative|losing)\b", query)
        )

    def _asks_sales_count_leader(self, query: str) -> bool:
        return bool(
            re.search(r"\b(?:most|highest|top|max|maximum)\b", query)
            and re.search(r"\b(?:number|count)\b", query)
            and re.search(r"\b(?:sales|sale|lifting|liftings)\b", query)
        )

    def _asks_sales_amount_leader(self, query: str, history: list[dict] | None) -> bool:
        if bool(
            re.search(r"\b(?:most|highest|top|max|maximum)\b", query)
            and re.search(r"\b(?:amount|revenue|sales value|sale value|income)\b", query)
        ):
            return True
        if "amount done" in query:
            return True
        if re.search(r"\b(?:most|highest|top|max|maximum)\b", query) and "amount" in query:
            history_text = " ".join(str(item.get("content", "")) for item in (history or [])[-6:])
            return "sale" in normalize_ai_query(history_text)
        return False

    def _asks_profit_loss(self, query: str) -> bool:
        """Detect profit/loss questions broadly."""
        # Standard financial terms
        if re.search(r"\b(?:profit|loss|net|margin)\b", query):
            return True
        # Colloquial: 'am i making money', 'am i losing', 'money or losing'
        if re.search(r"\b(?:making\s+money|losing\s+money|am\s+i\s+losing|money\s+or\s+losing|making\s+or\s+losing)\b", query):
            return True
        return False

    def _asks_improvement_advice(self, query: str) -> bool:
        improvement = bool(
            re.search(
                r"\b(?:improve|improvement|better|advice|advise|suggest|recommend|how\s+can\s+i\s+improve|how\s+to\s+improve|what\s+can\s+i\s+do|what\s+should\s+i\s+do|how\s+to\s+do\s+better|how\s+can\s+i\s+fix)\b",
                query,
            )
        )
        diagnostic = bool(
            re.search(
                r"\b(?:went\s+wrong|what\s+went\s+wrong|what\s+are\s+the\s+issues|issue|issues|problem|problems|weak|poor|poorly|performing\s+poorly|bad|mistake|mistakes|fix|correct)\b",
                query,
            )
        )
        domain = bool(
            re.search(
                r"\b(?:record|farm|flock|performance|profit|loss|mortality|fcr|feed|data|records|sales|sale|purchase|purchases|bird|birds)\b",
                query,
            )
        )
        # improvement/advice alone (no domain required for strong advice phrases)
        strong_advice = bool(
            re.search(
                r"\b(?:what\s+can\s+i\s+do|what\s+should\s+i\s+do|what\s+went\s+wrong|what\s+are\s+the\s+issues|performing\s+poorly)\b",
                query,
            )
        )
        return bool(
            strong_advice
            or (improvement and (domain or diagnostic))
            or (diagnostic and domain)
        )

    def _asks_flock_least_data(self, query: str) -> bool:
        has_least = bool(re.search(r"\b(?:least|minimum|lowest|fewest|smallest)\b", query))
        has_data = bool(re.search(r"\b(?:data|records|information|rows|details)\b", query))
        has_flock = bool(re.search(r"\b(?:flock|flocks|batch|batches)\b", query))
        return has_least and has_data and has_flock

    def _asks_farm_least_data(self, query: str) -> bool:
        has_least = bool(re.search(r"\b(?:least|minimum|lowest|fewest|smallest)\b", query))
        has_data = bool(re.search(r"\b(?:data|records|information|rows|details)\b", query))
        has_farm = bool(re.search(r"\b(?:farm|farms)\b", query))
        return has_least and has_data and has_farm

    def _asks_flock_least_data_comparison(self, query: str) -> bool:
        has_least = bool(re.search(r"\b(?:least|minimum|lowest|fewest|smallest)\b", query))
        has_data = bool(re.search(r"\b(?:data|records|information|rows|details)\b", query))
        has_this_flock = bool(re.search(r"\b(?:this|that|it|flock)\b", query))
        has_all_farms = bool(re.search(r"\b(?:all|every|other|compared|farms)\b", query))
        return has_least and has_data and has_this_flock and has_all_farms

    def _asks_farm_least_data_comparison(self, query: str) -> bool:
        has_least = bool(re.search(r"\b(?:least|minimum|lowest|fewest|smallest)\b", query))
        has_data = bool(re.search(r"\b(?:data|records|information|rows|details)\b", query))
        has_this_farm = bool(re.search(r"\b(?:this|that|it|farm)\b", query))
        has_all = bool(re.search(r"\b(?:all|every|other|compared)\b", query))
        return has_least and has_data and has_this_farm and has_all

    def _asks_single_farm_query(self, query: str) -> bool:
        if re.search(r"\bfarms\b", query):
            return False
        has_disqualifier = bool(
            re.search(
                r"\b(?:performance|performing|health|healthy|status|stats|statistics|doing|progress|progressing|fcr|weight|weights|body\s+weight|bird\s+weight|avg\s+weight|average\s+weight|feed|mortality|mortalities|death|deaths|dead|died|sales|sale|revenue|income|sold|earning|earnings|lifting|liftings|purchase|purchases|expense|expenses|spent|spend|spending|expenditure|cost|costs|profit|loss|net|issue|issues|problem|problems|breed|breed_name|species|improve|what\s+are\s+the|hatch|hatch_date|starting_birds|actual_birds|birds|chick|chicks|daily|record|records)\b",
                query,
            )
        )
        if has_disqualifier:
            return False
        has_show = bool(re.search(r"\b(?:show|give|tell|display|details|info|information|about|my|current|active|selected)\b", query))
        has_farm = bool(re.search(r"\bfarm\b", query))
        return has_show and has_farm

    def _asks_single_flock_query(self, query: str) -> bool:
        if re.search(r"\b(?:flocks|batches)\b", query):
            return False
        has_disqualifier = bool(
            re.search(
                r"\b(?:performance|performing|health|healthy|status|stats|statistics|doing|progress|progressing|fcr|weight|weights|body\s+weight|bird\s+weight|avg\s+weight|average\s+weight|feed|mortality|mortalities|death|deaths|dead|died|sales|sale|revenue|income|sold|earning|earnings|lifting|liftings|purchase|purchases|expense|expenses|spent|spend|spending|expenditure|cost|costs|profit|loss|net|issue|issues|problem|problems|breed|breed_name|species|improve|what\s+are\s+the|hatch|hatch_date|starting_birds|actual_birds|birds|chick|chicks|daily|record|records)\b",
                query,
            )
        )
        if has_disqualifier:
            return False
        has_show = bool(re.search(r"\b(?:show|give|tell|display|details|info|information|about|my|current|active|selected)\b", query))
        has_flock = bool(re.search(r"\b(?:flock|batch)\b", query))
        return has_show and has_flock

    def _asks_all_scope(self, query: str, history: list[dict] | None = None) -> bool:
        if history:
            pattern = r"\b(?:all|every|each|list|overall|account|best|worst|compare|comparison|ranking|middle|most|least|highest|lowest|top|bottom|better|worse)\b"
        else:
            pattern = r"\b(?:all|every|each|list|total|overall|account|best|worst|compare|comparison|ranking|middle|most|least|highest|lowest|top|bottom|better|worse)\b"
        return bool(re.search(pattern, query))

    def _is_comparative_query(self, question: str) -> bool:
        query = normalize_ai_query(question)
        return bool(
            re.search(
                r"\b(?:best|worst|compare|comparison|ranking|middle|most|least|highest|lowest|top|bottom|better|worse)\b",
                query,
            )
        )

    # U: NEW detector methods — cover all high-frequency farmer question types
    # U: so they never reach the LLM when a safe plan already exists.

    def _asks_performance(self, query: str) -> bool:
        """Detect performance/health/stats questions that are NOT improvement advice."""
        has_performance = bool(
            re.search(
                r"\b(?:performance|performing|health|healthy|status|stats|statistics|doing|progress|progressing)\b",
                query,
            )
            or re.search(
                r"\bhow\s+(?:are|is)\s+(?:my|the|this|that|it)\b",
                query,
            )
        )
        has_farm_entity = bool(
            re.search(r"\b(?:farm|flock|flocks?|batch|batches?|birds?|chickens?|it|this|that)\b", query)
        )
        # Exclude improvement-advice questions (those have their own plan)
        has_advice = bool(
            re.search(
                r"\b(?:improve|advice|advise|suggest|recommend|better|fix|issue|problem|wrong|poorly|what\s+to\s+do|how\s+to\s+do)\b",
                query,
            )
        )
        return has_performance and has_farm_entity and not has_advice

    def _performance_extreme_kind(self, query: str) -> str | None:
        has_flock = bool(re.search(r"\b(?:flock|flocks|batch|batches)\b", query))
        has_performance = bool(
            re.search(
                r"\b(?:performance|performing|performer|performers|doing|progress|progressing|health|healthy|status|stats|statistics)\b",
                query,
            )
        )
        if not has_flock or not has_performance:
            return None
        # U: Multi-part comparison questions need the full performance table so
        # U: the user can see best/worst/middle together. Single best/worst
        # U: questions use the exact SQL ranking plan below.
        has_best = bool(re.search(r"\b(?:best|top|highest|most)\b", query))
        has_worst = bool(re.search(r"\b(?:worst|poorest|lowest|least|bottom|bad|weakest)\b", query))
        if (has_best and has_worst) or re.search(r"\b(?:middle|mid|zone|compare|comparison|ranking)\b", query):
            return None
        if re.search(r"\b(?:worst|poorest|lowest|least|bottom|bad|weakest)\b", query):
            return "worst"
        if re.search(r"\b(?:best|top|highest|most)\b", query):
            return "best"
        return None

    def _asks_account_summary(self, query: str) -> bool:
        """Detect broad account summary questions."""
        # Do not capture if the question is specifically about daily data
        # e.g. "i meant daily data and everything" should route to daily_data, not summary.
        if re.search(r"\bdaily\s+data\b", query):
            return False
        summary_phrases = (
            "summary", "overview", "my data", "all data", "my records",
            "all records", "everything", "what do i have", "what all i have",
            "total things", "show my stuff", "all my data", "total data",
            "full data", "complete data", "all details", "all information",
            "my information", "all things", "all stuff", "my stuff",
            "my details", "all my info", "my info", "my all things",
            "i have in my account",
        )
        if any(phrase in query for phrase in summary_phrases):
            return True

        has_sales = bool(re.search(r"\b(?:sale|sales|revenue|income|sold|earning|earnings|lifting|liftings)\b", query))
        has_purchase = bool(re.search(r"\b(?:purchase|purchases|expense|expenses|spent|spend|spending|expenditure|feed\s+cost|labour|labor|equipment|cost|costs)\b", query))
        if has_sales and has_purchase:
            return True

        return bool(
            re.search(
                r"\b(?:show|give|tell|display|list)\s+(?:me\s+)?(?:my\s+|our\s+)?(?:all|complete|full)\s+(?:my\s+|our\s+)?(?:data|records|details|information|stuff|things)\b",
                query,
            )
        )

    def _asks_farm_list(self, query: str, entity_context: str = "") -> bool:
        """Detect 'list/show farms' without a specific farm reference."""
        if self._is_comparative_query(query):
            return False
        
        has_farm = bool(re.search(r"\bfarms?\b", query))
        has_farms_plural = bool(re.search(r"\bfarms\b", query))
        
        # If singular "farm" is requested and we have a context farm, don't trigger the list.
        if has_farm and not has_farms_plural:
            context_farm_id = self._context_farm_id(entity_context)
            if context_farm_id is not None:
                return False

        has_list_word = bool(
            re.search(r"\b(?:list|show|display|give|tell|all|every|my)\b", query)
        )
        has_flock = bool(re.search(r"\b(?:flocks?|batches?)\b", query))
        has_disqualifier = bool(
            re.search(
                r"\b(?:performance|performing|health|healthy|status|stats|statistics|doing|progress|progressing|fcr|weight|weights|body\s+weight|bird\s+weight|avg\s+weight|average\s+weight|feed|mortality|mortalities|death|deaths|dead|died|sales|sale|revenue|income|sold|earning|earnings|lifting|liftings|purchase|purchases|expense|expenses|spent|spend|spending|expenditure|cost|costs|profit|loss|net|issue|issues|problem|problems|breed|breed_name|species|improve|what\s+are\s+the|hatch|hatch_date|starting_birds|actual_birds|birds|chick|chicks)\b",
                query,
            )
        )
        if has_disqualifier:
            return False
        if has_list_word and has_farm and not has_flock:
            return True
        # "show farms" / "my farms"
        return bool(re.search(r"\b(?:my\s+farms?|show\s+farms?|list\s+farms?)\b", query))

    def _asks_flock_list(self, query: str, entity_context: str = "") -> bool:
        """Detect 'list/show flocks' questions."""
        if self._is_comparative_query(query):
            return False
        
        has_flock = bool(re.search(r"\b(?:flocks?|batches?)\b", query))
        has_flocks_plural = bool(re.search(r"\b(?:flocks|batches)\b", query))
        
        # If singular "flock" is requested and we have a context flock, don't trigger the list.
        if has_flock and not has_flocks_plural:
            context_flock_id = self._context_flock_id(entity_context)
            if context_flock_id is not None:
                return False

        has_list_word = bool(
            re.search(r"\b(?:list|show|display|give|tell|all|every|my)\b", query)
        )
        has_count = bool(re.search(r"\b(?:how many|count|number of|total)\b", query))
        has_disqualifier = bool(
            re.search(
                r"\b(?:performance|performing|health|healthy|status|stats|statistics|doing|progress|progressing|fcr|weight|weights|body\s+weight|bird\s+weight|avg\s+weight|average\s+weight|feed|mortality|mortalities|death|deaths|dead|died|sales|sale|revenue|income|sold|earning|earnings|lifting|liftings|purchase|purchases|expense|expenses|spent|spend|spending|expenditure|cost|costs|profit|loss|net|issue|issues|problem|problems|breed|breed_name|species|improve|what\s+are\s+the|hatch|hatch_date|starting_birds|actual_birds|birds|chick|chicks)\b",
                query,
            )
        )
        if has_count:
            return False  # handled by _asks_flock_count
        if has_disqualifier:
            return False  # handled by other detectors
        return has_list_word and has_flock

    def _asks_farm_count(self, query: str) -> bool:
        """Detect 'how many farms' questions."""
        return bool(
            re.search(r"\b(?:how many|number of|count|total)\b", query)
            and re.search(r"\bfarms?\b", query)
            and not re.search(r"\b(?:flocks?|batches?)\b", query)
        )

    def _asks_flock_count(self, query: str) -> bool:
        """Detect 'how many flocks' questions (total, not grouped)."""
        # "total flocks in each farm" / "flocks per farm" / "flocks by farm" need
        # the LLM to GROUP BY farm, so we do NOT intercept those here.
        if re.search(r"\b(?:in\s+each|per\s+farm|by\s+farm|each\s+farm|for\s+each)\b", query):
            return False
        # Exclude questions about birds/chickens (handled by current_birds)
        if re.search(r"\b(?:birds?|chickens?|alive|remaining|left|current)\b", query):
            return False
        # Exclude sales count leader questions ('most number of sales')
        if re.search(r"\b(?:sales?|sale)\b", query):
            return False
        return bool(
            re.search(r"\b(?:how many|number of|count|total)\b", query)
            and re.search(r"\b(?:flocks?|batches?)\b", query)
        )

    def _asks_sales_total(self, query: str) -> bool:
        """Detect 'total sales / revenue / income' questions."""
        has_sales = bool(
            re.search(r"\b(?:sale|sales|sails|revenue|income|sold|earning|earnings|lifting|liftings)\b", query)
        )
        # Exclude superlative (most/highest sales) — handled by sales_amount_leader
        has_superlative = bool(re.search(r"\b(?:most|highest|top|max|maximum)\b", query))
        # Exclude profit questions — profit/loss comes first in routing chain,
        # but guard here too in case of direct detector calls from tests.
        has_profit = bool(re.search(r"\b(?:profit|loss|net|margin)\b", query))
        return has_sales and not has_superlative and not has_profit

    def _asks_purchases_total(self, query: str) -> bool:
        """Detect 'total purchases / expenses / spending' questions."""
        has_purchase = bool(
            re.search(
                r"\b(?:purchase|purchases|expense|expenses|spent|spend|spending|expenditure|medicine|vaccines?|vaccination|feed cost|labour|labor|equipment)\b",
                query,
            )
        )
        has_profit = bool(re.search(r"\b(?:profit|loss|net|margin)\b", query))
        return has_purchase and not has_profit

    def _asks_mortality(self, query: str) -> bool:
        """Detect mortality / death / birds died questions."""
        return bool(
            re.search(
                r"\b(?:mortality|mortalities|mortallity|death|deaths|dead|died|birds?\s+died|birds?\s+dead|dead\s+birds?)\b",
                query,
            )
        )

    def _asks_daily_time_series(self, query: str) -> bool:
        """Detect time-series 'which days / when / what dates / on which day' questions
        about daily metrics (mortality, feed, weight, FCR). These must NOT be routed
        to aggregate (SUM/AVG) deterministic plans — they need per-row date results."""
        has_time_ref = bool(
            re.search(
                r"\b(?:which\s+days?|what\s+days?|days?\s+with|dates?\s+with|when|what\s+dates?|on\s+which\s+dates?|on\s+which\s+days?|which\s+dates?|what\s+date|in\s+which\s+days?)\b",
                query,
            )
            or bool(re.search(r"\b(?:lowest|highest|minimum|maximum|min|max)\b", query))
        )
        has_daily_metric = bool(
            re.search(
                r"\b(?:mortality|mortalities|mortallity|death|deaths|dead|die|died|birds?\s+(?:die|died)|birds?\s+dead|dead\s+birds?|feed|feeed|fcr|feed\s+conversion|weight|weights|bird\s+weight|average\s+weight|avg\s+weight|current\s+birds?|birds?\s+(?:left|remaining|alive|current|now)|bird\s+count)\b",
                query,
            )
        )
        return has_time_ref and has_daily_metric

    def _daily_time_series_metric(self, query: str) -> str | None:
        # U: Order matters: FCR contains the word "feed" conceptually, so detect it first.
        if re.search(r"\b(?:fcr|feed\s+conversion|conversion\s+ratio|feed\s+conversion\s+ratio)\b", query):
            return "fcr"
        if re.search(r"\b(?:avg\s+weight|average\s+weight|bird\s+weight|body\s+weight|weight|weights)\b", query):
            return "average_bird_weight"
        if re.search(r"\b(?:current\s+birds?|birds?\s+(?:left|remaining|alive|current|now)|bird\s+count)\b", query):
            return "birds_current"
        if re.search(r"\b(?:feed|feeed|feed\s+consumed|feed\s+intake)\b", query):
            return "feed_consumed_kg"
        if re.search(r"\b(?:mortality|mortalities|mortallity|death|deaths|dead|die|died|birds?\s+(?:die|died)|birds?\s+dead|dead\s+birds?)\b", query):
            return "birds_died"
        return None

    def _daily_extreme_direction(self, query: str) -> str:
        has_low = bool(re.search(r"\b(?:lowest|least|minimum|min|smallest|low|best)\b", query))
        has_high = bool(re.search(r"\b(?:highest|maximum|max|most|biggest|largest|high|worst)\b", query))
        if has_low and has_high:
            return "both"
        if has_low:
            return "lowest"
        return "highest" if has_high else "highest"

    def _asks_all_daily_scope(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:all|every|each|overall|account|all\s+farms|all\s+flocks|all\s+batches)\b",
                query,
            )
        )

    def _asks_feed_total(self, query: str) -> bool:
        """Detect 'total/how much feed consumed' questions."""
        has_feed = bool(re.search(r"\b(?:feed|feeed)\b", query))
        has_fcr = bool(re.search(r"\b(?:fcr|conversion|ratio)\b", query))
        has_performance = bool(
            re.search(r"\b(?:performance|performing|health|stats|progress)\b", query)
        )
        return has_feed and not has_fcr and not has_performance

    def _asks_avg_fcr(self, query: str) -> bool:
        """Detect FCR / feed conversion ratio questions."""
        return bool(
            re.search(r"\b(?:fcr|feed\s+conversion|conversion\s+ratio|feed\s+conversion\s+ratio)\b", query)
        )

    def _asks_avg_weight(self, query: str) -> bool:
        """Detect average bird weight questions."""
        has_weight = bool(re.search(r"\b(?:weight|weights|body\s+weight|bird\s+weight|avg\s+weight|average\s+weight)\b", query))
        # Performance/health questions take priority over weight.
        has_performance = bool(
            re.search(r"\b(?:performance|performing|health|stats|progress|how\s+(?:are|is))\b", query)
            and re.search(r"\b(?:farm|flock|flocks?|batch|batches?|birds?)\b", query)
        )
        return has_weight and not has_performance

    def _asks_current_birds(self, query: str) -> bool:
        """Detect 'current birds / how many birds alive' questions."""
        has_birds = bool(
            re.search(
                r"\b(?:current\s+(?:birds?|chickens?)|(?:birds?|chickens?)\s+alive|(?:birds?|chickens?)\s+left|(?:birds?|chickens?)\s+remaining|(?:birds?|chickens?)\s+now|how\s+many\s+(?:birds?|chickens?)|bird\s+count|live\s+(?:birds?|chickens?)|alive\s+(?:birds?|chickens?)|(?:birds?|chickens?)\s+do\s+i\s+have)\b",
                query,
            )
        )
        has_mortality = bool(re.search(r"\b(?:mortality|died|dead|death)\b", query))
        return has_birds and not has_mortality

    def _last_history_metric(self, history: list[dict] | None) -> str:
        for item in reversed((history or [])[-16:]):
            metric = item.get("metric")
            if metric:
                return str(metric)
        return ""

    def _active_context_ids(self, entity_context: str) -> tuple[int | None, int | None]:
        active_farm_id = self._line_int(
            entity_context, "Active app farm context", "farm_id"
        )
        active_flock_id = self._line_int(
            entity_context, "Active app flock context", "flock_id"
        )
        flock_farm_id = self._line_int(
            entity_context, "Active app flock context", "farm_id"
        )
        return active_farm_id or flock_farm_id, active_flock_id

    def _context_flock_id(self, entity_context: str) -> int | None:
        return (
            self._line_int(entity_context, "Resolved flock mention", "flock_id")
            or self._line_int(entity_context, "Last referenced flock from recent chat", "flock_id")
            or self._line_int(entity_context, "Active app flock context", "flock_id")
        )

    def _context_farm_id(self, entity_context: str) -> int | None:
        return (
            self._line_int(entity_context, "Resolved flock mention", "farm_id")
            or self._line_int(entity_context, "Resolved farm mention", "farm_id")
            or self._line_int(entity_context, "Last referenced flock from recent chat", "farm_id")
            or self._line_int(entity_context, "Last referenced farm from recent chat", "farm_id")
            or self._line_int(entity_context, "Active app flock context", "farm_id")
            or self._line_int(entity_context, "Active app farm context", "farm_id")
        )

    def _line_int(self, text: str, prefix: str, key: str) -> int | None:
        value = self._line_value(text, prefix, key)
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def _line_value(self, text: str, prefix: str, key: str) -> str | None:
        match = re.search(
            rf"{re.escape(prefix)}:\s*[^\n]*?\b{re.escape(key)}=([^,.\n]+)",
            text,
        )
        return match.group(1).strip() if match else None

    def _plan(
        self,
        sql: str,
        params: list,
        *,
        metric: str,
        result_type: str = "summary",
    ) -> SQLPlan:
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=params,
            metric=metric,
            result_type=result_type,
        )

    def _flock_least_data_plan(self) -> SQLPlan:
        sql = """
            SELECT base.flock_id, base.flock_name, base.farm_name, COALESCE(daily.daily_rows, 0) AS daily_rows
            FROM (
              SELECT flock_id, flock_name, farm_name
              FROM ai_farm_flock_data_view
              WHERE owner_id = %s AND flock_id IS NOT NULL
              GROUP BY flock_id, flock_name, farm_name
            ) base
            LEFT JOIN (
              SELECT flock_id, COUNT(daily_data_id) AS daily_rows
              FROM ai_dailydata_data_view
              WHERE owner_id = %s
              GROUP BY flock_id
            ) daily ON daily.flock_id = base.flock_id
            ORDER BY daily_rows ASC, base.flock_id ASC
        """
        return self._plan(
            sql,
            [self.user.id, self.user.id],
            metric="flock_least_data",
            result_type="table",
        )

    def _farm_least_data_plan(self) -> SQLPlan:
        sql = """
            SELECT base.farm_id, base.farm_name, COALESCE(daily.daily_rows, 0) AS daily_rows
            FROM (
              SELECT farm_id, farm_name
              FROM ai_farm_flock_data_view
              WHERE owner_id = %s AND farm_id IS NOT NULL
              GROUP BY farm_id, farm_name
            ) base
            LEFT JOIN (
              SELECT farm_id, COUNT(daily_data_id) AS daily_rows
              FROM ai_dailydata_data_view
              WHERE owner_id = %s
              GROUP BY farm_id
            ) daily ON daily.farm_id = base.farm_id
            ORDER BY daily_rows ASC, base.farm_id ASC
        """
        return self._plan(
            sql,
            [self.user.id, self.user.id],
            metric="farm_least_data",
            result_type="table",
        )

    def _current_workspace_plan(
        self,
        *,
        active_flock_id: int | None = None,
        active_farm_id: int | None = None,
    ) -> SQLPlan:
        if active_flock_id:
            return self._plan(
                """
                SELECT farm_id, farm_name AS current_farm, flock_id,
                       flock_name AS current_flock, hatch_date, flock_size,
                       actual_birds, breed_name
                FROM ai_farm_flock_data_view
                WHERE owner_id = %s AND flock_id = %s
                LIMIT 1
                """,
                [self.user.id, active_flock_id],
                metric="current_workspace",
            )
        return self._plan(
            """
            SELECT farm_id, farm_name AS current_farm,
                   COUNT(DISTINCT flock_id) AS flock_count
            FROM ai_farm_flock_data_view
            WHERE owner_id = %s AND farm_id = %s
            GROUP BY farm_id, farm_name
            LIMIT 1
            """,
            [self.user.id, active_farm_id],
            metric="current_workspace",
        )

    def _daily_data_for_flock_plan(self, flock_id: int) -> SQLPlan:
        return self._plan(
            """
            SELECT record_date, flock_id, flock_name, birds_died, total_mort,
                   birds_current, feed_consumed_kg, total_feed,
                   average_bird_weight, fcr, remarks, daily_data_status
            FROM ai_dailydata_data_view
            WHERE owner_id = %s AND flock_id = %s AND daily_data_id IS NOT NULL
            ORDER BY record_date DESC
            LIMIT 100
            """,
            [self.user.id, flock_id],
            metric="daily_data_by_flock",
            result_type="table",
        )

    def _flock_breed_plan(self, flock_id: int) -> SQLPlan:
        return self._plan(
            """
            SELECT flock_id, flock_name, farm_name, breed_name
            FROM ai_farm_flock_data_view
            WHERE owner_id = %s AND flock_id = %s
            LIMIT 1
            """,
            [self.user.id, flock_id],
            metric="flock_breed",
        )

    def _all_flock_breeds_plan(self, exclude_flock_id: int | None = None) -> SQLPlan:
        exclude_sql = "AND flock_id != %s" if exclude_flock_id else ""
        params = [self.user.id]
        if exclude_flock_id:
            params.append(exclude_flock_id)
        return self._plan(
            f"""
            SELECT flock_id, flock_name, farm_name, COALESCE(NULLIF(breed_name, ''), 'Not available') AS breed_name
            FROM ai_farm_flock_data_view
            WHERE owner_id = %s
              AND flock_id IS NOT NULL
              {exclude_sql}
            GROUP BY flock_id, flock_name, farm_name, breed_name
            ORDER BY farm_name, flock_name
            LIMIT 100
            """,
            params,
            metric="flock_breeds_by_flock",
            result_type="table",
        )

    def _most_used_breed_plan(self) -> SQLPlan:
        return self._plan(
            """
            SELECT breed_name, COUNT(DISTINCT flock_id) AS flock_count
            FROM ai_farm_flock_data_view
            WHERE owner_id = %s
              AND flock_id IS NOT NULL
              AND breed_name IS NOT NULL
              AND breed_name != ''
            GROUP BY breed_name
            ORDER BY flock_count DESC, breed_name
            LIMIT 10
            """,
            [self.user.id],
            metric="most_used_breed",
            result_type="table",
        )

    def _profit_for_flock_plan(self, flock_id: int) -> SQLPlan:
        return self._plan(
            """
            SELECT base.flock_id, base.flock_name, base.farm_name,
                   COALESCE(sales.total_sales, 0) AS total_sales,
                   COALESCE(purchases.total_purchases, 0) AS total_purchases,
                   COALESCE(base.flock_cost, 0) AS flock_cost,
                   COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS result,
                   CASE
                       WHEN COALESCE(purchases.total_purchases, 0) = 0 AND COALESCE(base.flock_cost, 0) = 0
                       THEN 'Purchase and flock-cost records are zero or missing, so profit may be incomplete.'
                       ELSE ''
                   END AS data_note
            FROM (
                SELECT flock_id, flock_name, farm_name, MAX(flock_cost) AS flock_cost
                FROM ai_farm_flock_data_view
                WHERE owner_id = %s AND flock_id = %s
                GROUP BY flock_id, flock_name, farm_name
            ) base
            LEFT JOIN (
                SELECT flock_id, SUM(sale_amount) AS total_sales
                FROM ai_sale_data_view
                WHERE owner_id = %s AND flock_id = %s
                GROUP BY flock_id
            ) sales ON sales.flock_id = base.flock_id
            LEFT JOIN (
                SELECT flock_id, SUM(purchase_amount) AS total_purchases
                FROM ai_purchase_data_view
                WHERE owner_id = %s AND flock_id = %s
                GROUP BY flock_id
            ) purchases ON purchases.flock_id = base.flock_id
            """,
            [self.user.id, flock_id, self.user.id, flock_id, self.user.id, flock_id],
            metric="profit_for_flock",
            result_type="money",
        )

    def _profit_ranking_plan(
        self,
        *,
        metric: str,
        order_direction: str,
        limit: int,
        losses_only: bool = False,
    ) -> SQLPlan:
        direction = "ASC" if order_direction.upper() == "ASC" else "DESC"
        where_loss = "WHERE ranked.result < 0" if losses_only else ""
        order_prefix = (
            "ranked.data_ready DESC, "
            if metric == "most_profitable_flock" and not losses_only
            else ""
        )
        return self._plan(
            f"""
            SELECT ranked.flock_id, ranked.flock_name, ranked.farm_name,
                   ranked.total_sales, ranked.total_purchases,
                   ranked.flock_cost, ranked.result, ranked.data_note,
                   ranked.data_ready
            FROM (
                SELECT base.flock_id, base.flock_name, base.farm_name,
                       COALESCE(sales.total_sales, 0) AS total_sales,
                       COALESCE(purchases.total_purchases, 0) AS total_purchases,
                       COALESCE(base.flock_cost, 0) AS flock_cost,
                       COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS result,
                       CASE
                           WHEN COALESCE(sales.total_sales, 0) > 0
                                AND (COALESCE(purchases.total_purchases, 0) > 0 OR COALESCE(base.flock_cost, 0) > 0)
                           THEN 1
                           ELSE 0
                       END AS data_ready,
                       CASE
                           WHEN COALESCE(sales.total_sales, 0) = 0
                           THEN 'Sales records are zero or missing, so this profit/loss may be incomplete.'
                           WHEN COALESCE(purchases.total_purchases, 0) = 0 AND COALESCE(base.flock_cost, 0) = 0
                           THEN 'Purchase and flock-cost records are zero or missing, so this profit/loss may be incomplete.'
                           ELSE ''
                       END AS data_note
                FROM (
                    SELECT flock_id, flock_name, farm_name, MAX(flock_cost) AS flock_cost
                    FROM ai_farm_flock_data_view
                    WHERE owner_id = %s AND flock_id IS NOT NULL
                    GROUP BY flock_id, flock_name, farm_name
                ) base
                LEFT JOIN (
                    SELECT flock_id, SUM(sale_amount) AS total_sales
                    FROM ai_sale_data_view
                    WHERE owner_id = %s
                    GROUP BY flock_id
                ) sales ON sales.flock_id = base.flock_id
                LEFT JOIN (
                    SELECT flock_id, SUM(purchase_amount) AS total_purchases
                    FROM ai_purchase_data_view
                    WHERE owner_id = %s
                    GROUP BY flock_id
                ) purchases ON purchases.flock_id = base.flock_id
            ) ranked
            {where_loss}
            ORDER BY {order_prefix}ranked.result {direction}, ranked.flock_name
            LIMIT {int(limit)}
            """,
            [self.user.id, self.user.id, self.user.id],
            metric=metric,
            result_type="table" if limit > 1 else "money",
        )

    def _flock_performance_ranking_plan(
        self,
        *,
        metric: str,
        order_direction: str,
        limit: int,
    ) -> SQLPlan:
        direction = "ASC" if order_direction.upper() == "ASC" else "DESC"
        return self._plan(
            f"""
            SELECT ranked.flock_id, ranked.flock_name, ranked.farm_name,
                   ranked.total_sales, ranked.total_purchases,
                   ranked.flock_cost, ranked.result, ranked.data_ready,
                   ranked.data_note, ranked.total_mortality,
                   ranked.total_feed_consumed, ranked.average_fcr,
                   ranked.average_weight, ranked.current_birds,
                   ranked.latest_daily_date
            FROM (
                SELECT base.flock_id, base.flock_name, base.farm_name,
                       COALESCE(sales.total_sales, 0) AS total_sales,
                       COALESCE(purchases.total_purchases, 0) AS total_purchases,
                       COALESCE(base.flock_cost, 0) AS flock_cost,
                       COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS result,
                       CASE
                           WHEN COALESCE(sales.total_sales, 0) > 0
                                AND (COALESCE(purchases.total_purchases, 0) > 0 OR COALESCE(base.flock_cost, 0) > 0)
                           THEN 1
                           ELSE 0
                       END AS data_ready,
                       CASE
                           WHEN COALESCE(sales.total_sales, 0) = 0
                           THEN 'Sales records are zero or missing, so this ranking may be incomplete.'
                           WHEN COALESCE(purchases.total_purchases, 0) = 0 AND COALESCE(base.flock_cost, 0) = 0
                           THEN 'Purchase and flock-cost records are zero or missing, so this ranking may be incomplete.'
                           ELSE ''
                       END AS data_note,
                       COALESCE(daily.total_mortality, 0) AS total_mortality,
                       COALESCE(daily.total_feed_consumed, 0) AS total_feed_consumed,
                       COALESCE(daily.average_fcr, 0) AS average_fcr,
                       COALESCE(daily.average_weight, 0) AS average_weight,
                       COALESCE(latest.birds_current, 0) AS current_birds,
                       COALESCE(latest.record_date, '') AS latest_daily_date
                FROM (
                    SELECT flock_id, flock_name, farm_name, MAX(flock_cost) AS flock_cost
                    FROM ai_farm_flock_data_view
                    WHERE owner_id = %s AND flock_id IS NOT NULL
                    GROUP BY flock_id, flock_name, farm_name
                ) base
                LEFT JOIN (
                    SELECT flock_id, SUM(sale_amount) AS total_sales
                    FROM ai_sale_data_view
                    WHERE owner_id = %s
                    GROUP BY flock_id
                ) sales ON sales.flock_id = base.flock_id
                LEFT JOIN (
                    SELECT flock_id, SUM(purchase_amount) AS total_purchases
                    FROM ai_purchase_data_view
                    WHERE owner_id = %s
                    GROUP BY flock_id
                ) purchases ON purchases.flock_id = base.flock_id
                LEFT JOIN (
                    SELECT flock_id,
                           SUM(birds_died) AS total_mortality,
                           SUM(feed_consumed_kg) AS total_feed_consumed,
                           AVG(fcr) AS average_fcr,
                           AVG(average_bird_weight) AS average_weight
                    FROM ai_dailydata_data_view
                    WHERE owner_id = %s AND daily_data_id IS NOT NULL
                    GROUP BY flock_id
                ) daily ON daily.flock_id = base.flock_id
                LEFT JOIN (
                    SELECT current_rows.flock_id, current_rows.record_date,
                           current_rows.birds_current
                    FROM ai_dailydata_data_view current_rows
                    WHERE current_rows.owner_id = %s
                      AND current_rows.daily_data_id IS NOT NULL
                      AND current_rows.record_date = (
                          SELECT MAX(compare_rows.record_date)
                          FROM ai_dailydata_data_view compare_rows
                          WHERE compare_rows.owner_id = %s
                            AND compare_rows.flock_id = current_rows.flock_id
                            AND compare_rows.daily_data_id IS NOT NULL
                      )
                ) latest ON latest.flock_id = base.flock_id
            ) ranked
            ORDER BY ranked.data_ready DESC, ranked.result {direction},
                     ranked.total_mortality DESC, ranked.average_fcr DESC,
                     ranked.flock_name
            LIMIT {int(limit)}
            """,
            [
                self.user.id,
                self.user.id,
                self.user.id,
                self.user.id,
                self.user.id,
                self.user.id,
            ],
            metric=metric,
            result_type="summary" if limit == 1 else "table",
        )

    def _daily_metric_extremes_plan(
        self,
        *,
        metric_column: str,
        direction: str,
        flock_id: int | None = None,
    ) -> SQLPlan:
        allowed_columns = {
            "birds_died": "mortality",
            "feed_consumed_kg": "feed consumed",
            "fcr": "FCR",
            "average_bird_weight": "average bird weight",
            "birds_current": "current birds",
        }
        if metric_column not in allowed_columns:
            metric_column = "birds_died"
        clean_direction = direction if direction in {"lowest", "highest", "both"} else "highest"
        scope_sql = "AND flock_id = %s" if flock_id else ""
        main_params = [self.user.id] + ([flock_id] if flock_id else [])
        sub_params = [self.user.id] + ([flock_id] if flock_id else [])
        if clean_direction == "both":
            sql = f"""
                SELECT record_date, flock_id, flock_name, farm_name,
                       CASE
                           WHEN {metric_column} = (
                               SELECT MIN(extreme_low.{metric_column})
                               FROM ai_dailydata_data_view extreme_low
                               WHERE extreme_low.owner_id = %s {scope_sql.replace('flock_id', 'extreme_low.flock_id')}
                                 AND extreme_low.daily_data_id IS NOT NULL
                                 AND extreme_low.{metric_column} IS NOT NULL
                           ) THEN 'lowest'
                           WHEN {metric_column} = (
                               SELECT MAX(extreme_high.{metric_column})
                               FROM ai_dailydata_data_view extreme_high
                               WHERE extreme_high.owner_id = %s {scope_sql.replace('flock_id', 'extreme_high.flock_id')}
                                 AND extreme_high.daily_data_id IS NOT NULL
                                 AND extreme_high.{metric_column} IS NOT NULL
                           ) THEN 'highest'
                           ELSE ''
                       END AS point_type,
                       {metric_column} AS metric_value,
                       birds_died, total_mort, birds_current,
                       feed_consumed_kg, average_bird_weight, fcr
                FROM ai_dailydata_data_view
                WHERE owner_id = %s {scope_sql}
                  AND daily_data_id IS NOT NULL
                  AND {metric_column} IS NOT NULL
                  AND (
                      {metric_column} = (
                          SELECT MIN(extreme_low_where.{metric_column})
                          FROM ai_dailydata_data_view extreme_low_where
                          WHERE extreme_low_where.owner_id = %s {scope_sql.replace('flock_id', 'extreme_low_where.flock_id')}
                            AND extreme_low_where.daily_data_id IS NOT NULL
                            AND extreme_low_where.{metric_column} IS NOT NULL
                      )
                      OR {metric_column} = (
                          SELECT MAX(extreme_high_where.{metric_column})
                          FROM ai_dailydata_data_view extreme_high_where
                          WHERE extreme_high_where.owner_id = %s {scope_sql.replace('flock_id', 'extreme_high_where.flock_id')}
                            AND extreme_high_where.daily_data_id IS NOT NULL
                            AND extreme_high_where.{metric_column} IS NOT NULL
                      )
                  )
                ORDER BY {metric_column} ASC, record_date ASC
                LIMIT 20
            """
            params = [*sub_params, *sub_params, *main_params, *sub_params, *sub_params]
        else:
            aggregate = "MIN" if clean_direction == "lowest" else "MAX"
            order = "ASC" if clean_direction == "lowest" else "DESC"
            sql = f"""
                SELECT record_date, flock_id, flock_name, farm_name,
                       '{clean_direction}' AS point_type,
                       {metric_column} AS metric_value,
                       birds_died, total_mort, birds_current,
                       feed_consumed_kg, average_bird_weight, fcr
                FROM ai_dailydata_data_view
                WHERE owner_id = %s {scope_sql}
                  AND daily_data_id IS NOT NULL
                  AND {metric_column} IS NOT NULL
                  AND {metric_column} = (
                      SELECT {aggregate}(extreme_rows.{metric_column})
                      FROM ai_dailydata_data_view extreme_rows
                      WHERE extreme_rows.owner_id = %s {scope_sql.replace('flock_id', 'extreme_rows.flock_id')}
                        AND extreme_rows.daily_data_id IS NOT NULL
                        AND extreme_rows.{metric_column} IS NOT NULL
                  )
                ORDER BY {metric_column} {order}, record_date ASC
                LIMIT 20
            """
            params = [*main_params, *sub_params]
        return self._plan(
            sql,
            params,
            metric=f"daily_metric_extreme_{metric_column}_{clean_direction}",
            result_type="table",
        )

    def _sales_leader_plan(self, *, metric: str, by: str) -> SQLPlan:
        order = (
            "sale_count DESC, total_sales DESC, flock_name"
            if by == "count"
            else "total_sales DESC, sale_count DESC, flock_name"
        )
        return self._plan(
            f"""
            SELECT flock_id, flock_name, farm_name,
                   COUNT(sale_id) AS sale_count,
                   COALESCE(SUM(sale_amount), 0) AS total_sales
            FROM ai_sale_data_view
            WHERE owner_id = %s AND flock_id IS NOT NULL
            GROUP BY flock_id, flock_name, farm_name
            ORDER BY {order}
            LIMIT 1
            """,
            [self.user.id],
            metric=metric,
            result_type="summary",
        )

    def _improvement_advice_plan(self) -> SQLPlan:
        return self._plan(
            """
            SELECT ranked.flock_id, ranked.flock_name, ranked.farm_name,
                   ranked.total_sales, ranked.total_purchases,
                   ranked.flock_cost, ranked.profit_loss,
                   COALESCE(daily.total_mortality, 0) AS total_mortality,
                   COALESCE(daily.total_feed_consumed, 0) AS total_feed_consumed,
                   COALESCE(daily.average_fcr, 0) AS average_fcr,
                   COALESCE(latest.birds_current, 0) AS current_birds,
                   COALESCE(latest.record_date, '') AS latest_daily_date
            FROM (
                SELECT base.flock_id, base.flock_name, base.farm_name,
                       COALESCE(sales.total_sales, 0) AS total_sales,
                       COALESCE(purchases.total_purchases, 0) AS total_purchases,
                       COALESCE(base.flock_cost, 0) AS flock_cost,
                       COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS profit_loss
                FROM (
                    SELECT flock_id, flock_name, farm_name, MAX(flock_cost) AS flock_cost
                    FROM ai_farm_flock_data_view
                    WHERE owner_id = %s AND flock_id IS NOT NULL
                    GROUP BY flock_id, flock_name, farm_name
                ) base
                LEFT JOIN (
                    SELECT flock_id, SUM(sale_amount) AS total_sales
                    FROM ai_sale_data_view
                    WHERE owner_id = %s
                    GROUP BY flock_id
                ) sales ON sales.flock_id = base.flock_id
                LEFT JOIN (
                    SELECT flock_id, SUM(purchase_amount) AS total_purchases
                    FROM ai_purchase_data_view
                    WHERE owner_id = %s
                    GROUP BY flock_id
                ) purchases ON purchases.flock_id = base.flock_id
            ) ranked
            LEFT JOIN (
                SELECT flock_id, SUM(birds_died) AS total_mortality,
                       SUM(feed_consumed_kg) AS total_feed_consumed,
                       AVG(fcr) AS average_fcr
                FROM ai_dailydata_data_view
                WHERE owner_id = %s AND daily_data_id IS NOT NULL
                GROUP BY flock_id
            ) daily ON daily.flock_id = ranked.flock_id
            LEFT JOIN (
                SELECT current_rows.flock_id, current_rows.record_date, current_rows.birds_current
                FROM ai_dailydata_data_view current_rows
                WHERE current_rows.owner_id = %s
                  AND current_rows.daily_data_id IS NOT NULL
                  AND current_rows.record_date = (
                      SELECT MAX(compare_rows.record_date)
                      FROM ai_dailydata_data_view compare_rows
                      WHERE compare_rows.owner_id = %s
                        AND compare_rows.flock_id = current_rows.flock_id
                        AND compare_rows.daily_data_id IS NOT NULL
                  )
            ) latest ON latest.flock_id = ranked.flock_id
            ORDER BY ranked.profit_loss ASC, daily.total_mortality DESC, daily.average_fcr DESC
            LIMIT 10
            """,
            [
                self.user.id,
                self.user.id,
                self.user.id,
                self.user.id,
                self.user.id,
                self.user.id,
            ],
            metric="improvement_advice",
            result_type="table",
        )

    # U: NEW: all the deterministic plan builder methods added below.
    # U: These guarantee correct SQL for common farmer questions.

    def _all_flocks_performance_plan(self) -> SQLPlan:
        """Performance summary for all farmer's flocks: feed, mortality, weight, FCR, sales, purchases, profit/loss."""
        return self._plan(
            """
            SELECT base.flock_id, base.flock_name, base.farm_name,
                   COALESCE(daily.total_feed_consumed, 0) AS total_feed,
                   COALESCE(daily.total_mortality, 0) AS total_mortality,
                   COALESCE(daily.average_weight, 0) AS avg_weight,
                   COALESCE(daily.average_fcr, 0) AS avg_fcr,
                   COALESCE(sales.total_sales, 0) AS total_sales,
                   COALESCE(purchases.total_purchases, 0) AS total_purchases,
                   COALESCE(base.flock_cost, 0) AS flock_cost,
                   COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS profit_loss,
                   COALESCE(daily.daily_data_status, 0) AS daily_data_status
            FROM (
                SELECT flock_id, flock_name, farm_name, MAX(flock_cost) AS flock_cost
                FROM ai_farm_flock_data_view
                WHERE owner_id = %s AND flock_id IS NOT NULL
                GROUP BY flock_id, flock_name, farm_name
            ) base
            LEFT JOIN (
                SELECT flock_id,
                       SUM(feed_consumed_kg) AS total_feed_consumed,
                       SUM(birds_died) AS total_mortality,
                       AVG(average_bird_weight) AS average_weight,
                       AVG(fcr) AS average_fcr,
                       MAX(daily_data_status) AS daily_data_status
                FROM ai_dailydata_data_view
                WHERE owner_id = %s AND daily_data_id IS NOT NULL
                GROUP BY flock_id
            ) daily ON daily.flock_id = base.flock_id
            LEFT JOIN (
                SELECT flock_id, SUM(sale_amount) AS total_sales
                FROM ai_sale_data_view
                WHERE owner_id = %s
                GROUP BY flock_id
            ) sales ON sales.flock_id = base.flock_id
            LEFT JOIN (
                SELECT flock_id, SUM(purchase_amount) AS total_purchases
                FROM ai_purchase_data_view
                WHERE owner_id = %s
                GROUP BY flock_id
            ) purchases ON purchases.flock_id = base.flock_id
            ORDER BY base.farm_name, base.flock_name
            LIMIT 100
            """,
            [self.user.id, self.user.id, self.user.id, self.user.id],
            metric="flock_performance",
            result_type="table",
        )

    def _farm_list_plan_llm(self) -> SQLPlan:
        """List all farms for this farmer."""
        return self._plan(
            """
            SELECT DISTINCT farm_id, farm_name, farm_city, farm_pin,
                   shed_count, farm_status
            FROM ai_farm_flock_data_view
            WHERE owner_id = %s AND farm_id IS NOT NULL
            ORDER BY farm_name
            LIMIT 100
            """,
            [self.user.id],
            metric="farm_list",
            result_type="table",
        )

    def _single_farm_plan(self, farm_id: int) -> SQLPlan:
        """Get details for a single farm."""
        return self._plan(
            """
            SELECT farm_id, farm_name, farm_address, farm_city, farm_pin,
                   shed_count, farm_status
            FROM ai_farm_flock_data_view
            WHERE owner_id = %s AND farm_id = %s
            LIMIT 1
            """,
            [self.user.id, farm_id],
            metric="complete_farm_report",
            result_type="summary",
        )

    def _flock_list_plan_llm(self) -> SQLPlan:
        """List all flocks for this farmer."""
        return self._plan(
            """
            SELECT flock_id, flock_name, farm_name, hatch_date,
                   flock_size, actual_birds, breed_name, flock_status
            FROM ai_farm_flock_data_view
            WHERE owner_id = %s AND flock_id IS NOT NULL
            GROUP BY flock_id, flock_name, farm_name, hatch_date,
                     flock_size, actual_birds, breed_name, flock_status
            ORDER BY farm_name, flock_name
            LIMIT 100
            """,
            [self.user.id],
            metric="flock_list",
            result_type="table",
        )

    def _farm_count_plan(self) -> SQLPlan:
        """Count of farms for this farmer."""
        return self._plan(
            """
            SELECT COUNT(DISTINCT farm_id) AS farm_count
            FROM ai_farm_flock_data_view
            WHERE owner_id = %s AND farm_id IS NOT NULL
            """,
            [self.user.id],
            metric="farm_count",
            result_type="count",
        )

    def _flock_count_plan(self) -> SQLPlan:
        """Count of flocks for this farmer."""
        return self._plan(
            """
            SELECT COUNT(DISTINCT flock_id) AS flock_count
            FROM ai_farm_flock_data_view
            WHERE owner_id = %s AND flock_id IS NOT NULL
            """,
            [self.user.id],
            metric="flock_count",
            result_type="count",
        )

    def _account_summary_plan(self) -> SQLPlan:
        """Full account summary: farms, flocks, birds, sales, purchases, feed, mortality, FCR."""
        return self._plan(
            """
            SELECT
              (SELECT COUNT(DISTINCT farm_id)
               FROM ai_farm_flock_data_view
               WHERE owner_id = %s AND farm_id IS NOT NULL) AS farm_count,
              (SELECT COUNT(DISTINCT flock_id)
               FROM ai_farm_flock_data_view
               WHERE owner_id = %s AND flock_id IS NOT NULL) AS flock_count,
              (SELECT COALESCE(SUM(current_rows.birds_current), 0)
               FROM ai_dailydata_data_view current_rows
               WHERE current_rows.owner_id = %s
                 AND current_rows.daily_data_id IS NOT NULL
                 AND current_rows.record_date = (
                     SELECT MAX(compare_rows.record_date)
                     FROM ai_dailydata_data_view compare_rows
                     WHERE compare_rows.owner_id = %s
                       AND compare_rows.flock_id = current_rows.flock_id
                       AND compare_rows.daily_data_id IS NOT NULL
                 )) AS current_birds,
              (SELECT COALESCE(SUM(sale_amount), 0)
               FROM ai_sale_data_view WHERE owner_id = %s) AS total_sales,
              (SELECT COALESCE(SUM(purchase_amount), 0)
               FROM ai_purchase_data_view WHERE owner_id = %s) AS total_purchases,
              (SELECT COALESCE(SUM(feed_consumed_kg), 0)
               FROM ai_dailydata_data_view WHERE owner_id = %s) AS total_feed_consumed,
              (SELECT COALESCE(SUM(birds_died), 0)
               FROM ai_dailydata_data_view WHERE owner_id = %s) AS total_mortality,
              (SELECT COALESCE(AVG(fcr), 0)
               FROM ai_dailydata_data_view
               WHERE owner_id = %s AND fcr IS NOT NULL) AS average_fcr
            """,
            [self.user.id] * 9,
            metric="farm_record_summary",
            result_type="summary",
        )

    def _sales_total_plan(self, flock_id: int | None = None) -> SQLPlan:
        """Total sales amount — optionally filtered to one flock."""
        if flock_id:
            return self._plan(
                """
                SELECT flock_id, flock_name, COALESCE(SUM(sale_amount), 0) AS total_sales,
                       COUNT(sale_id) AS sale_count
                FROM ai_sale_data_view
                WHERE owner_id = %s AND flock_id = %s AND sale_id IS NOT NULL
                GROUP BY flock_id, flock_name
                """,
                [self.user.id, flock_id],
                metric="total_sales",
                result_type="money",
            )
        return self._plan(
            """
            SELECT COALESCE(SUM(sale_amount), 0) AS total_sales,
                   COUNT(sale_id) AS sale_count
            FROM ai_sale_data_view
            WHERE owner_id = %s AND sale_id IS NOT NULL
            """,
            [self.user.id],
            metric="total_sales",
            result_type="money",
        )

    def _purchases_total_plan(self, flock_id: int | None = None) -> SQLPlan:
        """Total purchase amount — optionally filtered to one flock."""
        if flock_id:
            return self._plan(
                """
                SELECT flock_id, flock_name, COALESCE(SUM(purchase_amount), 0) AS total_purchases
                FROM ai_purchase_data_view
                WHERE owner_id = %s AND flock_id = %s
                GROUP BY flock_id, flock_name
                """,
                [self.user.id, flock_id],
                metric="total_purchases",
                result_type="money",
            )
        return self._plan(
            """
            SELECT COALESCE(SUM(purchase_amount), 0) AS total_purchases
            FROM ai_purchase_data_view
            WHERE owner_id = %s
            """,
            [self.user.id],
            metric="total_purchases",
            result_type="money",
        )

    def _mortality_total_plan(self, flock_id: int | None = None) -> SQLPlan:
        """Total mortality count — optionally filtered to one flock."""
        if flock_id:
            return self._plan(
                """
                SELECT flock_id, flock_name,
                       COALESCE(SUM(birds_died), 0) AS total_mortality,
                       MAX(total_mort) AS cumulative_mortality
                FROM ai_dailydata_data_view
                WHERE owner_id = %s AND flock_id = %s AND daily_data_id IS NOT NULL
                GROUP BY flock_id, flock_name
                """,
                [self.user.id, flock_id],
                metric="mortality",
                result_type="count",
            )
        return self._plan(
            """
            SELECT COALESCE(SUM(birds_died), 0) AS total_mortality
            FROM ai_dailydata_data_view
            WHERE owner_id = %s AND daily_data_id IS NOT NULL
            """,
            [self.user.id],
            metric="mortality",
            result_type="count",
        )

    def _feed_total_plan(self, flock_id: int | None = None) -> SQLPlan:
        """Total feed consumed — optionally filtered to one flock."""
        if flock_id:
            return self._plan(
                """
                SELECT flock_id, flock_name,
                       COALESCE(SUM(feed_consumed_kg), 0) AS total_feed_consumed
                FROM ai_dailydata_data_view
                WHERE owner_id = %s AND flock_id = %s AND daily_data_id IS NOT NULL
                GROUP BY flock_id, flock_name
                """,
                [self.user.id, flock_id],
                metric="feed_consumed",
                result_type="quantity",
            )
        return self._plan(
            """
            SELECT COALESCE(SUM(feed_consumed_kg), 0) AS total_feed_consumed
            FROM ai_dailydata_data_view
            WHERE owner_id = %s AND daily_data_id IS NOT NULL
            """,
            [self.user.id],
            metric="feed_consumed",
            result_type="quantity",
        )

    def _avg_fcr_plan(self, flock_id: int | None = None) -> SQLPlan:
        """Average FCR — optionally filtered to one flock."""
        if flock_id:
            return self._plan(
                """
                SELECT flock_id, flock_name,
                       COALESCE(AVG(fcr), 0) AS average_fcr,
                       MAX(total_fcr) AS cumulative_fcr
                FROM ai_dailydata_data_view
                WHERE owner_id = %s AND flock_id = %s
                  AND daily_data_id IS NOT NULL AND fcr IS NOT NULL
                GROUP BY flock_id, flock_name
                """,
                [self.user.id, flock_id],
                metric="average_fcr",
                result_type="decimal",
            )
        return self._plan(
            """
            SELECT COALESCE(AVG(fcr), 0) AS average_fcr
            FROM ai_dailydata_data_view
            WHERE owner_id = %s AND daily_data_id IS NOT NULL AND fcr IS NOT NULL
            """,
            [self.user.id],
            metric="average_fcr",
            result_type="decimal",
        )

    def _avg_weight_plan(self, flock_id: int | None = None) -> SQLPlan:
        """Average bird weight — optionally filtered to one flock."""
        if flock_id:
            return self._plan(
                """
                SELECT flock_id, flock_name,
                       COALESCE(AVG(average_bird_weight), 0) AS average_bird_weight
                FROM ai_dailydata_data_view
                WHERE owner_id = %s AND flock_id = %s
                  AND daily_data_id IS NOT NULL AND average_bird_weight IS NOT NULL
                GROUP BY flock_id, flock_name
                """,
                [self.user.id, flock_id],
                metric="average_weight",
                result_type="decimal",
            )
        return self._plan(
            """
            SELECT COALESCE(AVG(average_bird_weight), 0) AS average_bird_weight
            FROM ai_dailydata_data_view
            WHERE owner_id = %s AND daily_data_id IS NOT NULL
              AND average_bird_weight IS NOT NULL
            """,
            [self.user.id],
            metric="average_weight",
            result_type="decimal",
        )

    def _current_birds_plan_llm(self, flock_id: int | None = None) -> SQLPlan:
        """Current birds count using latest daily record per flock."""
        if flock_id:
            return self._plan(
                """
                SELECT current_rows.flock_id, current_rows.flock_name,
                       current_rows.birds_current, current_rows.record_date
                FROM ai_dailydata_data_view current_rows
                WHERE current_rows.owner_id = %s
                  AND current_rows.flock_id = %s
                  AND current_rows.daily_data_id IS NOT NULL
                  AND current_rows.record_date = (
                      SELECT MAX(compare_rows.record_date)
                      FROM ai_dailydata_data_view compare_rows
                      WHERE compare_rows.owner_id = %s
                        AND compare_rows.flock_id = current_rows.flock_id
                        AND compare_rows.daily_data_id IS NOT NULL
                  )
                LIMIT 1
                """,
                [self.user.id, flock_id, self.user.id],
                metric="current_birds",
                result_type="count",
            )
        return self._plan(
            """
            SELECT COALESCE(SUM(current_rows.birds_current), 0) AS current_birds
            FROM ai_dailydata_data_view current_rows
            WHERE current_rows.owner_id = %s
              AND current_rows.daily_data_id IS NOT NULL
              AND current_rows.record_date = (
                  SELECT MAX(compare_rows.record_date)
                  FROM ai_dailydata_data_view compare_rows
                  WHERE compare_rows.owner_id = %s
                    AND compare_rows.flock_id = current_rows.flock_id
                    AND compare_rows.daily_data_id IS NOT NULL
              )
            """,
            [self.user.id, self.user.id],
            metric="current_birds",
            result_type="count",
        )

    def _complete_flock_report_plan(self, flock_id: int) -> SQLPlan:
        return self._plan(
            """
            SELECT base.flock_id, base.flock_name, base.farm_name, base.hatch_date,
                   base.flock_size, base.actual_birds, base.breed_name,
                   COALESCE(latest.birds_current, 0) AS current_birds,
                   COALESCE(daily.total_mortality, 0) AS total_mortality,
                   COALESCE(daily.total_feed_consumed, 0) AS total_feed_consumed,
                   COALESCE(daily.average_weight, 0) AS average_weight,
                   COALESCE(daily.average_fcr, 0) AS average_fcr,
                   COALESCE(sales.total_sales, 0) AS total_sales,
                   COALESCE(purchases.total_purchases, 0) AS total_purchases,
                   COALESCE(base.flock_cost, 0) AS flock_cost,
                   COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS profit_loss
            FROM (
                SELECT flock_id, flock_name, farm_name, hatch_date, flock_size,
                       actual_birds, breed_name, MAX(flock_cost) AS flock_cost
                FROM ai_farm_flock_data_view
                WHERE owner_id = %s AND flock_id = %s
                GROUP BY flock_id, flock_name, farm_name, hatch_date,
                         flock_size, actual_birds, breed_name
            ) base
            LEFT JOIN (
                SELECT flock_id, SUM(birds_died) AS total_mortality,
                       SUM(feed_consumed_kg) AS total_feed_consumed,
                       AVG(average_bird_weight) AS average_weight,
                       AVG(fcr) AS average_fcr
                FROM ai_dailydata_data_view
                WHERE owner_id = %s AND flock_id = %s AND daily_data_id IS NOT NULL
                GROUP BY flock_id
            ) daily ON daily.flock_id = base.flock_id
            LEFT JOIN (
                SELECT current_rows.flock_id, current_rows.birds_current
                FROM ai_dailydata_data_view current_rows
                WHERE current_rows.owner_id = %s
                  AND current_rows.flock_id = %s
                  AND current_rows.daily_data_id IS NOT NULL
                  AND current_rows.record_date = (
                      SELECT MAX(compare_rows.record_date)
                      FROM ai_dailydata_data_view compare_rows
                      WHERE compare_rows.owner_id = %s
                        AND compare_rows.flock_id = current_rows.flock_id
                        AND compare_rows.daily_data_id IS NOT NULL
                  )
            ) latest ON latest.flock_id = base.flock_id
            LEFT JOIN (
                SELECT flock_id, SUM(sale_amount) AS total_sales
                FROM ai_sale_data_view
                WHERE owner_id = %s AND flock_id = %s
                GROUP BY flock_id
            ) sales ON sales.flock_id = base.flock_id
            LEFT JOIN (
                SELECT flock_id, SUM(purchase_amount) AS total_purchases
                FROM ai_purchase_data_view
                WHERE owner_id = %s AND flock_id = %s
                GROUP BY flock_id
            ) purchases ON purchases.flock_id = base.flock_id
            """,
            [
                self.user.id,
                flock_id,
                self.user.id,
                flock_id,
                self.user.id,
                flock_id,
                self.user.id,
                self.user.id,
                flock_id,
                self.user.id,
                flock_id,
            ],
            metric="complete_flock_report",
            result_type="summary",
        )

    def _build_plan(
        self,
        question: str,
        history: list[dict] | None,
        *,
        entity_context: str = "",
        error_feedback: str = "",
    ) -> SQLPlan:
        messages = self.prompt_builder.messages(question, history, entity_context)
        if error_feedback:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "The previous SQL plan failed validation/execution with this error: "
                        f"{error_feedback}. Return a corrected JSON SQL plan only."
                    ),
                }
            )

        result = self.client.chat(
            messages,
            model=AIBOT_SQL_DEFAULT_MODEL,
            fallback_model=AIBOT_SQL_DEFAULT_MODEL,
            temperature=0,
            max_tokens=900,
            timeout=float(os.getenv("AIBOT_SQL_TIMEOUT", "30")),
        )
        payload = self._parse_plan_payload(result.content)
        return self._to_sql_plan(payload)

    def _parse_plan_payload(self, content: str) -> LLMPlanPayload:
        cleaned = self._strip_code_fences(content)
        try:
            raw = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("The AI did not return valid JSON.") from exc

        if raw.get("blocked"):
            raise BlockedAIQuery(raw.get("reason") or "blocked")

        sql = str(raw.get("sql", "")).strip().rstrip(";")
        params = raw.get("params", [])
        if not isinstance(params, list):
            raise ValueError("AI SQL params must be a list.")

        return LLMPlanPayload(
            sql=sql,
            params=params,
            metric=str(raw.get("metric") or "farm_data_query"),
            result_type=str(raw.get("result_type") or "summary"),
        )

    def _to_sql_plan(self, payload: LLMPlanPayload) -> SQLPlan:
        placeholder_count = payload.sql.count("%s")
        owner_filter_count = re.sub(r"\s*=\s*", " = ", payload.sql.lower()).count(
            "owner_id = %s"
        )
        owner_param_count = sum(1 for param in payload.params if param == OWNER_PARAM)

        if placeholder_count != len(payload.params):
            # U: llama-3.1-8b sometimes copies an owner-only aggregate SQL
            # U: pattern correctly but forgets to repeat OWNER_PARAM for every
            # U: owner_id placeholder. This repair is intentionally narrow:
            # U: it only applies when every placeholder is an owner filter, so
            # U: it cannot invent missing farm/flock/name/date parameters.
            if placeholder_count == owner_filter_count and owner_filter_count > 0:
                payload = LLMPlanPayload(
                    sql=payload.sql,
                    params=[OWNER_PARAM] * placeholder_count,
                    metric=payload.metric,
                    result_type=payload.result_type,
                )
                owner_param_count = placeholder_count
            else:
                raise ValueError("SQL placeholder count does not match params.")
        if owner_filter_count == 0:
            raise ValueError("SQL is missing the tenant owner filter.")
        if owner_param_count != owner_filter_count:
            raise ValueError("SQL owner filters must use authenticated owner params.")

        safe_params = [
            self.user.id if param == OWNER_PARAM else param for param in payload.params
        ]
        return SQLPlan(
            sql=payload.sql,
            params=safe_params,
            metric=payload.metric,
            result_type=payload.result_type,
        )

    def _format_answer(
        self,
        question: str,
        plan: SQLPlan,
        rows: list[dict],
        history: list[dict] | None,
        entity_context: str = "",
    ) -> str:
        compact_rows = self._json_safe_rows(rows[:25])
        prompt = f"""
Farmer question:
{question}

Entity context:
{entity_context or "No entity context."}

Metric:
{plan.metric}

Result rows:
{json.dumps(compact_rows, ensure_ascii=True)}

If there are more than 25 matching rows, only the first 25 are shown here.
Write the answer for the farmer.
If the farmer used a rough phrase like "flock 1" but Entity Context resolved it to a real flock, answer for the resolved flock name/id and do not say the rough phrase has no data.
If the question is a comparison or ranking request, write a detailed text analysis identifying the specific flocks requested. Otherwise, if there are multiple rows and no specific ranking is asked, keep the text short because the frontend will render the rows in structured cards/tables.
""".strip()
        try:
            result = self.client.chat(
                [
                    {"role": "system", "content": ANSWER_SYSTEM},
                    *self._history_messages(history or []),
                    {"role": "user", "content": prompt},
                ],
                model=AIBOT_SQL_DEFAULT_MODEL,
                fallback_model=AIBOT_SQL_DEFAULT_MODEL,
                temperature=0.1,
                max_tokens=600,
                timeout=float(os.getenv("AIBOT_SQL_TIMEOUT", "30")),
            )
            return result.content
        except (GroqAllKeysFailed, KeyError, ValueError, httpx.HTTPError):
            logger.warning(
                "Groq answer formatting failed; returning safe unformatted result.",
                exc_info=True,
            )
            # U: NEW: do not silently fall back to the old deterministic answer
            # U: formatter. The response still includes rows/display payload, so
            # U: the frontend can render the data without mixing approaches.
            if rows:
                return (
                    "I found the matching farm records, but I could not format the "
                    "answer naturally right now. Please ask again or use a more "
                    "specific farm/flock question."
                )
            return "I could not find matching records in your farm data for that question."

    def _history_messages(self, history: list[dict]) -> list[dict[str, str]]:
        messages = []
        for item in history[-16:]:
            role = "assistant" if item.get("role") == "assistant" else "user"
            content = str(item.get("content", "")).strip()
            if content:
                messages.append({"role": role, "content": content})
        return messages

    def _sql_error_response(self, reason: str) -> dict:
        logger.warning("Groq SQL Farmer AI failed without rule fallback: %s", reason)
        return {
            "status": "error",
            "message": (
                "I couldn't answer that question using your farm records. "
                "Please try asking a more specific question about your farms, flocks, "
                "daily data, sales, purchases, mortality, feed, FCR, or profit."
            ),
            "details": reason,
            "suggestion": (
                "Example: 'daily data only for flock 3', 'total flocks in each farm', "
                "or 'profit for second flock'."
            ),
            "route": TEXT_TO_SQL,
            "engine": "groq_sql",
        }

    def _display_payload(self, plan: SQLPlan, rows: list[dict]) -> dict | None:
        safe_rows = self._json_safe_rows(rows[:30])
        if not safe_rows:
            return None

        if plan.metric in {"farm_list", "complete_farm_report"}:
            return self._cards_payload(
                title="Farm records",
                rows=safe_rows,
                title_keys=("farm_name",),
                field_keys=(
                    "farm_city",
                    "farm_pin",
                    "shed_count",
                    "farm_status",
                    "flock_count",
                ),
            )

        if plan.metric in {"flock_list", "all_flocks", "complete_flock_report"}:
            return self._cards_payload(
                title="Flock records",
                rows=safe_rows,
                title_keys=("flock_name",),
                field_keys=(
                    "farm_name",
                    "hatch_date",
                    "flock_size",
                    "actual_birds",
                    "current_birds",
                    "breed_name",
                    "flock_cost",
                    "total_sales",
                    "total_purchases",
                    "profit_loss",
                ),
            )

        if plan.metric == "flock_breeds_by_flock":
            return self._cards_payload(
                title="Flock breeds",
                rows=safe_rows,
                title_keys=("flock_name",),
                field_keys=("farm_name", "breed_name"),
            )

        # U: NEW: Flock performance table.
        if plan.metric == "flock_performance":
            return self._table_payload(
                title="Flock performance",
                rows=safe_rows,
                preferred_keys=(
                    "flock_name",
                    "farm_name",
                    "total_feed",
                    "total_mortality",
                    "avg_weight",
                    "avg_fcr",
                    "profit_loss",
                    "daily_data_status",
                ),
            )

        if plan.metric in {"daily_data_by_flock", "latest_flock_status"}:
            return self._table_payload(
                title="Daily data",
                rows=safe_rows,
                preferred_keys=(
                    "record_date",
                    "flock_name",
                    "birds_died",
                    "total_mort",
                    "birds_current",
                    "feed_consumed_kg",
                    "average_bird_weight",
                    "fcr",
                    "remarks",
                ),
            )

        if plan.metric.startswith("daily_metric_extreme_"):
            return self._table_payload(
                title="Daily metric dates",
                rows=safe_rows,
                preferred_keys=(
                    "point_type",
                    "record_date",
                    "flock_name",
                    "metric_value",
                    "birds_died",
                    "birds_current",
                    "feed_consumed_kg",
                    "average_bird_weight",
                    "fcr",
                ),
            )

        if plan.metric == "improvement_advice":
            return None

        if "profit" in plan.metric or "loss" in plan.metric:
            return self._table_payload(
                title="Profit / loss",
                rows=safe_rows,
                preferred_keys=(
                    "flock_name",
                    "farm_name",
                    "total_sales",
                    "total_purchases",
                    "flock_cost",
                    "result",
                    "profit_loss",
                ),
            )

        # U: NEW: Summary/scalar metrics — show as a simple summary card.
        if plan.metric in {
            "farm_record_summary", "total_sales", "total_purchases",
            "mortality", "feed_consumed", "average_fcr", "average_weight",
            "current_birds", "farm_count", "flock_count",
        }:
            if len(safe_rows) == 1:
                return self._summary_card_payload(plan.metric, safe_rows[0])
            # Multi-row (flock-filtered) — use a table.
            return self._table_payload(title="Records", rows=safe_rows)

        if len(safe_rows) > 1 or plan.result_type == "table":
            return self._table_payload(title="Records", rows=safe_rows)

        return None

    def _summary_card_payload(self, metric: str, row: dict) -> dict:
        """Build a simple key-value summary card for scalar metrics."""
        title_map = {
            "farm_record_summary": "Account summary",
            "total_sales": "Total sales",
            "total_purchases": "Total purchases",
            "mortality": "Mortality",
            "feed_consumed": "Feed consumed",
            "average_fcr": "Average FCR",
            "average_weight": "Average weight",
            "current_birds": "Current birds",
            "farm_count": "Farm count",
            "flock_count": "Flock count",
        }
        title = title_map.get(metric, "Summary")
        card_rows = [
            {
                "label": self._display_label(key),
                "value": self._format_display_value(key, value),
            }
            for key, value in row.items()
            if key not in {
                "owner_id", "farm_id", "flock_id", "sale_id",
                "purchase_id", "daily_data_id",
            }
            and value not in (None, "")
        ]
        return {"type": "cards", "title": title, "cards": [{"title": title, "rows": card_rows}]}

    def _cards_payload(
        self,
        *,
        title: str,
        rows: list[dict],
        title_keys: tuple[str, ...],
        field_keys: tuple[str, ...],
    ) -> dict:
        cards = []
        for row in rows:
            card_title = next(
                (self._format_display_value(key, row.get(key)) for key in title_keys if row.get(key) not in (None, "")),
                "Record",
            )
            card_rows = []
            for key in field_keys:
                if key not in row or row.get(key) in (None, ""):
                    continue
                card_rows.append(
                    {
                        "label": self._display_label(key),
                        "value": self._format_display_value(key, row.get(key)),
                    }
                )
            cards.append({"title": card_title, "rows": card_rows})
        return {"type": "cards", "title": title, "cards": cards}

    def _table_payload(
        self,
        *,
        title: str,
        rows: list[dict],
        preferred_keys: tuple[str, ...] | None = None,
    ) -> dict:
        keys = self._display_keys(rows, preferred_keys=preferred_keys)
        return {
            "type": "table",
            "title": title,
            "columns": [{"key": key, "label": self._display_label(key)} for key in keys],
            "rows": [
                {
                    key: self._format_display_value(key, row.get(key))
                    for key in keys
                }
                for row in rows
            ],
        }

    def _display_keys(
        self,
        rows: list[dict],
        *,
        preferred_keys: tuple[str, ...] | None = None,
    ) -> list[str]:
        hidden = {"owner_id", "farm_id", "flock_id", "sale_id", "purchase_id", "daily_data_id"}
        if preferred_keys:
            keys = [
                key
                for key in preferred_keys
                if any(key in row and row.get(key) not in (None, "") for row in rows)
            ]
        else:
            keys = []
            for row in rows:
                for key in row.keys():
                    if key not in hidden and key not in keys:
                        keys.append(key)
        return keys[:8]

    def _display_label(self, key: str) -> str:
        labels = {
            "farm_name": "Farm",
            "farm_city": "City",
            "farm_pin": "PIN",
            "shed_count": "Sheds",
            "farm_status": "Status",
            "flock_count": "Flocks",
            "farm_count": "Farms",
            "flock_name": "Flock",
            "hatch_date": "Hatch date",
            "flock_size": "Starting birds",
            "actual_birds": "Actual birds",
            "current_birds": "Current birds",
            "breed_name": "Breed",
            "flock_cost": "Flock cost",
            "total_sales": "Sales",
            "total_purchases": "Purchases",
            "profit_loss": "Profit / loss",
            "result": "Result",
            "data_note": "Data note",
            "data_ready": "Complete cost data",
            "sale_count": "Sale count",
            "latest_daily_date": "Latest daily date",
            "record_date": "Date",
            "point_type": "Point",
            "metric_value": "Value",
            "birds_died": "Mortality",
            "total_mort": "Total mortality",
            "total_mortality": "Total mortality",
            "birds_current": "Current birds",
            "feed_consumed_kg": "Feed",
            "total_feed_consumed": "Total feed",
            "total_feed": "Feed",
            "average_bird_weight": "Avg. weight",
            "avg_weight": "Avg. weight",
            "fcr": "FCR",
            "avg_fcr": "FCR",
            "average_fcr": "Avg. FCR",
            "cumulative_fcr": "Cumulative FCR",
            "cumulative_mortality": "Cumulative mortality",
            "daily_data_status": "Daily Data Status",
            "remarks": "Remarks",
            "flock_status": "Flock status",
        }
        return labels.get(key, key.replace("_", " ").title())

    def _format_display_value(self, key: str, value):
        if value in (None, ""):
            return "Not available"
        if isinstance(value, Decimal):
            value = float(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if key in {
            "flock_cost", "total_sales", "total_purchases", "profit_loss",
            "result", "sale_amount", "purchase_amount",
        }:
            try:
                return f"Rs. {float(value):,.2f}"
            except (TypeError, ValueError):
                return str(value)
        if key in {"feed_consumed_kg", "total_feed_consumed", "total_feed"}:
            try:
                return f"{float(value):,.2f} kg"
            except (TypeError, ValueError):
                return str(value)
        if key in {"average_bird_weight", "avg_weight"}:
            try:
                return f"{float(value):,.2f} gm"
            except (TypeError, ValueError):
                return str(value)
        if key in {"fcr", "avg_fcr", "average_fcr", "cumulative_fcr"}:
            try:
                v = float(value)
                return f"{v:,.2f}" if v != 0 else "Not available"
            except (TypeError, ValueError):
                return str(value)
        if isinstance(value, float):
            return f"{value:,.2f}"
        return str(value)

    def _entity_metadata(self, entity_context: str) -> dict:
        metadata = {}
        flock_id = (
            self._line_int(entity_context, "Resolved flock mention", "flock_id")
            or self._line_int(entity_context, "Last referenced flock from recent chat", "flock_id")
            or self._line_int(entity_context, "Active app flock context", "flock_id")
        )
        farm_id = (
            self._line_int(entity_context, "Resolved flock mention", "farm_id")
            or self._line_int(entity_context, "Resolved farm mention", "farm_id")
            or self._line_int(entity_context, "Last referenced flock from recent chat", "farm_id")
            or self._line_int(entity_context, "Last referenced farm from recent chat", "farm_id")
            or self._line_int(entity_context, "Active app flock context", "farm_id")
            or self._line_int(entity_context, "Active app farm context", "farm_id")
        )
        if farm_id:
            metadata["resolved_farm_id"] = farm_id
        if flock_id:
            metadata["resolved_flock_id"] = flock_id
            metadata["intent_entity_type"] = "flock"
        elif farm_id:
            metadata["intent_entity_type"] = "farm"
        return metadata

    def _blocked_message(self, reason: str) -> str:
        if "cross_tenant" in reason:
            return "I can only answer questions about your own Chikooza farm data."
        if "conversation_only" in reason:
            return "Okay. Ask me whenever you need farm records."
        return (
            "I could not connect that question to a safe farm-record query. "
            "I can answer about your farms, flocks, sales, purchases, daily data, "
            "mortality, feed, weight, FCR, and profit."
        )

    def _blocked_suggestion(self, reason: str) -> str:
        if "cross_tenant" in reason:
            return "Ask only about the farm records in your own logged-in account."
        if "conversation_only" in reason:
            return "Ask about farms, flocks, sales, purchases, daily data, FCR, or profit when needed."
        return "Try: 'show my farm summary', 'total sales', 'current birds', 'average FCR', or 'profit or loss'."

    def _conversation_only_answer(self, question: str) -> str:
        query = normalize_ai_query(question)
        if re.match(r"^(thanks|thank you|okay thanks|ok thanks|thanks okay)[!. ]*$", query):
            return "You're welcome. Ask me whenever you need farm records."
        if re.match(r"^(ok|okay)[!. ]*$", query):
            return "Okay. Ask your next farm question whenever you want."
        # U: NEW: catch "okay next" / "okay now" / "okay then" prefixes that are
        # U: just transition phrases — NOT standalone conversational messages.
        # U: They should not produce a conversation-only answer; the rest of the
        # U: question text is the actual query and will be handled by SQL planner.
        if re.match(r"^(ok|okay)(?:\s+(?:next|now|then|so|well|fine))+[!., ]*$", query):
            return "Okay. Ask your next farm question whenever you want."
        if re.match(r"^(nothing more|no more|that's all|thats all|all good|done|stop|enough)[!. ]*$", query):
            return "Okay, I will stop here. Ask me whenever you need farm records."
        if re.match(r"^(huh|what do you mean|what meaning|what)[?!. ]*$", query):
            return (
                "I can answer questions from your saved farm records: farms, flocks, "
                "sales, purchases, daily data, mortality, feed, weight, FCR, and profit."
            )
        if re.match(r"^(hello|hi|hey|namaste)[!. ]*$", query):
            return (
                "Hello. Ask me about your farms, flocks, sales, purchases, daily data, "
                "mortality, feed, weight, FCR, or profit."
            )
        return ""

    def _json_safe_rows(self, rows: list[dict]) -> list[dict]:
        return [
            {key: self._json_safe_value(value) for key, value in row.items() if not key.endswith("_id")}
            for row in rows
        ]

    def _json_safe_value(self, value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    def _strip_code_fences(self, content: str) -> str:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()


class BlockedAIQuery(ValueError):
    pass
