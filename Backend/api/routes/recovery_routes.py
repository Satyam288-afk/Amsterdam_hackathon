"""Public, fictional-data-only recovery demo endpoints.

These endpoints deliberately contain no production customer data and need no
Supabase/Twilio/LLM configuration. They make a reliable hackathon demo possible.
"""

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.recovery.engine import RecoveryStore, calculate_benchmark

router = APIRouter(prefix="/api/recovery", tags=["AI Revenue Recovery Demo"])
store = RecoveryStore()


class PromiseRequest(BaseModel):
    customer_text: str = Field(..., min_length=3, max_length=1000)
    promise_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class SimulatedResponseRequest(BaseModel):
    response_type: Literal["PAYMENT_CONFIRMED", "PROMISE_TO_PAY", "DISPUTE", "PAYMENT_FAILED", "NO_RESPONSE"]


@router.get("/summary")
async def recovery_summary():
    return store.summary()


@router.get("/cases")
async def list_recovery_cases():
    return {"demo_data": True, "cases": store.list_cases()}


@router.get("/cases/{case_id}")
async def get_recovery_case(case_id: str):
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    return case


@router.post("/cases/{case_id}/execute")
async def execute_recovery_action(case_id: str):
    try:
        return store.execute_action(case_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery case not found")


@router.post("/cases/{case_id}/promise")
async def record_promise_to_pay(case_id: str, payload: PromiseRequest):
    try:
        return store.record_promise(case_id, payload.customer_text, payload.promise_date)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/cases/{case_id}/payment-confirmed")
async def confirm_payment(case_id: str):
    try:
        return store.confirm_payment(case_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery case not found")


@router.post("/cases/{case_id}/simulate-response")
async def simulate_customer_response(case_id: str, payload: SimulatedResponseRequest):
    try:
        return store.simulate_response(case_id, payload.response_type)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/demo/advance-promises")
async def advance_failed_promises(as_of: str = "2026-09-05"):
    try:
        affected = store.mark_failed_promises(date.fromisoformat(as_of))
    except ValueError:
        raise HTTPException(status_code=422, detail="as_of must be an ISO date")
    return {"affected_cases": affected, "as_of": as_of}


@router.get("/benchmark")
async def recovery_benchmark():
    return calculate_benchmark(store.list_cases())
