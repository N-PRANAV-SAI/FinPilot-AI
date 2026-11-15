import sys
import time
from pathlib import Path

workspace = Path(r"C:\Users\Pranav\Downloads\FinPilot-AI\FinPilot-AI")
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))

from backend.api.main import analyze

print("Starting end-to-end analyze('AAPL')...")
t0 = time.time()
res = analyze("AAPL")
duration = time.time() - t0

print(f"\nAnalysis completed successfully in {duration:.2f} seconds!")
print(f"Company: {res.get('company_name')} ({res.get('ticker')}) - {res.get('exchange')} [{res.get('country')}]")
print(f"Selected Quant Model: {res.get('quant_models', {}).get('selected_model')}")
print(f"Prediction: {res.get('prediction', {}).get('direction')} ({res.get('prediction', {}).get('probability', 0)*100:.1f}%)")
print(f"Sentiment: {res.get('sentiment', {}).get('overall_label')} (Score: {res.get('sentiment', {}).get('score', 0):.2f})")
if res.get('hybrid_models'):
    print(f"Hybrid Model Available: {res.get('hybrid_models', {}).get('selected_model')}")
else:
    print("Hybrid Model: No news sentiment features available to train hybrid model")
if res.get('shap'):
    pos = [f"{x['feature']} (+{x['contribution']:.4f})" for x in res['shap'].get('top_positive', [])[:3]]
    neg = [f"{x['feature']} ({x['contribution']:.4f})" for x in res['shap'].get('top_negative', [])[:3]]
    print(f"SHAP Top Bullish: {', '.join(pos)}")
    print(f"SHAP Top Bearish: {', '.join(neg)}")
print(f"Filings Retrieved: {len(res.get('filings', []))}")
print(f"LLM Synthesis length: {len(res.get('llm_explanation', ''))} characters")
