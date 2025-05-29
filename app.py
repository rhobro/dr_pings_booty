from flask import Flask
from time import time as now
import os

app = Flask(__name__)

@app.route("/test")
def sup_gang():
    return {
        "timestamp": now(),
        "msg": "yup, you poked me"
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))