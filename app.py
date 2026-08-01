from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
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
# IMPORTANT: this is a decorator applied only to routes that actually exist,
# not a blanket before_request. A blanket "redirect everything to /login"
# rule would make every URL -- real or made-up -- return the same 302,
# which breaks directory brute-forcing tools (gobuster/dirb/ffuf all treat
# that as a wildcard response and refuse to give useful results). By only
# gating real routes, nonexistent paths fall through to Flask's normal 404,
# so gobuster can actually tell /backup apart from noise.
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


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
@login_required
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
