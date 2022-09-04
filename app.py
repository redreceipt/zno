import os
from flask import Flask, escape, render_template, request, flash

from zno import getInfo

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or b'_5#y2L"F4Q8z\n\xec]/'


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html")
    else:
        info = getInfo(request.form["query"], verbose=True)
        if not len(info.keys()):
            flash("No title found")
            return render_template("index.html")
        app.logger.debug(info)
        return render_template("title.html", info=info)


# TODO authenticate this
@app.route("/api/title/<title>")
def titleAPI(title):
    return getInfo(escape(title), verbose=True)


@app.errorhandler(404)
def notFound(error):
    app.logger.debug(request.url)
    app.logger.error(error)
    return "page not found", 404
