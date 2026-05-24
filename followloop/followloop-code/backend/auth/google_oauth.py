"""
Google OAuth 2.0 helpers — token exchange, encryption, credential refresh.
"""
import os
import json
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from flask import Blueprint, request, jsonify

from db.models import (
    upsert_pm,
    upsert_oauth_token,
    get_oauth_token,
    update_oauth_token,
    create_session,
)

auth_bp = Blueprint("auth", __name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "email",
    "profile",
]


def _fernet() -> Fernet:
    return Fernet(os.environ["TOKEN_ENCRYPTION_KEY"].encode())


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def get_credentials_for_pm(pm_id: str) -> Credentials:
    """
    Return a valid Google Credentials object for the given PM.
    Refreshes access token automatically if expired.
    """
    record = get_oauth_token(pm_id)
    if not record:
        raise ValueError(f"No OAuth token found for pm_id={pm_id}")

    refresh_token = decrypt_token(record["refresh_token"])

    creds = Credentials(
        token=record["access_token"],
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        # Do NOT pass scopes here — including scopes not in the original grant
        # causes refresh to fail with invalid_scope. The access token already
        # carries the correct scopes; scopes are re-declared only at OAuth time.
    )

    # google-auth's utcnow() is naive, so expiry must also be naive UTC
    creds.expiry = datetime.fromisoformat(record["token_expiry"].replace("Z", "+00:00")).replace(tzinfo=None)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        update_oauth_token(
            pm_id=pm_id,
            access_token=creds.token,
            token_expiry=creds.expiry.isoformat(),
        )

    return creds


# ---------------------------------------------------------------------------
# Backend endpoint: exchange auth code for tokens
# ---------------------------------------------------------------------------

@auth_bp.route("/auth/google/exchange", methods=["POST"])
def exchange_code():
    data = request.get_json()
    code = data.get("code")
    if not code:
        return jsonify({"error": "missing code"}), 400

    try:
      return _exchange_code(code)
    except Exception as e:
        import traceback
        print(f"[auth] exchange_code failed: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


def _exchange_code(code: str):
    # oauthlib raises a warning when Google returns expanded scope URIs
    # (e.g. "userinfo.email" instead of "email") — this suppresses that.
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
                "redirect_uris": [os.environ["GOOGLE_REDIRECT_URI"]],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    flow.fetch_token(code=code)

    creds = flow.credentials

    # Get user info via userinfo endpoint (no extra API to enable)
    import requests as _requests
    userinfo_resp = _requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.token}"},
    )
    userinfo_resp.raise_for_status()
    userinfo = userinfo_resp.json()
    email = userinfo["email"]
    name = userinfo.get("name") or userinfo.get("given_name") or email.split("@")[0]
    google_sub = userinfo["id"]

    # Upsert PM record
    pm = upsert_pm(email=email, name=name, google_sub=google_sub)

    # Log which scopes Google actually granted (for debugging)
    print(f"[auth] Scopes granted by Google: {sorted(creds.scopes or [])}")

    # Encrypt and store tokens
    expiry_iso = creds.expiry.astimezone(timezone.utc).isoformat() if creds.expiry else datetime.now(timezone.utc).isoformat()
    upsert_oauth_token(
        pm_id=pm["id"],
        access_token=creds.token,
        refresh_token_encrypted=encrypt_token(creds.refresh_token),
        token_expiry=expiry_iso,
        scopes=list(creds.scopes or SCOPES),
    )

    # Create session
    session_token = create_session(pm["id"])

    return jsonify({"pm_id": pm["id"], "session_token": session_token})
