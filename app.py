from flask import Flask
from time import time as now
import os

app = Flask(__name__)

@app.route("/test")
def test():
    return {
        "timestamp": now(),
        "msg": "yes, your request reached me"
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))