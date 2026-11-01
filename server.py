from flask import Flask, request, render_template
import hashlib
import os
import requests

app = Flask(__name__)

API_KEY = os.getenv("VINDECODER_API_KEY", "")
SECRET_KEY = os.getenv("VINDECODER_SECRET_KEY", "")


def get_control_sum(vin: str) -> str:
    raw = API_KEY + SECRET_KEY + vin
    return hashlib.md5(raw.encode()).hexdigest()


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        vin = request.form["vin"].strip().upper()
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
    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
