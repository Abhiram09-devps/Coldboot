from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")

# ---------------------------------------------------------------------------
# CTF credentials
# ---------------------------------------------------------------------------
VALID_USER = "admin"
VALID_PASS = "R3tr0Gam3r!2026"

# The credentials above, XOR'd against the key "c0ldboot" and base64-encoded.
# This is what actually lives at the hidden /backup endpoint. The XOR key
# itself is hidden separately, in an HTML comment on the login page
# (view-source is fair game; the endpoint itself is what gobuster is for).
XOR_KEY = "c0ldboot"
ENCODED_BACKUP = "AlQBDQxVPUcXQlwjAwJcBkICXFZU"

# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
# Only /login and the static assets are reachable while unauthenticated.
# /backup is ALSO intentionally reachable unauthenticated -- it's not linked
# from any page, so the only way to find it is by directory brute-forcing
# (gobuster/dirb/ffuf). That's the whole point of the challenge: recon before
# you can even log in.
PUBLIC_PATHS = {"/login", "/backup"}
PUBLIC_PREFIXES = ("/static/",)


@app.before_request
def require_login():
    path = request.path
    if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
        return
    if not session.get("authenticated"):
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == VALID_USER and password == VALID_PASS:
            session["authenticated"] = True
            return redirect(url_for("index"))
        error = "ACCESS DENIED — INVALID CREDENTIALS."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/backup")
def backup():
    """Hidden ops-backup endpoint. Not linked anywhere in the UI."""
    return jsonify({
        "note": "nightly ops backup - scheduled for deletion, do not index",
        "generated": "2026-07-30T02:14:00Z",
        "payload_encoding": "xor+base64",
        "user_backup": ENCODED_BACKUP,
    })


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
