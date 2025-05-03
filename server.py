from flask import Flask, request, render_template, jsonify
import hashlib
import requests

app = Flask(__name__)

API_KEY = "18f7539422d4"
SECRET_KEY = "cfdc2dc8ee"

def get_control_sum(vin):
    raw = API_KEY + SECRET_KEY + vin
    return hashlib.md5(raw.encode()).hexdigest()

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        vin = request.form["vin"]
        control_sum = get_control_sum(vin)
        url = f"https://api.vindecoder.eu/3.2/{API_KEY}/{control_sum}/decode/info/{vin}.json"
        response = requests.get(url)
        try:
            result = response.json()
        except:
            result = {"error": "Ошибка при разборе ответа"}
    return render_template("index.html", result=result)
