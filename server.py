from flask import Flask, request, render_template, jsonify
import hashlib
import json
import os
from pathlib import Path
import requests
from analytics.valuation import evaluate

app = Flask(__name__)

API_KEY = os.getenv("VINDECODER_API_KEY", "")
SECRET_KEY = os.getenv("VINDECODER_SECRET_KEY", "")
DATA_PATH = Path(os.getenv("SHM_MARKET_JSON", "data/latest_market.json"))


def get_control_sum(vin: str) -> str:
    raw = API_KEY + SECRET_KEY + vin
    return hashlib.md5(raw.encode()).hexdigest()


@app.route("/", methods=["GET", "POST"])
def index():
    # Keep the old VIN helper available, but Market Center is now the main SHM tool.
    if request.method == "GET":
        return render_template("market_center.html")

    result = None
    vin = request.form.get("vin", "").strip().upper()
    if not API_KEY or not SECRET_KEY:
        result = {"error": "VIN decoder credentials are not configured"}
    else:
        control_sum = get_control_sum(vin)
        url = f"https://api.vindecoder.eu/3.2/{API_KEY}/{control_sum}/decode/info/{vin}.json"
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            result = response.json()
        except Exception as exc:
            result = {"error": f"VIN decoder request failed: {exc}"}
    return jsonify(result)


@app.get("/market")
def market_center():
    return render_template("market_center.html")


@app.get("/api/market-center")
def market_center_data():
    try:
        return jsonify(json.loads(DATA_PATH.read_text(encoding="utf-8")))
    except Exception as exc:
        return jsonify({
            "updated_at": None,
            "stats": {},
            "coverage": [],
            "listings": [],
            "error": f"market data unavailable: {exc}",
        }), 503


@app.get("/api/market-segment")
def market_segment_api():
    try:
        data=json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return jsonify({"error": f"market data unavailable: {exc}"}),503

    brand=request.args.get("brand")
    year=request.args.get("year",type=int)
    body=request.args.get("body_type")
    rows=[]
    for x in data.get("listings",[]):
        if (x.get("asset_type") or "semi_trailer")!="semi_trailer":
            continue
        if brand and x.get("brand")!=brand:
            continue
        if year and x.get("year")!=year:
            continue
        if body and (x.get("body_type") or "other")!=body:
            continue
        rows.append(x)

    seg=None
    if brand and year and body:
        seg=next((s for s in data.get("segments",[]) if s.get("brand")==brand and s.get("year")==year and s.get("body_type")==body),None)

    priced=[x for x in rows if isinstance(x.get("price_original"),(int,float))]
    priced.sort(key=lambda x:x.get("price_original"))
    return jsonify({
        "filters":{"brand":brand,"year":year,"body_type":body},
        "count":len(rows),
        "priced_count":len(priced),
        "segment":seg,
        "sources":len({x.get("source") for x in rows if x.get("source")}),
        "countries":len({x.get("country") for x in rows if x.get("country")}),
        "fresh_count":sum(bool(x.get("seen_this_run")) for x in rows),
        "lowest":priced[:10],
        "highest":priced[-10:],
    })


@app.post("/api/private/evaluate")
def private_evaluate():
    token = os.getenv("SHM_PRIVATE_TOKEN", "")
    auth = request.headers.get("Authorization", "")
    if not token or auth != f"Bearer {token}":
        return jsonify({"error": "private valuation unavailable"}), 403
    payload = request.get_json(silent=True) or {}
    target = payload.get("target") or {}
    return jsonify(evaluate(
        target,
        transport_to_wyhl_eur=payload.get("transport_to_wyhl_eur"),
        post_arrival_costs_eur=payload.get("post_arrival_costs_eur"),
        target_profit_eur=payload.get("target_profit_eur"),
    ))


@app.get("/health")
def health():
    return jsonify({"ok": True, "market_data_exists": DATA_PATH.exists()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
