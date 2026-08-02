# COLDBOOT — Login CTF Challenge

## How it works

This is a small Flask app, not a static site — that's required for the
gating and hidden-endpoint mechanics to be real (a static HTML file can't
enforce server-side auth, and "hidden" JS logic is visible via view-source).

**Access control:** every real route is gated behind login except
`/login` and the recon endpoints below. Truly nonexistent paths return a
normal 404 (not a redirect) so directory brute-force tools can actually
tell hits apart from noise.

**Recon layer (tuned for a ~15-20 minute solve):**

- The site ships with `static/gg/bb/hh/wordlist.txt` — a ~140-word custom
  list, buried a few folders deep under `static/`. It's served
  automatically by Flask's static file handling (no auth required, same
  as any static asset), and there's a **download button right on the
  login page** ("⬇ download recon wordlist") so players self-serve it —
  you don't have to hand it out manually.
- Point gobuster at the root using that downloaded file:
  ```
  gobuster dir -u http://TARGET:5000/ -w wordlist.txt
  ```
- The scan turns up **five** non-404 paths, not one:
  - `/backup`, `/old-backup`, `/uploads`, `/debug` — decoys. Each is a
    real 200 response with plausible-looking but useless JSON, so the
    obvious first guess (`backup`, present in every stock wordlist) costs
    the player a bit of time verifying it's a dead end instead of handing
    them the flag immediately.
  - `/coldsync-ops` — the real one. Not a word in stock wordlists
    (dirb/SecLists `common.txt`), so it's only found via the provided
    custom list (or a much bigger general-purpose one).
- `/coldsync-ops` returns JSON with `"payload_encoding": "xor+base64"`
  and a base64 blob: `admin:R3tr0Gam3r!2026` XOR'd byte-by-byte against
  the key `c0ldboot`, then base64-encoded.
- **The XOR key is split across two separate discovery techniques**,
  forcing players to combine both instead of finding one comment and
  being done:
  - `view-source:` on `/login` → HTML comment reveals the *prefix*: `c0ld`
  - Response headers on `/login` (`curl -i`, or browser devtools Network
    tab) → `X-Ops-Seed-Suffix: boot` reveals the *suffix*
  - Concatenated: `c0ld` + `boot` = `c0ldboot`
- Submitting `admin` / `R3tr0Gam3r!2026` on `/login` sets
  `session['authenticated'] = True` and unlocks the rest of the site.

## Running it

### For competition deployment (recommended): Docker

Players don't need Python, pip, or anything installed — you (the organizer)
just need Docker on whatever machine or server will host the challenge.

```bash
docker build -t coldboot-ctf .
docker run -d -p 5000:5000 -e SECRET_KEY=$(openssl rand -hex 32) --name coldboot coldboot-ctf
```

That's it. The challenge is now live at `http://<host-ip>:5000` for anyone
who can reach that machine/port. To stop it: `docker stop coldboot`.

- `-p 5000:5000` maps container port 5000 to the host. Change the first
  number if you want it on a different port, e.g. `-p 8080:5000`.
- `-e SECRET_KEY=...` sets a random Flask session secret at runtime instead
  of baking one into the image (important if multiple people might inspect
  the image).
- If you're hosting this for a live competition, put it on a VPS (DigitalOcean,
  Linode, a cloud VM, etc.) with a public IP, open the port in the firewall,
  and hand out `http://<vps-ip>:5000` to players. A reverse proxy (nginx/Caddy)
  in front with a domain name is nicer but optional.

### For local testing / development only

```
pip install -r requirements.txt
python app.py
```

Serves on `http://0.0.0.0:5000`.

## Solve path (for testing / verification)

1. Visit the site — only `/login` is reachable.
2. `view-source:` the login page → find the HTML comment giving the key
   *prefix* `c0ld`.
3. `curl -i http://TARGET:5000/login` (or check devtools Network tab) →
   find the `X-Ops-Seed-Suffix: boot` response header. Combine: `c0ldboot`.
4. Run gobuster against the root with `wordlist.txt` → get back `/backup`,
   `/old-backup`, `/uploads`, `/debug` (decoys, all dead ends) and
   `/coldsync-ops` (the real one).
5. `curl http://TARGET:5000/coldsync-ops` → get the base64 blob
   `AlQBDQxVPUcXQlwjAwJcBkICXFZU`.
6. Base64-decode, then XOR each byte against the repeating key `c0ldboot`
   → recover `admin:R3tr0Gam3r!2026`.
7. Log in at `/login` with those credentials → redirected to the
   authenticated home page.

## Notes for the challenge author

- Credentials, the XOR key, and the encoded blob are all in `app.py` near
  the top — change them freely; just remember to regenerate the base64
  blob to match if you change either the plaintext or the key. Note the
  key is split into a prefix (hardcoded in `templates/login.html`'s HTML
  comment) and a suffix (hardcoded in the `X-Ops-Seed-Suffix` header in
  `app.py`'s `login()` view) — update both halves if you change `XOR_KEY`.
- `app.secret_key` is a placeholder. Set the `SECRET_KEY` environment
  variable to something random before exposing this anywhere real.
- `wordlist.txt` (at `static/gg/bb/hh/wordlist.txt`) is sized (~140 words)
  to make a gobuster scan take a couple of minutes rather than being
  instant — tune its size up/down to adjust difficulty. Keep
  `coldsync-ops` and the four decoy words in it (or swap in your own
  real/decoy path names and update `app.py` to match).
- If you want it even harder: add more decoy endpoints, extend the
  wordlist, or add another encoding layer on top of xor+base64.
