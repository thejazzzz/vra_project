import requests
from dotenv import load_dotenv
load_dotenv(".env.local")
from database.db import engine
from sqlalchemy import text

BASE_URL = "http://localhost:7000"
EMAIL = "verifier_new@example.com"

def test_auth_flow():
    print(f"Testing Auth Flow for {EMAIL}...")
    
    # 0. Register
    register_payload = {"email": EMAIL, "password": "securepassword"}
    try:
        reg_res = requests.post(f"{BASE_URL}/auth/register", json=register_payload, timeout=10)
        if reg_res.status_code == 200:
            print("✅ Registration Successful.")
        elif reg_res.status_code == 400:
            # Likely user already exists - log and continue
            print(f"ℹ️ Registration returned 400 (user may already exist): {reg_res.text}")
        else:
            reg_res.raise_for_status()
    except Exception as e:
        print(f"❌ Registration Failed: {e}")
        return

    # 1.5 Manually Verify Email in DB
    try:
        with engine.begin() as conn:
            result = conn.execute(text("UPDATE users SET email_verified = TRUE WHERE email = :email"), {"email": EMAIL})
            if result.rowcount == 0:
                print(f"❌ No user found with email {EMAIL} to verify.")
                return
            print("✅ Email manually verified in DB.")
    except Exception as e:
        print(f"❌ Database Verification Update Failed: {e}")
        return

    # 1. Login
    login_payload = {"email": EMAIL, "password": "securepassword"}
    try:
        login_res = requests.post(f"{BASE_URL}/auth/login", json=login_payload, timeout=10)
        login_res.raise_for_status()
        tokens = login_res.json()
        access_token = tokens["access_token"]
        print(f"✅ Login Successful. Token: {access_token[:10]}...")
    except Exception as e:
        print(f"❌ Login Failed: {e}")
        if 'login_res' in locals(): print(login_res.text)
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Get Me
    try:
        me_res = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        me_res.raise_for_status()
        user = me_res.json()
        print(f"✅ /auth/me Successful. User ID: {user['id']}")
    except Exception as e:
        print(f"❌ /auth/me Failed: {e}")
        if 'me_res' in locals(): print(me_res.text)
        return

    # 3. Get Sessions (Dashboard)
    try:
        sess_res = requests.get(f"{BASE_URL}/planner/sessions", headers=headers, timeout=10)
        sess_res.raise_for_status()
        sessions = sess_res.json().get("sessions", [])
        print(f"✅ /planner/sessions Successful. Found {len(sessions)} sessions.")
    except Exception as e:
        print(f"❌ /planner/sessions Failed: {e}")
        if 'sess_res' in locals(): print(sess_res.text)
        return
        
    print("\n🎉 Verification Complete: Backend Auth & Dashboard Endpoints are working.")

if __name__ == "__main__":
    test_auth_flow()
