from flask import Flask, escape, request

from zno import getInfo

app = Flask(__name__)


@app.route('/')
def index():
    return "search page"


@app.route('/title/<title>')
def title(title, method=["GET", "POST"]):
    app.logger.debug(f"{request.url}")
    if request.method == 'GET':
        return getInfo(escape(title))
    else:
        return getInfo(request.form["search"])


@app.route('/api/<title>')
def api(title):
    app.logger.debug(f"{request.url}")
    return getInfo(escape(title))


@app.errorhandler(404)
def notFound(error):
    app.logger.error(f"404 error: {error}")
    return "page not found", 404
