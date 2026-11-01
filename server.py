from flask import Flask, request, render_template, jsonify
import hashlib
import json
import os
from pathlib import Path
import requests

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


@app.get("/health")
def health():
    return jsonify({"ok": True, "market_data_exists": DATA_PATH.exists()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
