from flask import Flask, escape, redirect, render_template, request, url_for

from zno import getInfo

app = Flask(__name__)


@app.route('/')
def index():
    return redirect(url_for('search'))


@app.route('/search', methods=["GET", "POST"])
def search():
    if request.method == 'GET':
        return render_template("search.html")
    else:
        return redirect(url_for('title', title=request.form["query"]))


# TODO rebuild URL to correct title
@app.route("/title/<title>")
def title(title):
    app.logger.debug(request.url)
    info = getInfo(title)
    app.logger.debug(info)
    return render_template("title.html", info=info)


# TODO authenticate this
@app.route('/api/title/<title>')
def titleAPI(title):
    app.logger.debug(request.url)
    return getInfo(escape(title))


@app.errorhandler(404)
def notFound(error):
    app.logger.debug(request.url)
    app.logger.error(error)
    return "page not found", 404
