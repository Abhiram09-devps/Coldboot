# COLDBOOT — Login CTF Challenge

## How it works

This is a small Flask app, not a static site — that's required for the
gating and hidden-endpoint mechanics to be real (a static HTML file can't
enforce server-side auth, and "hidden" JS logic is visible via view-source).

- Every route except `/login` redirects to the login page if the visitor
  isn't authenticated (Flask session cookie).
- `/backup` is the one deliberate exception. It is **not linked from any
  page** — the only way to find it is to brute-force it, e.g. with:
  ```
  gobuster dir -u http://TARGET:5000/ -w /usr/share/wordlists/dirb/common.txt
  ```
  `backup` is a common word in most default wordlists (dirb's `common.txt`,
  SecLists' `common.txt`), so this is solvable without a custom wordlist.
- `/backup` returns JSON containing a base64-encoded, XOR-obfuscated blob:
  `admin:R3tr0Gam3r!2026` XOR'd byte-by-byte against the repeating key
  `c0ldboot`, then base64-encoded.
- The XOR key itself is **not** in the JSON — it's hidden in an HTML
  comment in the login page's source (`view-source:` on `/login`), so the
  player needs both recon steps (view-source *and* gobuster) to fully
  reconstruct the credentials.
- Submitting `admin` / `R3tr0Gam3r!2026` on `/login` sets
  `session['authenticated'] = True` and unlocks the rest of the site.

## Running it

```
pip install -r requirements.txt
python app.py
```

Serves on `http://0.0.0.0:5000`.

## Solve path (for testing / verification)

1. Visit the site — only `/login` is reachable.
2. `view-source:` the login page → find the HTML comment with the XOR key
   `c0ldboot`.
3. Run gobuster (or dirb/ffuf) against the root → discover `/backup`.
4. `curl http://TARGET:5000/backup` → get the base64 blob
   `AlQBDQxVPUcXQlwjAwJcBkICXFZU`.
5. Base64-decode, then XOR each byte against the repeating key `c0ldboot`
   → recover `admin:R3tr0Gam3r!2026`.
6. Log in at `/login` with those credentials → redirected to the
   authenticated home page.

## Notes for the challenge author

- Credentials, the XOR key, and the encoded blob are all in `app.py` near
  the top — change them freely; just remember to regenerate the base64
  blob to match if you change either the plaintext or the key.
- `app.secret_key` is a placeholder. Set the `SECRET_KEY` environment
  variable to something random before exposing this anywhere real.
- If you want a harder challenge, swap `/backup` for a less obvious
  wordlist word, or add another XOR/rot13 layer.
