"""Minimal stand-in for OFTLY INTELLIGENCE, implementing contract oftly.intelligence/1 (docs/INTELLIGENCE_CONTRACT.md).
It is NOT intelligent: it nudges outfits that contain a navy piece, so you can see the integration working.
Run:  .venv/bin/python scripts/stub_intelligence.py      then start OFTLY with
      OFTLY_INTELLIGENCE_URL=http://127.0.0.1:9911 ./scripts/start.sh"""
import uvicorn
from fastapi import FastAPI, File, UploadFile

app = FastAPI(title="OFTLY intelligence stub")

@app.get("/v1/health")
def health():
    return {"name": "stub", "version": "0.0", "capabilities": ["rank_outfits", "suggest_attributes"]}

@app.post("/v1/rank_outfits")
def rank(body: dict):
    adj = []
    for o in body.get("outfits", []):
        if any(p.get("colour") == "navy" for p in o["pieces"]):
            adj.append({"id": o["id"], "delta": 3.0, "note": "Stub: navy pieces get a small boost."})
    return {"adjustments": adj}

@app.post("/v1/suggest_attributes")
async def suggest(image: UploadFile = File(...)):
    await image.read()
    return {"suggestions": [{"field": "pattern", "value": "solid", "confidence": 0.5}]}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9911, log_level="warning")
