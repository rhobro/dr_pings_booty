from flask import Flask
from time import time as now

app = Flask(__name__)

@app.route("/test")
def sup_gang():
    return {
        "timestamp": now(),
        "msg": "yup, you poked me"
    }
