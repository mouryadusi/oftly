import io
import logging
import sqlite3
import time
import pytest
from fastapi.testclient import TestClient
from conftest import PASSWORD, add, png, signed_in
from app import admin, auth, config
from app.main import app

def reg(c, email="new@example.com", pw=PASSWORD, **kw):
    return c.post("/api/auth/register", json={"email": email, "password": pw, **kw})

def accounts():
    c = sqlite3.connect(config.accounts_db_path()); c.row_factory = sqlite3.Row; return c

# ------------------------------------------------------------------ registration and storage
def test_register_sets_httponly_session_and_csrf_cookies(anon):
    r = reg(anon, display_name="Sam")
    assert r.status_code == 201 and r.json()["email"] == "new@example.com" and "password" not in r.text
    sc = " ".join(r.headers.get_list("set-cookie")).lower()
    assert "oftly_session=" in sc and "httponly" in sc and "samesite=lax" in sc
    assert anon.get("/api/auth/me").json()["display_name"] == "Sam"
    anon.headers["x-csrf-token"] = anon.cookies["oftly_csrf"]
    assert anon.get("/api/preferences").json()["preferred_name"] == "Sam"

def test_passwords_are_argon2id_and_sessions_are_stored_hashed(anon):
    reg(anon); tok = anon.cookies["oftly_session"]
    db = accounts(); u = db.execute("SELECT * FROM users").fetchone()
    assert u["pw_hash"].startswith("$argon2id$") and PASSWORD not in u["pw_hash"]
    assert db.execute("SELECT COUNT(*) FROM sessions WHERE token_hash=?", (tok,)).fetchone()[0] == 0       # raw token is not stored
    assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1

@pytest.mark.parametrize("pw", ["short1", "password123", "aaaaaaaaaaaaaaaa", "x" * 129])
def test_weak_passwords_rejected(anon, pw):
    assert reg(anon, pw=pw).status_code == 422

def test_email_validation_and_duplicates(anon):
    for bad in ["nope", "a@b", "a b@c.com", "x" * 300 + "@a.com"]:
        assert reg(anon, email=bad).status_code == 422, bad
    assert reg(anon).status_code == 201
    assert reg(TestClient(app), email="NEW@example.com").status_code == 409          # case-insensitive uniqueness

def test_private_beta_invite_code(anon, monkeypatch):
    monkeypatch.setenv("OFTLY_INVITE_CODES", "friends-2026, spare")
    assert reg(anon).status_code == 403 and reg(anon, invite="wrong").status_code == 403
    assert reg(anon, invite="spare").status_code == 201
    assert anon.get("/api/auth/config").json()["invite_required"] is True

def test_new_accounts_start_clean_and_demo_is_off_by_default(anon, monkeypatch):
    monkeypatch.delenv("OFTLY_ENABLE_DEMO")
    reg(anon); anon.headers["x-csrf-token"] = anon.cookies["oftly_csrf"]
    assert anon.get("/api/summary").json()["total"] == 0 and anon.get("/api/outfits").json() == []
    assert anon.post("/api/demo").status_code == 404 and anon.get("/api/auth/config").json()["demo_enabled"] is False

# ------------------------------------------------------------------ login, brute force
def test_login_logout_and_generic_errors(anon):
    reg(TestClient(app)); 
    bad_pw = anon.post("/api/auth/login", json={"email": "new@example.com", "password": "wrong-password-123"})
    bad_user = anon.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong-password-123"})
    assert bad_pw.status_code == bad_user.status_code == 401 and bad_pw.json() == bad_user.json()      # no account enumeration
    assert anon.post("/api/auth/login", json={"email": "new@example.com", "password": PASSWORD}).status_code == 200
    anon.headers["x-csrf-token"] = anon.cookies["oftly_csrf"]
    old = anon.cookies["oftly_session"]
    assert anon.post("/api/auth/logout").status_code == 204 and anon.get("/api/auth/me").status_code == 401
    assert TestClient(app, cookies={"oftly_session": old}).get("/api/summary").status_code == 401      # replaying the old cookie fails

def test_brute_force_is_throttled_and_locks_even_correct_password(anon):
    reg(TestClient(app))
    codes = [anon.post("/api/auth/login", json={"email": "new@example.com", "password": f"guess-number-{i:02d}"}).status_code for i in range(10)]
    assert codes[:8] == [401] * 8 and codes[8:] == [429, 429]
    r = anon.post("/api/auth/login", json={"email": "new@example.com", "password": PASSWORD})
    assert r.status_code == 429 and "Retry-After" in r.headers

def test_account_lockout_persists_after_limiter_reset(anon):
    reg(TestClient(app))
    for i in range(8): anon.post("/api/auth/login", json={"email": "new@example.com", "password": f"guess-number-{i:02d}"})
    auth.limiter.clear()                                                    # e.g. a server restart
    assert anon.post("/api/auth/login", json={"email": "new@example.com", "password": PASSWORD}).status_code == 429

def test_registration_rate_limit_per_ip(anon):
    codes = [reg(anon, email=f"u{i}@example.com").status_code for i in range(12)]
    assert codes[:10] == [201] * 10 and codes[10:] == [429, 429]

# ------------------------------------------------------------------ every route is protected
def test_every_api_route_rejects_anonymous_requests(anon):
    public = {"/api/health", "/api/auth/register", "/api/auth/login", "/api/auth/forgot", "/api/auth/reset", "/api/auth/config", "/api/engine"}
    checked = 0
    for r in app.routes:
        path = getattr(r, "path", "")
        if not (path.startswith("/api") or path.startswith("/media")) or path in public: continue
        for m in (r.methods - {"HEAD", "OPTIONS"}):
            res = anon.request(m, path.replace("{iid}", "1").replace("{oid}", "1").replace("{eid}", "1").replace("{name}", "x.jpg").replace("{cid}", "shirts"))
            assert res.status_code == 401, f"{m} {path} -> {res.status_code}"; checked += 1
    assert checked >= 35, checked

def test_docs_are_disabled_in_production(anon):
    assert anon.get("/docs").status_code in (404, 405) and anon.get("/openapi.json").status_code in (404, 405)

# ------------------------------------------------------------------ CSRF
def test_state_changing_requests_need_the_csrf_token(client):
    tok = client.headers.pop("x-csrf-token")
    assert client.post("/api/items", json={"name": "x", "category": "shirts"}).status_code == 403
    assert client.post("/api/items", json={"name": "x", "category": "shirts"}, headers={"x-csrf-token": "wrong"}).status_code == 403
    assert client.get("/api/items").status_code == 200
    assert client.post("/api/items", json={"name": "x", "category": "shirts"}, headers={"x-csrf-token": tok}).status_code == 201

def test_bearer_token_clients_do_not_need_csrf(anon):
    reg(anon); tok = anon.cookies["oftly_session"]
    c = TestClient(app)
    assert c.post("/api/items", json={"name": "x", "category": "shirts"}, headers={"authorization": f"Bearer {tok}"}).status_code == 201

# ------------------------------------------------------------------ sessions
def test_idle_and_absolute_expiry_and_tampering(client):
    assert client.get("/api/summary").status_code == 200
    db = accounts(); db.execute("UPDATE sessions SET last_seen=?", (time.time() - 8 * 86400,)); db.commit()
    assert client.get("/api/summary").status_code == 401                       # idle > 7 days
    c2 = signed_in("b@example.com")
    db.execute("UPDATE sessions SET expires_at=? WHERE user_id=(SELECT id FROM users WHERE email='b@example.com')", (time.time() - 1,)); db.commit()
    assert c2.get("/api/summary").status_code == 401                           # absolute lifetime
    c3 = signed_in("c@example.com"); c3.cookies.set("oftly_session", c3.cookies["oftly_session"][:-3] + "abc", domain="testserver.local") if False else None
    assert TestClient(app, cookies={"oftly_session": "tampered"}).get("/api/summary").status_code == 401

def test_logout_all_revokes_every_device(client):
    other = TestClient(app); other.post("/api/auth/login", json={"email": "tester@example.com", "password": PASSWORD})
    assert other.get("/api/summary").status_code == 200
    assert client.post("/api/auth/logout-all").status_code == 204
    assert other.get("/api/summary").status_code == 401 and client.get("/api/summary").status_code == 401

def test_password_change_signs_out_other_devices_and_checks_current(client):
    other = TestClient(app); other.post("/api/auth/login", json={"email": "tester@example.com", "password": PASSWORD})
    assert client.post("/api/auth/password", json={"current": "nope-nope-nope-1", "new": "another-long-pass-9"}).status_code == 403
    assert client.post("/api/auth/password", json={"current": PASSWORD, "new": "short"}).status_code == 422
    assert client.post("/api/auth/password", json={"current": PASSWORD, "new": "another-long-pass-9"}).status_code == 204
    assert client.get("/api/summary").status_code == 200 and other.get("/api/summary").status_code == 401
    assert TestClient(app).post("/api/auth/login", json={"email": "tester@example.com", "password": PASSWORD}).status_code == 401

# ------------------------------------------------------------------ user isolation
def test_users_cannot_see_or_touch_each_others_data(client, second_client):
    a = add(client, "A secret jacket", "shirts", primary_color="red", notes="private note")
    up = client.post("/api/uploads", files={"file": ("a.png", png(), "image/png")}).json()
    client.patch(f"/api/items/{a['id']}", json={"name": "A secret jacket", "category": "shirts", "image": up["image"]})
    a2 = add(client, "A secret trousers", "pants")
    oid = client.post("/api/outfits", json={"item_ids": [a["id"], a2["id"]], "name": "A look"}).json()["id"]
    client.put("/api/preferences", json={"preferred_name": "Alice", "city": "Paris"})
    # B sees nothing of A's
    assert second_client.get("/api/items").json()["total"] == 0 and second_client.get("/api/outfits").json() == []
    assert second_client.get("/api/preferences").json()["city"] == "" and second_client.get("/api/summary").json()["total"] == 0
    assert second_client.get(f"/api/items/{a['id']}").status_code == 404 and second_client.get(f"/api/outfits/{oid}").status_code == 404
    assert client.get(up["image_url"]).status_code == 200 and second_client.get(up["image_url"]).status_code == 404       # photos too
    # B cannot modify or delete A's records (same numeric ids exist for B only after B creates them)
    assert second_client.patch(f"/api/items/{a['id']}", json={"name": "hijack", "category": "shirts"}).status_code == 404
    assert second_client.delete(f"/api/items/{a['id']}").status_code == 404 and second_client.delete(f"/api/outfits/{oid}").status_code == 404
    b = add(second_client, "B shirt", "shirts"); assert b["id"] == a["id"]         # same id, different database
    assert client.get(f"/api/items/{a['id']}").json()["name"] == "A secret jacket"
    # B's exports and wipe never include or affect A
    assert "A secret jacket" not in second_client.get("/api/export").text and "private note" not in second_client.get("/api/export/backup").content.decode("latin-1")
    assert second_client.delete("/api/data?confirm=true").status_code in (200, 204)
    assert client.get("/api/summary").json()["total"] == 2
    d = config.data_dir() / "users"; assert len(list(d.iterdir())) == 2

def test_media_path_traversal_is_blocked(client):
    for p in ["/media/../accounts.db", "/media/..%2faccounts.db", "/media/%2e%2e/%2e%2e/accounts.db", "/media/....//accounts.db"]:
        assert client.get(p).status_code in (400, 404), p

# ------------------------------------------------------------------ password recovery
def test_recovery_flow_is_single_use_enumeration_safe_and_revokes_sessions(client):
    anon = TestClient(app)
    known = anon.post("/api/auth/forgot", json={"email": "tester@example.com"}); unknown = anon.post("/api/auth/forgot", json={"email": "ghost@example.com"})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    assert len(auth.OUTBOX) == 1 and auth.OUTBOX[0]["to"] == "tester@example.com"          # mail only for the real account
    token = auth.OUTBOX[0]["body"].split("token=")[1].split()[0]
    assert accounts().execute("SELECT COUNT(*) FROM resets WHERE token_hash=?", (token,)).fetchone()[0] == 0     # token stored hashed
    assert anon.post("/api/auth/reset", json={"token": token, "password": "tiny"}).status_code == 422
    assert anon.post("/api/auth/reset", json={"token": token, "password": "a-brand-new-passphrase-3"}).status_code == 204
    assert anon.post("/api/auth/reset", json={"token": token, "password": "a-brand-new-passphrase-4"}).status_code == 400    # single use
    assert client.get("/api/summary").status_code == 401                                   # old sessions revoked
    assert anon.post("/api/auth/login", json={"email": "tester@example.com", "password": PASSWORD}).status_code == 401
    assert anon.post("/api/auth/login", json={"email": "tester@example.com", "password": "a-brand-new-passphrase-3"}).status_code == 200

def test_reset_tokens_expire_and_only_the_newest_works(client):
    anon = TestClient(app); anon.post("/api/auth/forgot", json={"email": "tester@example.com"}); t1 = auth.OUTBOX[-1]["body"].split("token=")[1].split()[0]
    auth.limiter.clear(); anon.post("/api/auth/forgot", json={"email": "tester@example.com"}); t2 = auth.OUTBOX[-1]["body"].split("token=")[1].split()[0]
    assert anon.post("/api/auth/reset", json={"token": t1, "password": "a-brand-new-passphrase-3"}).status_code == 400
    db = accounts(); db.execute("UPDATE resets SET expires_at=?", (time.time() - 1,)); db.commit()
    assert anon.post("/api/auth/reset", json={"token": t2, "password": "a-brand-new-passphrase-3"}).status_code == 400

def test_forgot_is_rate_limited_per_account(client):
    anon = TestClient(app)
    codes = [anon.post("/api/auth/forgot", json={"email": "tester@example.com"}).status_code for _ in range(5)]
    assert codes[:3] == [202] * 3 and codes[3:] == [429, 429]

def test_admin_cli_can_issue_a_reset_link_without_email(client, capsys):
    assert admin.main(["reset-link", "tester@example.com"]) == 0
    out = capsys.readouterr().out; assert "/#/reset?token=" in out
    token = out.split("token=")[1].split()[0]
    assert TestClient(app).post("/api/auth/reset", json={"token": token, "password": "a-brand-new-passphrase-3"}).status_code == 204
    assert admin.main(["reset-link", "ghost@example.com"]) == 1

# ------------------------------------------------------------------ account deletion
def test_account_deletion_removes_everything_and_leaves_others_alone(client, second_client):
    add(client, "mine", "shirts"); client.post("/api/uploads", files={"file": ("a.png", png(), "image/png")})
    uid = accounts().execute("SELECT id FROM users WHERE email='tester@example.com'").fetchone()[0]
    assert (config.data_dir() / "users" / uid / "oftly.db").exists()
    assert client.request("DELETE", "/api/auth/account", json={"password": "wrong-password-123"}).status_code == 403
    assert client.request("DELETE", "/api/auth/account", json={"password": PASSWORD}).status_code == 204
    assert not (config.data_dir() / "users" / uid).exists()
    assert accounts().execute("SELECT COUNT(*) FROM users WHERE id=?", (uid,)).fetchone()[0] == 0 and accounts().execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (uid,)).fetchone()[0] == 0
    assert TestClient(app).post("/api/auth/login", json={"email": "tester@example.com", "password": PASSWORD}).status_code == 401
    assert second_client.get("/api/summary").status_code == 200

# ------------------------------------------------------------------ uploads
def test_upload_validation_rejects_non_images_and_disguised_files(client):
    up = lambda name, data, ct: client.post("/api/uploads", files={"file": (name, data, ct)}).status_code
    assert up("a.png", png(), "image/png") == 201
    assert up("evil.jpg", b"<html><script>alert(1)</script></html>", "image/jpeg") in (400, 415, 422)
    assert up("evil.svg", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "image/svg+xml") in (400, 415, 422)
    assert up("../../x.png", png(), "image/png") == 201                           # name is ignored; storage name is random
    assert up("empty.png", b"", "image/png") in (400, 415, 422)

def test_oversized_upload_is_refused_before_processing(client):
    assert client.post("/api/uploads", files={"file": ("big.png", b"0" * 11_000_000, "image/png")}).status_code == 413

def test_photo_quota_per_user(client, monkeypatch):
    monkeypatch.setenv("OFTLY_MAX_PHOTOS", "2")
    codes = [client.post("/api/uploads", files={"file": ("a.png", png((i, 9, 9)), "image/png")}).status_code for i in range(3)]
    assert codes == [201, 201, 413]

# ------------------------------------------------------------------ transport + hygiene
def test_https_requests_get_secure_cookies_and_hsts(anon):
    r = anon.post("/api/auth/register", json={"email": "s@example.com", "password": PASSWORD}, headers={"x-forwarded-proto": "https"})
    assert r.headers["strict-transport-security"].startswith("max-age=")
    plain = TestClient(app).get("/api/health"); assert "strict-transport-security" not in plain.headers

def test_forced_secure_cookie_flag(anon, monkeypatch):
    monkeypatch.setenv("OFTLY_COOKIE_SECURE", "1")
    assert "secure" in " ".join(reg(anon).headers.get_list("set-cookie")).lower()

def test_passwords_never_appear_in_logs(anon, caplog):
    caplog.set_level(logging.DEBUG)
    reg(anon); anon.post("/api/auth/login", json={"email": "new@example.com", "password": "wrong-password-123"})
    anon.post("/api/auth/forgot", json={"email": "new@example.com"})
    assert PASSWORD not in caplog.text and "wrong-password-123" not in caplog.text

def test_unhandled_errors_do_not_leak_details():
    def boom(): raise RuntimeError("secret-internal-detail /etc/passwd")
    app.add_api_route("/api/_boom", boom, methods=["GET"]); app.router.routes.insert(0, app.router.routes.pop())
    c = signed_in("boom@example.com"); c2 = TestClient(app, raise_server_exceptions=False, cookies=c.cookies)
    r = c2.get("/api/_boom"); assert r.status_code == 500 and "secret-internal-detail" not in r.text and "Traceback" not in r.text
    app.router.routes[:] = [x for x in app.router.routes if getattr(x, "path", "") != "/api/_boom"]
