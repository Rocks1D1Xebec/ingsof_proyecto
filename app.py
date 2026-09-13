import os

from flask import Flask, abort, send_file, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)


@app.route("/")
def index():
    return send_file(os.path.join(BASE_DIR, "index.html"))


@app.route("/<path:filename>")
def archivos(filename):
    if filename.startswith("css/"):
        ruta = os.path.join(BASE_DIR, filename)
        if os.path.isfile(ruta):
            return send_from_directory(BASE_DIR, filename)
        abort(404)
    if filename.endswith(".html"):
        ruta = os.path.join(BASE_DIR, filename)
        if os.path.isfile(ruta):
            return send_from_directory(BASE_DIR, filename)
        abort(404)
    abort(404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)