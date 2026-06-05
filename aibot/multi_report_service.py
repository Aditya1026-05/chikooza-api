import logging
import re
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger(__name__)

# U: LEGACY / NOT LIVE: this multi-report helper belongs to the old
# U: deterministic intent-agent pipeline. The active Farmer AI endpoint now
# U: uses aibot/llm_sql.py for Groq SQL planning and structured display data.


class ChikoozaMultiReportService:
    """
    U: NEW: Handles compound farmer questions by decomposing them into multiple
    U: fixed tenant-safe backend report tasks. This avoids forcing a long
    U: question into one summary metric.
    """

    MAX_BREAKDOWN_ITEMS = 15

    ACCOUNT_TASKS = {
        "farm_count": "how many farms",
        "flock_count": "how many flocks",
        "sales": "total sales",
        "purchases": "total purchases",
        "profit": "profit or loss",
        "current_birds": "current birds",
        "mortality": "mortality",
        "feed": "feed consumed",
        "weight": "average weight",
        "fcr": "average fcr",
    }

    ALL_METRICS = (
        "sales",
        "purchases",
        "profit",
        "current_birds",
        "mortality",
        "feed",
        "weight",
        "fcr",
    )

    def __init__(self, deterministic_service):
        self.deterministic_service = deterministic_service

    def answer(
        self,
        question: str,
        history: list | None = None,
        intent=None,
        entity_resolution=None,
    ) -> dict:
        spec = self._spec(question, intent=intent)
        target_entity_type = self._target_entity_type(intent, entity_resolution)
        if target_entity_type and spec["wants_all"]:
            # U: OLD: targeted complete-report prompts still expanded to broad
            # U: farm/flock breakdowns. U: NEW: keep the report scoped to the
            # U: already resolved farm/flock.
            include_child_flocks = target_entity_type == "farm" and spec["include_flocks"]
            spec = {
                **spec,
                "include_account": False,
                "include_farms": False,
                "include_flocks": include_child_flocks,
                "breakdown_farms": False,
                "breakdown_flocks": include_child_flocks,
            }
        report = {
            "requested_metrics": sorted(spec["metrics"]),
            "date_range": self._json_safe(spec.get("date_range")),
            "account": (
                self._account_section(spec, history=history)
                if spec["include_account"]
                else {}
            ),
            "farms": [],
            "flocks": [],
            "target": [],
            "requested_sections": {
                "farms": spec["include_farms"],
                "flocks": spec["include_flocks"],
            },
            "limits": {"max_breakdown_items": self.MAX_BREAKDOWN_ITEMS},
        }

        target_phrase = self._target_phrase(intent)
        if target_phrase or target_entity_type:
            report["target"] = self._target_section(
                target_phrase,
                spec,
                history=history,
                target_entity_type=target_entity_type,
                entity_resolution=entity_resolution,
            )
            if spec["include_flocks"]:
                # U: NEW: for "show flocks and all stuff for 2nd farm", keep
                # U: the farm target and list only that farm's flocks.
                report["flocks"] = self._flock_breakdown(
                    spec,
                    history=history,
                    farm_id=getattr(entity_resolution, "farm_id", None)
                    if target_entity_type == "farm"
                    else None,
                )
        else:
            if spec["include_farms"]:
                report["farms"] = self._farm_breakdown(spec, history=history)
            if spec["include_flocks"]:
                report["flocks"] = self._flock_breakdown(spec, history=history)

        answer = self._format_report(report)
        return {
            "status": "success",
            "data": self._json_safe(report),
            "answer": answer,
            "message": answer,
            "rows": [],
            "query": None,
            "params": [],
            "route": "TEXT_TO_SQL",
            "metric": "multi_farm_report",
            "engine": "safe_multi_intent",
        }

    def _spec(self, question: str, intent=None) -> dict:
        query = self._normalize(question)
        metrics = set()

        if self._mentions_count(query) and re.search(r"\bfarms?\b", query):
            metrics.add("farm_count")
        if self._mentions_count(query) and re.search(
            r"\b(?:flocks?|batches?)\b", query
        ):
            metrics.add("flock_count")
        if re.search(r"\b(?:sale|sales|revenue|income|sold)\b", query):
            metrics.add("sales")
        if re.search(
            r"\b(?:purchase|purchases|expense|expenses|spent|spend|costs?)\b", query
        ):
            metrics.add("purchases")
        if re.search(r"\b(?:profit|loss|net|earning|earnings)\b", query):
            metrics.add("profit")
        if re.search(r"\b(?:current birds?|birds? left|bird count)\b", query):
            metrics.add("current_birds")
        if re.search(r"\b(?:mortality|deaths?|died|dead birds?)\b", query):
            metrics.add("mortality")
        if re.search(r"\bfeed\b", query) and "feed conversion" not in query:
            metrics.add("feed")
        if re.search(r"\b(?:weight|body weight)\b", query):
            metrics.add("weight")
        if re.search(r"\b(?:fcr|feed conversion)\b", query):
            metrics.add("fcr")

        wants_all = self._wants_all_metrics(query)
        if getattr(intent, "source", "") == "rule_summary_detail_followup":
            # U: NEW: "now tell this in detail" after an account summary should
            # U: expand the previous account summary into full farm/flock detail.
            wants_all = True
        date_range = self._date_range_from_query(query)
        include_farms = bool(re.search(r"\bfarms?\b", query))
        include_flocks = bool(re.search(r"\b(?:flocks?|batches?)\b", query))
        breakdown_farms = include_farms and self._wants_breakdown(query, "farm")
        breakdown_flocks = include_flocks and self._wants_breakdown(query, "flock")

        targeted_complete = wants_all and (
            self._intent_has_specific_target(intent) or self._has_singular_target(query)
        )

        if wants_all and not targeted_complete:
            metrics.update(self.ALL_METRICS)
            # U: OLD: "show all my data" only returned account totals unless the
            # U: farmer explicitly said farms/flocks. U: NEW: complete-data
            # U: wording includes both saved farms and saved flocks by default.
            include_farms = True
            include_flocks = True
            metrics.add("farm_count")
            metrics.add("flock_count")
            breakdown_farms = True
            breakdown_flocks = True

        elif wants_all:
            metrics.update(self.ALL_METRICS)

        if include_farms and self._mentions_count(query):
            metrics.add("farm_count")
        if include_flocks and self._mentions_count(query):
            metrics.add("flock_count")

        if not metrics:
            metrics.update(
                ("farm_count", "flock_count", "sales", "purchases", "profit")
            )

        return {
            "metrics": metrics,
            "include_farms": include_farms or breakdown_farms,
            "include_flocks": include_flocks or breakdown_flocks,
            "breakdown_farms": breakdown_farms,
            "breakdown_flocks": breakdown_flocks,
            "wants_all": wants_all,
            "include_account": True,
            "date_range": date_range,
        }

    def _account_section(self, spec: dict, history: list | None) -> dict:
        account = {}
        for metric in self._ordered_metrics(spec["metrics"]):
            if spec.get("date_range") and metric not in {"farm_count", "flock_count"}:
                account[metric] = self._metric_by_id(
                    metric,
                    farm_id=None,
                    flock_id=None,
                    date_range=spec.get("date_range"),
                )
                continue
            safe_question = self.ACCOUNT_TASKS.get(metric)
            if safe_question:
                account[metric] = self._safe_answer(safe_question, history=history)
        return account

    def _target_section(
        self,
        target_phrase: str,
        spec: dict,
        history: list | None,
        target_entity_type: str = "",
        entity_resolution=None,
    ) -> list[dict]:
        by_id_section = self._target_section_by_id(
            target_phrase,
            spec,
            target_entity_type=target_entity_type,
            entity_resolution=entity_resolution,
        )
        if by_id_section:
            return by_id_section

        metrics = []
        for metric in self._ordered_metrics(spec["metrics"]):
            if metric in {"farm_count", "flock_count"}:
                continue
            safe_question = self._target_question(metric, target_phrase)
            if safe_question:
                metrics.append(
                    {
                        "metric": metric,
                        "response": self._safe_answer(safe_question, history=history),
                    }
                )
        return [{"target": target_phrase, "metrics": metrics}]

    def _target_section_by_id(
        self,
        target_phrase: str,
        spec: dict,
        *,
        target_entity_type: str,
        entity_resolution=None,
    ) -> list[dict]:
        if not target_entity_type or not entity_resolution:
            return []

        farm_id = getattr(entity_resolution, "farm_id", None)
        flock_id = getattr(entity_resolution, "flock_id", None)
        if target_entity_type == "flock" and not flock_id:
            return []
        if target_entity_type == "farm" and not farm_id:
            return []

        detail = self._target_detail_by_id(target_entity_type, farm_id, flock_id)
        target = (
            detail.get(f"{target_entity_type}_name")
            or target_phrase
            or f"selected {target_entity_type}"
        )
        metrics = self._entity_metrics(
            spec,
            farm_id=farm_id,
            flock_id=flock_id if target_entity_type == "flock" else None,
            history=None,
            date_range=spec.get("date_range"),
        )
        return [
            {
                "target": target,
                "entity_type": target_entity_type,
                "details": detail,
                "metrics": metrics,
            }
        ]

    def _target_detail_by_id(
        self, target_entity_type: str, farm_id: int | None, flock_id: int | None
    ) -> dict:
        try:
            if target_entity_type == "flock":
                plan = self.deterministic_service._flock_list_plan(
                    farm_id=farm_id,
                    flock_id=flock_id,
                )
            else:
                plan = self.deterministic_service._farm_list_plan(farm_id=farm_id)
            rows = self.deterministic_service.executor.execute(plan)
            return self._json_safe(rows[0]) if rows else {}
        except Exception:
            logger.exception("Target detail fetch failed")
            return {}

    def _farm_breakdown(self, spec: dict, history: list | None) -> list[dict]:
        rows = self._list_rows("farm")[: self.MAX_BREAKDOWN_ITEMS]
        return [
            {
                "details": self._json_safe(row),
                "metrics": self._entity_metrics(
                    spec,
                    farm_id=row.get("farm_id"),
                    flock_id=None,
                    history=history,
                    date_range=spec.get("date_range"),
                ),
            }
            for row in rows
        ]

    def _flock_breakdown(
        self, spec: dict, history: list | None, farm_id: int | None = None
    ) -> list[dict]:
        rows = self._list_rows("flock", farm_id=farm_id)[: self.MAX_BREAKDOWN_ITEMS]
        return [
            {
                "details": self._json_safe(row),
                "metrics": self._entity_metrics(
                    spec,
                    farm_id=row.get("farm_id"),
                    flock_id=row.get("flock_id"),
                    history=history,
                    date_range=spec.get("date_range"),
                ),
            }
            for row in rows
        ]

    def _entity_metrics(
        self,
        spec: dict,
        *,
        farm_id: int | None,
        flock_id: int | None,
        history: list | None,
        date_range=None,
    ) -> dict:
        metrics = {}
        for metric in self._ordered_metrics(spec["metrics"]):
            if metric in {"farm_count", "flock_count"}:
                continue
            response = self._metric_by_id(
                metric,
                farm_id=farm_id,
                flock_id=flock_id,
                date_range=date_range,
            )
            if response:
                metrics[metric] = response
        return metrics

    def _metric_by_id(
        self,
        metric: str,
        *,
        farm_id: int | None,
        flock_id: int | None,
        date_range=None,
    ) -> dict | None:
        try:
            plan = self._plan_for_metric(
                metric,
                farm_id=farm_id,
                flock_id=flock_id,
                date_range=date_range,
            )
            if not plan:
                return None
            rows = self.deterministic_service.executor.execute(plan)
            answer = self.deterministic_service._format_answer(plan, rows)
            return {
                "metric": metric,
                "answer": answer,
                "data": self.deterministic_service._response_data(plan, rows),
                "rows": self._json_safe(rows),
                "status": "success",
            }
        except Exception as exc:
            logger.exception("Multi-report metric failed")
            return {
                "metric": metric,
                "answer": f"I could not safely calculate {metric.replace('_', ' ')} for this item.",
                "data": None,
                "rows": [],
                "status": "error",
                "details": str(exc),
            }

    def _plan_for_metric(
        self,
        metric: str,
        *,
        farm_id: int | None,
        flock_id: int | None,
        date_range=None,
    ):
        service = self.deterministic_service
        if metric == "sales":
            return service._aggregate_plan(
                "ai_sale_data_view",
                "COALESCE(SUM(sale_amount), 0)",
                "total_sales",
                "money",
                farm_id=farm_id,
                flock_id=flock_id,
                date_column="sale_date",
                date_range=date_range,
            )
        if metric == "purchases":
            return service._aggregate_plan(
                "ai_purchase_data_view",
                "COALESCE(SUM(purchase_amount), 0)",
                "total_purchases",
                "money",
                farm_id=farm_id,
                flock_id=flock_id,
                date_column="purchase_date",
                date_range=date_range,
            )
        if metric == "profit":
            return service._profit_plan(farm_id, flock_id, date_range=date_range)
        if metric == "current_birds":
            return service._current_birds_plan(
                farm_id,
                flock_id,
                date_range=date_range,
            )
        if metric == "mortality":
            return service._aggregate_plan(
                "ai_dailydata_data_view",
                "COALESCE(SUM(birds_died), 0)",
                "mortality",
                "count",
                farm_id=farm_id,
                flock_id=flock_id,
                date_column="record_date",
                date_range=date_range,
            )
        if metric == "feed":
            return service._aggregate_plan(
                "ai_dailydata_data_view",
                "COALESCE(SUM(feed_consumed_kg), 0)",
                "feed_consumed",
                "quantity",
                farm_id=farm_id,
                flock_id=flock_id,
                date_column="record_date",
                date_range=date_range,
            )
        if metric == "weight":
            return service._aggregate_plan(
                "ai_dailydata_data_view",
                "COALESCE(AVG(average_bird_weight), 0)",
                "average_weight",
                "decimal",
                farm_id=farm_id,
                flock_id=flock_id,
                date_column="record_date",
                date_range=date_range,
            )
        if metric == "fcr":
            return service._aggregate_plan(
                "ai_dailydata_data_view",
                "COALESCE(AVG(fcr), 0)",
                "fcr",
                "decimal",
                farm_id=farm_id,
                flock_id=flock_id,
                date_column="record_date",
                date_range=date_range,
            )
        return None

    def _list_rows(
        self,
        label: str,
        *,
        farm_id: int | None = None,
        flock_id: int | None = None,
    ) -> list[dict]:
        try:
            if label == "farm":
                plan = self.deterministic_service._farm_list_plan(farm_id=farm_id)
            else:
                plan = self.deterministic_service._flock_list_plan(
                    farm_id=farm_id,
                    flock_id=flock_id,
                )
            return self.deterministic_service.executor.execute(plan)
        except Exception:
            logger.exception("Multi-report list fetch failed")
            return []

    def _safe_answer(self, safe_question: str, history: list | None) -> dict:
        try:
            response = self.deterministic_service.answer(safe_question, history=history)
            return {
                "question": safe_question,
                "metric": response.get("metric"),
                "answer": response.get("answer") or response.get("message"),
                "data": self._json_safe(response.get("data")),
                "rows": self._json_safe(response.get("rows") or []),
                "status": response.get("status"),
            }
        except Exception as exc:
            logger.exception("Multi-report safe task failed")
            return {
                "question": safe_question,
                "metric": "error",
                "answer": f"I could not safely answer: {safe_question}.",
                "data": None,
                "rows": [],
                "status": "error",
                "details": str(exc),
            }

    def _format_report(self, report: dict) -> str:
        lines = ["Here is the combined report from your Chikooza records."]
        account_lines = self._format_account(report.get("account") or {})
        if account_lines:
            lines.append("\nAccount totals:")
            lines.extend(account_lines)

        target_lines = self._format_target(report.get("target") or [])
        if target_lines:
            lines.append("\nSelected item:")
            lines.extend(target_lines)

        farm_lines = []
        if (report.get("requested_sections") or {}).get("farms"):
            farm_lines = self._format_entity_breakdown(
                "farm", report.get("farms") or []
            )
        if farm_lines:
            lines.append("\nFarm-wise details:")
            lines.extend(farm_lines)

        flock_lines = []
        if (report.get("requested_sections") or {}).get("flocks"):
            flock_lines = self._format_entity_breakdown(
                "flock", report.get("flocks") or []
            )
        if flock_lines:
            lines.append("\nFlock-wise details:")
            lines.extend(flock_lines)

        if len(lines) == 1:
            lines.append(
                "I could not find enough saved farm data to build this report."
            )
        return "\n".join(lines)

    def _format_account(self, account: dict) -> list[str]:
        lines = []
        for metric in self._ordered_metrics(account.keys()):
            answer = self._friendly_answer(metric, account.get(metric))
            if answer:
                lines.append(f"- {answer}")
        return lines

    def _format_target(self, targets: list[dict]) -> list[str]:
        lines = []
        for target in targets:
            entity_type = target.get("entity_type") or ""
            details = target.get("details") or {}
            description = (
                self._entity_description(entity_type, details)
                if entity_type in {"farm", "flock"}
                else ""
            )
            lines.append(
                f"- {target.get('target')}:"
                f"{f' {description}' if description else ''}"
            )
            metrics = target.get("metrics") or []
            if isinstance(metrics, dict):
                iterable = [
                    {"metric": metric, "response": response}
                    for metric, response in metrics.items()
                ]
            else:
                iterable = metrics
            for item in iterable:
                answer = self._friendly_answer(item.get("metric"), item.get("response"))
                if answer:
                    lines.append(f"  {answer}")
        return lines

    def _format_entity_breakdown(self, label: str, items: list[dict]) -> list[str]:
        if not items:
            return [f"- No {label}s found in your account."]

        lines = []
        for index, item in enumerate(items, start=1):
            details = item.get("details") or {}
            name = details.get(f"{label}_name") or f"{label.title()} {index}"
            description = self._entity_description(label, details)
            lines.append(
                f"- {index}. {name}{f' - {description}' if description else ''}"
            )

            metric_answers = [
                self._friendly_answer(metric, response)
                for metric, response in (item.get("metrics") or {}).items()
                if self._friendly_answer(metric, response)
            ]
            if metric_answers:
                lines.append(f"  {' '.join(metric_answers)}")
        return lines

    def _entity_description(self, label: str, details: dict) -> str:
        if label == "farm":
            parts = [
                details.get("farm_city"),
                (
                    f"{details.get('shed_count')} sheds"
                    if details.get("shed_count") not in (None, "")
                    else ""
                ),
                "active" if details.get("farm_status") else "inactive",
            ]
            return ", ".join(str(part) for part in parts if part)

        parts = [
            f"farm: {details.get('farm_name')}" if details.get("farm_name") else "",
            f"size: {details.get('flock_size')}" if details.get("flock_size") else "",
            (
                f"actual birds: {details.get('actual_birds')}"
                if details.get("actual_birds") not in (None, "")
                else ""
            ),
            (
                f"hatch date: {details.get('hatch_date')}"
                if details.get("hatch_date")
                else ""
            ),
            f"breed: {details.get('breed_name')}" if details.get("breed_name") else "",
        ]
        return ", ".join(part for part in parts if part)

    def _target_question(self, metric: str, target_phrase: str) -> str | None:
        task = self.ACCOUNT_TASKS.get(metric)
        if not task:
            return None
        return f"{task} for {target_phrase}"

    def _target_phrase(self, intent) -> str:
        if not intent:
            return ""
        entity_type = getattr(intent, "entity_type", "") or ""
        reference = (getattr(intent, "entity_reference", "") or "").strip()
        if not entity_type:
            return ""
        if reference in {"", "current"}:
            # U: OLD: broad multi-part questions like "how many farms and
            # U: flocks do I have" produced a fake "Selected item: the flock".
            # U: NEW: only create a target section when the farmer gave a real
            # U: target such as first/that/exact farm/flock.
            return ""
        if reference in {
            "it",
            "that",
            "this",
            "same",
            "same one",
            "this one",
            "that one",
        }:
            return f"the {entity_type}"
        if reference in {"last", "last one"}:
            return f"last {entity_type}"
        if reference == "other":
            return f"other {entity_type}"
        if reference in {"first", "second", "third", "fourth", "fifth"}:
            return f"{reference} {entity_type}"
        return f"{entity_type} {reference}"

    def _target_entity_type(self, intent, entity_resolution=None) -> str:
        entity_type = (getattr(intent, "entity_type", "") or "").strip()
        if entity_type in {"farm", "flock"}:
            if entity_resolution and (
                getattr(entity_resolution, "farm_id", None)
                or getattr(entity_resolution, "flock_id", None)
            ):
                return entity_type
            if self._intent_has_specific_target(intent):
                return entity_type
        return ""

    def _intent_has_specific_target(self, intent) -> bool:
        if not intent:
            return False
        reference = (getattr(intent, "entity_reference", "") or "").strip()
        return bool(reference and reference != "other")

    def _has_singular_target(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:for|inside|about|of|in)\s+(?:the\s+|my\s+|our\s+)?[a-z0-9 ]*\b(?:farm|flock|batch)\b",
                query,
            )
        )

    def _ordered_metrics(self, metrics) -> list[str]:
        order = (
            "farm_count",
            "flock_count",
            "sales",
            "purchases",
            "profit",
            "current_birds",
            "mortality",
            "feed",
            "weight",
            "fcr",
        )
        metric_set = set(metrics)
        return [metric for metric in order if metric in metric_set]

    def _wants_all_metrics(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:all their stuff|all the stuff|all stuff|all data|all the data|all my data|my all data|"
                r"all details|all records|all information|everything|full data|complete data|"
                r"complete records|inside each|inside every|each of the|every farm|every flock|"
                r"individually|individual|full report|complete report)\b",
                query,
            )
            or re.search(
                r"\b(?:all|complete|full)\s+(?:my\s+|our\s+)?"
                r"(?:farms?|flocks?|batches?)\s+"
                r"(?:data|records|details|information|stuff|things)\b",
                query,
            )
        )

    def _wants_breakdown(self, query: str, label: str) -> bool:
        plural = "flocks|batches" if label == "flock" else "farms"
        return bool(
            re.search(
                rf"\b(?:each|every|individual|individually|inside|inside each|inside every|per|by)\s+(?:of\s+the\s+)?(?:{label}|{plural})\b",
                query,
            )
            or re.search(rf"\b(?:{label}|{plural})[- ]wise\b", query)
            or "all their stuff" in query
        )

    def _mentions_count(self, query: str) -> bool:
        return bool(
            re.search(
                r"\b(?:how many|number of|total number|total no|no of|count)\b", query
            )
        )

    def _date_range_from_query(self, query: str):
        parser = getattr(self.deterministic_service, "_date_range_from_query", None)
        if not parser:
            return None
        return parser(query)

    def _answer_text(self, response: dict | None) -> str:
        return str((response or {}).get("answer") or "").strip()

    def _friendly_answer(self, metric: str | None, response: dict | None) -> str:
        answer = self._answer_text(response)
        if not answer:
            return ""

        if metric == "profit":
            value = self._numeric_value(response)
            if value is not None:
                status = (
                    "profit" if value > 0 else "loss" if value < 0 else "break-even"
                )
                return f"Profit/Loss: Rs. {value:,.2f} ({status})."
        if metric == "fcr":
            return answer.replace("Fcr:", "Average FCR:")
        if metric == "weight":
            return answer.replace("Average Weight:", "Average weight:")
        return answer

    def _numeric_value(self, response: dict | None) -> float | None:
        data = (response or {}).get("data")
        if isinstance(data, dict):
            data = data.get("result")
        try:
            return float(data)
        except (TypeError, ValueError):
            return None

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").lower()).strip()

    def _json_safe(self, value):
        if all(hasattr(value, attr) for attr in ("start", "end", "label")):
            return {
                "start": self._json_safe(value.start),
                "end": self._json_safe(value.end),
                "label": value.label,
            }
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(item) for item in value]
        return value
