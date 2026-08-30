"""Public, fictional-data-only recovery demo endpoints.

These endpoints deliberately contain no production customer data and need no
Supabase/Twilio/LLM configuration. They make a reliable hackathon demo possible.
"""

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.recovery.engine import RecoveryStore, calculate_benchmark
from services.recovery.diagnosis import diagnose_customer_reply
from api.auth import require_recovery_admin, require_recovery_user

router = APIRouter(prefix="/api/recovery", tags=["AI Revenue Recovery Demo"], dependencies=[Depends(require_recovery_user)])
store = RecoveryStore()


class PromiseRequest(BaseModel):
    customer_text: str = Field(..., min_length=3, max_length=1000)
    promise_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class SimulatedResponseRequest(BaseModel):
    response_type: Literal["PAYMENT_CONFIRMED", "PROMISE_TO_PAY", "DISPUTE", "PAYMENT_FAILED", "NO_RESPONSE"]


class DiagnosisRequest(BaseModel):
    customer_text: str = Field(..., min_length=3, max_length=2000)


@router.get("/summary")
async def recovery_summary():
    return store.summary()


@router.get("/cases")
async def list_recovery_cases():
    return {"demo_data": True, "cases": store.list_cases()}


@router.get("/call-summaries")
async def list_demo_call_summaries():
    return {"demo_data": True, "data": store.list_call_summaries(), "total": len(store.list_call_summaries())}


@router.get("/scenarios")
async def list_recovery_scenarios():
    return {"demo_data": True, "scenarios": store.scenario_catalog()}


@router.post("/scenarios/{scenario_id}/activate", dependencies=[Depends(require_recovery_admin)])
async def activate_recovery_scenario(scenario_id: str):
    try:
        return store.activate_scenario(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery scenario not found")


@router.get("/cases/{case_id}")
async def get_recovery_case(case_id: str):
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    return case


@router.post("/demo/reset", dependencies=[Depends(require_recovery_admin)])
async def reset_recovery_demo():
    """Reset only the in-memory fictional records used by this demo."""
    return {
        "demo_data": True,
        "message": "Demo reset. The golden-path case is ready to run again.",
        "summary": store.reset(),
    }


@router.post("/cases/{case_id}/execute", dependencies=[Depends(require_recovery_admin)])
async def execute_recovery_action(case_id: str):
    try:
        return store.execute_action(case_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery case not found")


@router.post("/cases/{case_id}/diagnose", dependencies=[Depends(require_recovery_admin)])
async def diagnose_recovery_reply(case_id: str, payload: DiagnosisRequest):
    case = store.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    diagnosis = diagnose_customer_reply(payload.customer_text, case.get("cause", "unknown"))
    return store.apply_diagnosis(case_id, diagnosis, payload.customer_text)


@router.post("/cases/{case_id}/promise", dependencies=[Depends(require_recovery_admin)])
async def record_promise_to_pay(case_id: str, payload: PromiseRequest):
    try:
        return store.record_promise(case_id, payload.customer_text, payload.promise_date)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/cases/{case_id}/payment-confirmed", dependencies=[Depends(require_recovery_admin)])
async def confirm_payment(case_id: str):
    try:
        return store.confirm_payment(case_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery case not found")


@router.post("/cases/{case_id}/simulate-response", dependencies=[Depends(require_recovery_admin)])
async def simulate_customer_response(case_id: str, payload: SimulatedResponseRequest):
    try:
        return store.simulate_response(case_id, payload.response_type)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/cases/{case_id}/simulate-call", dependencies=[Depends(require_recovery_admin)])
async def simulate_recovery_call(case_id: str, payload: SimulatedResponseRequest):
    try:
        return store.simulate_call(case_id, payload.response_type)
    except KeyError:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/demo/advance-promises", dependencies=[Depends(require_recovery_admin)])
async def advance_failed_promises(as_of: str = "2026-09-05"):
    try:
        affected = store.mark_failed_promises(date.fromisoformat(as_of))
    except ValueError:
        raise HTTPException(status_code=422, detail="as_of must be an ISO date")
    return {"affected_cases": affected, "as_of": as_of}


@router.get("/benchmark")
async def recovery_benchmark():
    return calculate_benchmark(store.list_cases())
