import subprocess
from flask import Flask, render_template, request, redirect

from piframe.wifi.manager import save_network, scan_visible_ssids


def create_portal_app() -> Flask:
    app = Flask(__name__, template_folder="templates")

    @app.route("/")
    def index():
        visible = scan_visible_ssids()
        ssids = sorted(visible.keys())
        return render_template("setup.html", ssids=ssids)

    @app.route("/save", methods=["POST"])
    def save():
        ssid = request.form.get("ssid", "").strip()
        psk = request.form.get("psk", "").strip()
        if not ssid:
            return redirect("/")
        save_network(ssid, psk)
        return render_template("setup.html", ssids=[], saved=True)

    return app
