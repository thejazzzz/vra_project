import requests
import time

BASE_URL = "http://localhost:7000"
EMAIL = "verifier_v2@example.com"

def test_auth_flow_cookies():
    print(f"🧪 Testing Cookie-Based Auth Flow for {EMAIL}...")
    
    session = requests.Session()
    
    # 1. Login
    print("\n[1] Attempting Login...")
    login_payload = {"email": EMAIL}
    try:
        login_res = session.post(f"{BASE_URL}/auth/login", json=login_payload, timeout=30)
        login_res.raise_for_status()
        
        # Check Cookies
        access_cookie = session.cookies.get("vra_auth_token")
        refresh_cookie = session.cookies.get("vra_refresh_token") # Note: This might not be visible if path is restricted?
        # A standard requests session *stores* path-restricted cookies but might not return them in simple .get() if path doesn't match?
        # Actually requests.Session stores all cookies.
        
        if access_cookie:
            print(f"✅ Login Successful. Access Cookie found: {access_cookie[:10]}...")
        else:
            print("❌ Login Failed. access cookie missing.")
            return

        # refresh cookie has path /auth/refresh.
        # It should be in the jar.
        has_refresh = any(c.name == 'vra_refresh_token' for c in session.cookies)
        if has_refresh:
             print(f"✅ Refresh Cookie found (HttpOnly/Path restricted).")
        else:
             print("❌ Refresh Cookie missing.")
             
    except Exception as e:
        print(f"❌ Login Failed: {e}")
        if 'login_res' in locals(): print(login_res.text)
        return

    # 2. Get Me (Protected Route)
    print("\n[2] Testing Protected Route (/auth/me)...")
    try:
        me_res = session.get(f"{BASE_URL}/auth/me", timeout=10) # Cookies sent auto
        me_res.raise_for_status()
        user = me_res.json()
        print(f"✅ /auth/me Successful. User ID: {user['id']}")
    except Exception as e:
        print(f"❌ /auth/me Failed: {e}")
        if 'me_res' in locals(): print(me_res.text)
        return

    # 3. Test Refresh Token
    print("\n[3] Testing Token Refresh (/auth/refresh)...")
    
    # Save old tokens to compare
    old_access = session.cookies.get("vra_auth_token")
    old_refresh_val = next((c.value for c in session.cookies if c.name == 'vra_refresh_token'), None)

    try:
        # We must POST to /auth/refresh. 
        # The session should automatically send the vra_refresh_token cookie because the path matches/is subpath.
        refresh_res = session.post(f"{BASE_URL}/auth/refresh", timeout=10)
        refresh_res.raise_for_status()
        
        print("✅ Refresh Request Successful.")
        
        new_access = session.cookies.get("vra_auth_token")
        new_refresh_val = next((c.value for c in session.cookies if c.name == 'vra_refresh_token'), None)
        
        if new_access != old_access:
            print(f"✅ Access Token Rotated: {old_access[:5]}... -> {new_access[:5]}...")
        else:
            print("⚠️ Access Token did not change (might be issue or intended if only extending).")

        if new_refresh_val != old_refresh_val:
            print(f"✅ Refresh Token Rotated.")
        else:
            print(f"⚠️ Refresh Token did not rotate (Check logic).")
            
    except Exception as e:
        print(f"❌ Refresh Failed: {e}")
        if 'refresh_res' in locals(): print(refresh_res.text)
        return

    # 4. Logout
    print("\n[4] Testing Logout...")
    try:
        logout_res = session.post(f"{BASE_URL}/auth/logout", timeout=10)
        logout_res.raise_for_status()
        
        # Verify cookies cleared
        cleared_access = session.cookies.get("vra_auth_token")
        if not cleared_access:
             print("✅ Logout Successful. Cookies cleared.")
        else:
             print(f"❌ Cookies still present: {cleared_access}")
             
    except Exception as e:
        print(f"❌ Logout Failed: {e}")
        if 'logout_res' in locals(): print(logout_res.text)   
        return 
    print("\n🎉 Full Auth Verification Complete.")

if __name__ == "__main__":
    test_auth_flow_cookies()
