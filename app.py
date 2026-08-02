from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, get_flashed_messages
from functools import wraps
import os
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
# `or` (not the second arg to .get()) so this falls back correctly whether
# SECRET_KEY is missing entirely OR present-but-empty (e.g. a blank field
# in a hosting dashboard). Flask refuses to touch sessions at all if
# secret_key ends up falsy, which is exactly what caused the "no secret
# key was set" 500 error.
app.secret_key = os.environ.get("SECRET_KEY") or "coldboot-ctf-fallback-secret-change-me"

# ---------------------------------------------------------------------------
# CTF credentials
# ---------------------------------------------------------------------------
VALID_USER = "admin"
VALID_PASS = "R3tr0Gam3r!2026"

# The credentials above, XOR'd against the key "c0ldboot" and base64-encoded.
# This lives at the REAL hidden endpoint (see /coldsync-ops below).
#
# The key "c0ldboot" is intentionally split across two separate discovery
# techniques so the player needs both:
#   1. view-source on /login -> HTML comment gives the prefix "c0ld"
#   2. inspect /login's response headers -> X-Ops-Seed-Suffix gives "boot"
# Concatenating them reconstructs "c0ldboot".
XOR_KEY = "c0ldboot"
ENCODED_BACKUP = "AlQBDQxVPUcXQlwjAwJcBkICXFZU"

# ---------------------------------------------------------------------------
# Challenge 2: the flag hidden via steghide in the RUSTBELT cover image.
# ---------------------------------------------------------------------------
FLAG = "FLAG{st3gh1dden_1n_th3_rustb3lt_c0v3r}"
NOTIFY_EMAIL = "abhiram.aofficial09@gmail.com"

# SMTP credentials for sending the "team solved it" notification email.
# Set these as environment variables -- see README.md for how to generate
# a Gmail App Password. If they're not set, email sending is skipped
# (submission still succeeds, it just won't notify anyone).
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")


def send_solve_notification(team_name, team_email):
    """Best-effort email notification. Never lets an email failure block
    a correct flag submission -- the player still gets their congrats
    page even if SMTP isn't configured or the send fails."""
    if not SMTP_USER or not SMTP_PASS:
        app.logger.warning("SMTP not configured -- skipping notification email")
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = f"COLDBOOT CTF — flag captured by {team_name}"
        msg["From"] = SMTP_USER
        msg["To"] = NOTIFY_EMAIL
        msg.set_content(
            f"Team name: {team_name}\n"
            f"Team email: {team_email}\n"
            f"Flag submitted: {FLAG}\n"
        )
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    except Exception as e:
        app.logger.error(f"Failed to send solve notification email: {e}")

# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
# IMPORTANT: this is a decorator applied only to routes that actually exist,
# not a blanket before_request. A blanket "redirect everything to /login"
# rule would make every URL -- real or made-up -- return the same 302,
# which breaks directory brute-forcing tools (gobuster/dirb/ffuf all treat
# that as a wildcard response and refuse to give useful results). By only
# gating real routes, nonexistent paths fall through to Flask's normal 404,
# so gobuster can actually tell real hits apart from noise.
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
    response = app.make_response(render_template("login.html", error=error))
    # Second half of the XOR key -- deliberately only visible via response
    # headers (curl -i, browser devtools Network tab), not view-source.
    response.headers["X-Ops-Seed-Suffix"] = "boot"
    return response


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Decoys -- these exist so the obvious first guesses ("backup" is in every
# stock wordlist) cost the player a little time without handing them
# anything real. Each one is a genuine 200, not a 404, so they show up in
# a gobuster scan just like the real endpoint does.
# ---------------------------------------------------------------------------
@app.route("/backup")
def decoy_backup():
    return jsonify({
        "note": "this backup rotated out last week",
        "status": "stale — check current ops tooling instead",
    })


@app.route("/old-backup")
def decoy_old_backup():
    return jsonify({"error": "archived", "contact": "it-ops@coldboot.local"})


@app.route("/uploads")
def decoy_uploads():
    return jsonify({"files": []})


@app.route("/debug")
def decoy_debug():
    return jsonify({"status": "wrong door"})


@app.route("/coldsync-ops")
def backup():
    """The REAL hidden endpoint. Not linked anywhere in the UI, and not a
    word you'll find in a stock dirb/gobuster wordlist -- players need the
    provided custom wordlist (or a big enough general one) to land on it."""
    return jsonify({
        "note": "nightly ops sync - scheduled for deletion, do not index",
        "generated": "2026-07-30T02:14:00Z",
        "payload_encoding": "xor+base64",
        "user_backup": ENCODED_BACKUP,
    })


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/submit-flag", methods=["POST"])
@login_required
def submit_flag():
    team_name = request.form.get("team_name", "").strip()
    team_email = request.form.get("team_email", "").strip()
    submitted_flag = request.form.get("flag", "").strip()

    if not team_name or not team_email or not submitted_flag:
        flash("ALL FIELDS ARE REQUIRED.")
        return redirect(url_for("index"))

    if submitted_flag != FLAG:
        flash("INCORRECT FLAG. KEEP DIGGING.")
        return redirect(url_for("index"))

    session["team_name"] = team_name
    session["flag_captured"] = True
    send_solve_notification(team_name, team_email)
    return redirect(url_for("congrats"))


@app.route("/congrats")
@login_required
def congrats():
    if not session.get("flag_captured"):
        return redirect(url_for("index"))
    return render_template("congrats.html", team_name=session.get("team_name", "PLAYER"))


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
