"""Run and persist the 60-case synthetic Gemini diagnosis evaluation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings
from services.recovery.evaluation import run_diagnosis_evaluation, save_evaluation


if __name__ == "__main__":
    result = run_diagnosis_evaluation()
    save_evaluation(settings.diagnosis_evaluation_path, result)
    print(f"Saved {result['total_cases']}-case evaluation: {result['accuracy']}% accuracy; {result['fallback_count']} fallback(s)")
