from flask import Flask

from zno import getInfo

app = Flask(__name__)


@app.route('/')
def index():
    info = getInfo("braveheart")
    return info
