import re
from datetime import timedelta

from .modern_services import DateRange, SQLPlan, TEXT_TO_SQL

# U: LEGACY / NOT LIVE: this trend helper belongs to the old deterministic
# U: intent-agent pipeline. The active Farmer AI endpoint now uses
# U: aibot/llm_sql.py for Groq SQL planning and answer formatting.


class ChikoozaTrendComparisonService:
    """
    U: NEW: Safe trend/comparison reports for Farmer AI.
    U: This service builds fixed parameterized SQL only; Groq never writes SQL.
    """

    DAILY_METRICS = {"mortality", "feed", "weight", "fcr", "current_birds"}
    HIGHER_IS_BETTER = {"sales", "purchases", "profit", "feed", "weight", "current_birds"}
    LOWER_IS_BETTER = {"mortality", "fcr"}

    def __init__(self, deterministic_service):
        self.deterministic_service = deterministic_service

    def answer(self, question: str, intent=None, entity_resolution=None) -> dict:
        query = self._normalize(question)
        if getattr(intent, "intent", "") == "best_flock_report":
            return self._best_flock_answer(query, entity_resolution=entity_resolution)
        if getattr(intent, "intent", "") == "trend_report":
            return self._trend_answer(query, entity_resolution=entity_resolution)
        return self._comparison_answer(query, entity_resolution=entity_resolution)

    def _comparison_answer(self, query: str, entity_resolution=None) -> dict:
        metrics = self._metrics_from_query(query, default=("sales", "purchases", "profit"))
        current_range, previous_range = self._comparison_ranges(query)
        farm_id, flock_id = self._entity_ids(entity_resolution)
        items = []
        lines = [
            f"Comparison for {current_range.label} vs {previous_range.label} from your Chikooza records."
        ]

        for metric in metrics:
            current = self._metric_value(metric, current_range, farm_id=farm_id, flock_id=flock_id)
            previous = self._metric_value(metric, previous_range, farm_id=farm_id, flock_id=flock_id)
            change = current - previous
            direction = "increased" if change > 0 else "decreased" if change < 0 else "stayed the same"
            items.append(
                {
                    "metric": metric,
                    "current": current,
                    "previous": previous,
                    "change": change,
                    "current_range": self._range_data(current_range),
                    "previous_range": self._range_data(previous_range),
                }
            )
            lines.append(
                f"- {self._metric_label(metric)}: {self._format_value(metric, current)} vs "
                f"{self._format_value(metric, previous)}; {direction} by {self._format_value(metric, abs(change))}."
            )

        return self._response("comparison_report", "\n".join(lines), {"items": items})

    def _trend_answer(self, query: str, entity_resolution=None) -> dict:
        metric = self._metrics_from_query(query, default=("mortality",))[0]
        date_range = self.deterministic_service._date_range_from_query(query) or self._default_trend_range()
        farm_id, flock_id = self._entity_ids(entity_resolution)
        plan = self._trend_plan(metric, date_range, farm_id=farm_id, flock_id=flock_id)
        rows = self.deterministic_service.executor.execute(plan)
        values = [float(row.get("result") or 0) for row in rows]
        first = values[0] if values else 0
        last = values[-1] if values else 0
        direction = "increasing" if last > first else "decreasing" if last < first else "flat"
        label = self._metric_label(metric)
        if not rows:
            answer = f"I could not find saved {label.lower()} records for {date_range.label}."
        else:
            answer = (
                f"{label} trend for {date_range.label}: {direction}. "
                f"First value {self._format_value(metric, first)}, latest value {self._format_value(metric, last)} "
                f"across {len(rows)} saved period(s)."
            )
        return self._response(
            "trend_report",
            answer,
            {
                "metric": metric,
                "date_range": self._range_data(date_range),
                "direction": direction,
                "rows": rows,
            },
            rows=rows,
            query=plan.sql,
            params=plan.params,
        )

    def _best_flock_answer(self, query: str, entity_resolution=None) -> dict:
        metric = self._metrics_from_query(query, default=("profit",))[0]
        date_range = self.deterministic_service._date_range_from_query(query)
        farm_id, _ = self._entity_ids(entity_resolution)
        plan = self._best_flock_plan(metric, date_range=date_range, farm_id=farm_id)
        rows = self.deterministic_service.executor.execute(plan)
        if not rows:
            answer = "I could not find saved flock records to compare."
        else:
            top = rows[0]
            answer = (
                f"Best flock by {self._metric_label(metric).lower()}"
                f"{f' for {date_range.label}' if date_range else ''}: "
                f"{top.get('flock_name') or 'Unnamed flock'} from {top.get('farm_name') or 'its farm'} "
                f"with {self._format_value(metric, float(top.get('result') or 0))}."
            )
        return self._response(
            "best_flock_report",
            answer,
            {"metric": metric, "date_range": self._range_data(date_range), "rows": rows},
            rows=rows,
            query=plan.sql,
            params=plan.params,
        )

    def _metric_value(
        self,
        metric: str,
        date_range: DateRange,
        *,
        farm_id: int | None,
        flock_id: int | None,
    ) -> float:
        plan = self._metric_plan(metric, date_range, farm_id=farm_id, flock_id=flock_id)
        rows = self.deterministic_service.executor.execute(plan)
        row = rows[0] if rows else {}
        if metric == "profit":
            return float(row.get("result") or 0)
        return float(row.get("result") or 0)

    def _metric_plan(
        self,
        metric: str,
        date_range: DateRange,
        *,
        farm_id: int | None,
        flock_id: int | None,
    ) -> SQLPlan:
        if metric == "profit":
            return self.deterministic_service._profit_plan(
                farm_id,
                flock_id,
                date_range=date_range,
            )
        plan_data = self._aggregate_metric(metric)
        if metric == "current_birds":
            return self.deterministic_service._current_birds_plan(
                farm_id,
                flock_id,
                date_range=date_range,
            )
        return self.deterministic_service._aggregate_plan(
            plan_data["view"],
            plan_data["expression"],
            plan_data["metric"],
            plan_data["result_type"],
            farm_id=farm_id,
            flock_id=flock_id,
            date_column=plan_data["date_column"],
            date_range=date_range,
        )

    def _trend_plan(
        self,
        metric: str,
        date_range: DateRange,
        *,
        farm_id: int | None,
        flock_id: int | None,
    ) -> SQLPlan:
        if metric not in self.DAILY_METRICS:
            metric = "mortality"
        plan_data = self._aggregate_metric(metric)
        where_sql, params = self.deterministic_service._where_clause(
            farm_id=farm_id,
            flock_id=flock_id,
        )
        where_sql, params = self.deterministic_service._apply_date_range(
            where_sql,
            params,
            plan_data["date_column"],
            date_range,
        )
        sql = (
            f"SELECT {plan_data['date_column']} AS period, {plan_data['expression']} AS result "
            f"FROM {plan_data['view']} WHERE {where_sql} "
            f"AND daily_data_id IS NOT NULL GROUP BY {plan_data['date_column']} "
            f"ORDER BY {plan_data['date_column']} LIMIT 90"
        )
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=params,
            metric=f"{metric}_trend",
            result_type="table",
            date_range=date_range,
        )

    def _best_flock_plan(
        self,
        metric: str,
        *,
        date_range: DateRange | None,
        farm_id: int | None,
    ) -> SQLPlan:
        if metric == "profit":
            return self._best_flock_profit_plan(date_range=date_range, farm_id=farm_id)
        plan_data = self._aggregate_metric(metric if metric != "current_birds" else "sales")
        where_sql, params = self.deterministic_service._where_clause(farm_id=farm_id)
        if plan_data.get("date_column"):
            where_sql, params = self.deterministic_service._apply_date_range(
                where_sql,
                params,
                plan_data["date_column"],
                date_range,
            )
        order = "ASC" if metric in self.LOWER_IS_BETTER else "DESC"
        sql = (
            f"SELECT flock_id, flock_name, farm_name, {plan_data['expression']} AS result "
            f"FROM {plan_data['view']} WHERE {where_sql} AND flock_id IS NOT NULL "
            f"GROUP BY flock_id, flock_name, farm_name ORDER BY result {order} LIMIT 5"
        )
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=params,
            metric=f"best_flock_{metric}",
            result_type="table",
            date_range=date_range,
        )

    def _best_flock_profit_plan(self, *, date_range: DateRange | None, farm_id: int | None) -> SQLPlan:
        base_where, base_params = self.deterministic_service._where_clause(farm_id=farm_id)
        sale_where, sale_params = self.deterministic_service._where_clause(farm_id=farm_id)
        sale_where, sale_params = self.deterministic_service._apply_date_range(
            sale_where,
            sale_params,
            "sale_date",
            date_range,
        )
        purchase_where, purchase_params = self.deterministic_service._where_clause(farm_id=farm_id)
        purchase_where, purchase_params = self.deterministic_service._apply_date_range(
            purchase_where,
            purchase_params,
            "purchase_date",
            date_range,
        )
        sql = f"""
            SELECT
                base.flock_id,
                base.flock_name,
                base.farm_name,
                COALESCE(sales.total_sales, 0) AS total_sales,
                COALESCE(purchases.total_purchases, 0) AS total_purchases,
                COALESCE(base.flock_cost, 0) AS flock_cost,
                COALESCE(sales.total_sales, 0) - COALESCE(purchases.total_purchases, 0) - COALESCE(base.flock_cost, 0) AS result
            FROM (
                SELECT flock_id, flock_name, farm_name, MAX(flock_cost) AS flock_cost
                FROM ai_farm_flock_data_view
                WHERE {base_where} AND flock_id IS NOT NULL
                GROUP BY flock_id, flock_name, farm_name
            ) base
            LEFT JOIN (
                SELECT flock_id, SUM(sale_amount) AS total_sales
                FROM ai_sale_data_view
                WHERE {sale_where} AND sale_id IS NOT NULL
                GROUP BY flock_id
            ) sales ON sales.flock_id = base.flock_id
            LEFT JOIN (
                SELECT flock_id, SUM(purchase_amount) AS total_purchases
                FROM ai_purchase_data_view
                WHERE {purchase_where} AND purchase_date IS NOT NULL
                GROUP BY flock_id
            ) purchases ON purchases.flock_id = base.flock_id
            ORDER BY result DESC
            LIMIT 5
        """
        return SQLPlan(
            sql=re.sub(r"\s+", " ", sql).strip(),
            params=base_params + sale_params + purchase_params,
            metric="best_flock_profit",
            result_type="table",
            date_range=date_range,
        )

    def _aggregate_metric(self, metric: str) -> dict:
        mapping = {
            "sales": {
                "view": "ai_sale_data_view",
                "expression": "COALESCE(SUM(sale_amount), 0)",
                "metric": "total_sales",
                "result_type": "money",
                "date_column": "sale_date",
            },
            "purchases": {
                "view": "ai_purchase_data_view",
                "expression": "COALESCE(SUM(purchase_amount), 0)",
                "metric": "total_purchases",
                "result_type": "money",
                "date_column": "purchase_date",
            },
            "mortality": {
                "view": "ai_dailydata_data_view",
                "expression": "COALESCE(SUM(birds_died), 0)",
                "metric": "mortality",
                "result_type": "count",
                "date_column": "record_date",
            },
            "feed": {
                "view": "ai_dailydata_data_view",
                "expression": "COALESCE(SUM(feed_consumed_kg), 0)",
                "metric": "feed_consumed",
                "result_type": "quantity",
                "date_column": "record_date",
            },
            "weight": {
                "view": "ai_dailydata_data_view",
                "expression": "COALESCE(AVG(average_bird_weight), 0)",
                "metric": "average_weight",
                "result_type": "decimal",
                "date_column": "record_date",
            },
            "fcr": {
                "view": "ai_dailydata_data_view",
                "expression": "COALESCE(AVG(fcr), 0)",
                "metric": "fcr",
                "result_type": "decimal",
                "date_column": "record_date",
            },
        }
        return mapping.get(metric, mapping["sales"])

    def _comparison_ranges(self, query: str) -> tuple[DateRange, DateRange]:
        current = self.deterministic_service._date_range_from_query(query)
        today = self.deterministic_service._today()
        if not current:
            current = DateRange(today - timedelta(days=29), today, "last 30 days")
        if "last month" in query and "this month" in query:
            previous = self.deterministic_service._date_range_from_query("last month")
        elif "last week" in query and "this week" in query:
            previous = self.deterministic_service._date_range_from_query("last week")
        elif "yesterday" in query and "today" in query:
            previous = self.deterministic_service._date_range_from_query("yesterday")
        else:
            previous = self._previous_matching_range(current)
        return current, previous

    def _previous_matching_range(self, current: DateRange) -> DateRange:
        length = (current.end - current.start).days + 1
        end = current.start - timedelta(days=1)
        start = end - timedelta(days=length - 1)
        return DateRange(start, end, f"previous {length} days")

    def _default_trend_range(self) -> DateRange:
        today = self.deterministic_service._today()
        return DateRange(today - timedelta(days=29), today, "last 30 days")

    def _metrics_from_query(self, query: str, default: tuple[str, ...]) -> list[str]:
        hits = []
        checks = (
            ("profit", r"\b(?:profit|loss|net|earning|earnings|perform|performance|best|top)\b"),
            ("sales", r"\b(?:sale|sales|revenue|income|sold)\b"),
            ("purchases", r"\b(?:purchase|purchases|expense|expenses|spent|spend|costs?)\b"),
            ("mortality", r"\b(?:mortality|death|deaths|died|dead)\b"),
            ("feed", r"\bfeed\b"),
            ("weight", r"\b(?:weight|body weight)\b"),
            ("fcr", r"\b(?:fcr|feed conversion)\b"),
            ("current_birds", r"\b(?:current birds|bird count|birds left)\b"),
        )
        for metric, pattern in checks:
            if re.search(pattern, query):
                hits.append(metric)
        return hits or list(default)

    def _entity_ids(self, entity_resolution) -> tuple[int | None, int | None]:
        if not entity_resolution:
            return None, None
        return (
            getattr(entity_resolution, "farm_id", None),
            getattr(entity_resolution, "flock_id", None),
        )

    def _metric_label(self, metric: str) -> str:
        return {
            "sales": "Sales",
            "purchases": "Purchases",
            "profit": "Profit/Loss",
            "mortality": "Mortality",
            "feed": "Feed consumed",
            "weight": "Average weight",
            "fcr": "Average FCR",
            "current_birds": "Current birds",
        }.get(metric, metric.replace("_", " ").title())

    def _format_value(self, metric: str, value: float) -> str:
        if metric in {"sales", "purchases", "profit"}:
            return f"Rs. {value:,.2f}"
        if metric == "feed":
            return f"{value:,.2f} kg"
        if metric in {"weight", "fcr"}:
            return f"{value:,.2f}"
        return f"{value:,.0f}"

    def _range_data(self, date_range: DateRange | None) -> dict | None:
        if not date_range:
            return None
        return {
            "start": date_range.start.isoformat(),
            "end": date_range.end.isoformat(),
            "label": date_range.label,
        }

    def _response(
        self,
        metric: str,
        answer: str,
        data: dict,
        *,
        rows: list | None = None,
        query: str | None = None,
        params: list | None = None,
    ) -> dict:
        return {
            "status": "success",
            "data": data,
            "answer": answer,
            "message": answer,
            "rows": rows or [],
            "query": query,
            "params": params or [],
            "route": TEXT_TO_SQL,
            "metric": metric,
            "engine": "safe_trend_comparison",
        }

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").lower()).strip()
