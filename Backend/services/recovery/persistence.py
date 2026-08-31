"""Durable single-node storage for the recovery demo/workspace.

This keeps the proven RecoveryStore domain logic intact while persisting its
state atomically in SQLite. It is intentionally small and dependency-free;
multi-tenant production deployments should replace it with Postgres + RLS.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from services.recovery.engine import RecoveryStore


class SQLiteRecoveryStore(RecoveryStore):
    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self._path, check_same_thread=False)
        self._connection.execute("create table if not exists recovery_state (id integer primary key check (id = 1), payload text not null)")
        saved = self._connection.execute("select payload from recovery_state where id = 1").fetchone()
        if saved:
            payload = json.loads(saved[0])
            self._cases = payload.get("cases", self._cases)
            self._call_summaries = payload.get("call_summaries", [])
        else:
            self._persist()

    def _persist(self) -> None:
        payload = json.dumps({"cases": self._cases, "call_summaries": self._call_summaries}, separators=(",", ":"))
        with self._connection:
            self._connection.execute("insert into recovery_state (id, payload) values (1, ?) on conflict(id) do update set payload=excluded.payload", (payload,))

    def reset(self) -> Dict[str, Any]:
        result = super().reset(); self._persist(); return result

    def activate_scenario(self, scenario_id: str) -> Dict[str, Any]:
        result = super().activate_scenario(scenario_id); self._persist(); return result

    def execute_action(self, case_id: str) -> Dict[str, Any]:
        result = super().execute_action(case_id); self._persist(); return result

    def apply_diagnosis(self, case_id: str, diagnosis: Dict[str, Any], customer_text: str) -> Dict[str, Any]:
        result = super().apply_diagnosis(case_id, diagnosis, customer_text); self._persist(); return result

    def record_promise(self, case_id: str, customer_text: str, promise_date: Optional[str] = None) -> Dict[str, Any]:
        result = super().record_promise(case_id, customer_text, promise_date); self._persist(); return result

    def confirm_payment(self, case_id: str) -> Dict[str, Any]:
        result = super().confirm_payment(case_id); self._persist(); return result

    def receive_payment_webhook(self, case_id: str, provider_event_id: str, payment_id: str, amount: int) -> Dict[str, Any]:
        result = super().receive_payment_webhook(case_id, provider_event_id, payment_id, amount); self._persist(); return result

    def simulate_response(self, case_id: str, response_type: str) -> Dict[str, Any]:
        result = super().simulate_response(case_id, response_type); self._persist(); return result

    def simulate_call(self, case_id: str, response_type: str) -> Dict[str, Any]:
        result = super().simulate_call(case_id, response_type); self._persist(); return result

    def mark_failed_promises(self, as_of):
        result = super().mark_failed_promises(as_of); self._persist(); return result
