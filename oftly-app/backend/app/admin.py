"""Operator tools (run from the backend folder):  python -m app.admin <command>
  list-users | reset-link EMAIL | revoke-sessions EMAIL | delete-user EMAIL | new-invite
Use reset-link to help a tester who cannot receive email (no mail provider configured)."""
import argparse
import secrets
import shutil
import sys

from . import auth, config


def _user(email):
    with auth.acct() as c:
        return c.execute("SELECT id,email FROM users WHERE email=?", (email.strip().lower(),)).fetchone()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m app.admin")
    ap.add_argument("cmd", choices=["list-users", "reset-link", "revoke-sessions", "delete-user", "new-invite"])
    ap.add_argument("email", nargs="?")
    a = ap.parse_args(argv)
    if a.cmd == "new-invite":
        print(secrets.token_urlsafe(9)); return 0
    if a.cmd == "list-users":
        with auth.acct() as c:
            for r in c.execute("SELECT email,display_name,created_at,last_login FROM users ORDER BY created_at"):
                print(f"{r['email']}\t{r['display_name']}\tcreated={int(r['created_at'])}\tlast_login={int(r['last_login'] or 0)}")
        return 0
    u = _user(a.email or "")
    if not u:
        print("No such user", file=sys.stderr); return 1
    if a.cmd == "reset-link":
        print(f"{str(config.env('PUBLIC_URL', 'http://127.0.0.1:8000')).rstrip('/')}/#/reset?token={auth.make_reset_token(u['id'])}   (valid 30 minutes, single use)")
    elif a.cmd == "revoke-sessions":
        auth.revoke(u["id"]); print("All sessions revoked.")
    elif a.cmd == "delete-user":
        with auth.acct() as c:
            c.execute("DELETE FROM users WHERE id=?", (u["id"],))
        shutil.rmtree(config.data_dir() / "users" / u["id"], ignore_errors=True); print("Deleted account and all data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
