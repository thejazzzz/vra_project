# scripts/verify_expansion.py
import urllib.request
import urllib.parse
import json
import time
import uuid
import threading
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
load_dotenv(".env.local")
from database.db import engine
from sqlalchemy import text

BASE_URL = "http://localhost:7000"
TEST_EMAIL = "verifier_expansion@example.com"

# A query likely to have 0 results on Arxiv/S2 initially, forcing expansion
# "sdlfkjsdlfkjsdflkjsdflkjsdf" (Nonsense)
RARE_QUERY = "sdlfkjsdlfkjsdflkjsdflkjsdf"

def get_auth_token():
    print(f"Logging in as {TEST_EMAIL}...")
    try:
        # Register first
        reg_data = json.dumps({"email": TEST_EMAIL, "password": "securepassword"}).encode('utf-8')
        reg_req = urllib.request.Request(f"{BASE_URL}/auth/register", method="POST", data=reg_data)
        reg_req.add_header('Content-Type', 'application/json')
        try:
            urllib.request.urlopen(reg_req, timeout=10)
            print(f"Registered new user: {TEST_EMAIL}")
        except urllib.error.HTTPError as e:
            if e.code == 400:
                # Check if it's actually "already registered" vs other validation error
                try:
                    error_body = json.load(e)
                    # Adjust based on your API's actual error response structure
                    if "already" not in str(error_body).lower() and "exists" not in str(error_body).lower():
                        print(f"Registration failed (not 'already exists'): {error_body}")
                except:
                    pass  # If we can't parse, proceed anyway
            else:
                raise

        # Verify email manually
        with engine.begin() as conn:
            conn.execute(text("UPDATE users SET email_verified = TRUE WHERE email = :email"), {"email": TEST_EMAIL})

        # Then login
        data = json.dumps({"email": TEST_EMAIL, "password": "securepassword"}).encode('utf-8')
        req = urllib.request.Request(f"{BASE_URL}/auth/login", method="POST", data=data)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            body = json.load(response)
            return body.get("access_token")
    except Exception as e:
        print(f"Login Exception: {e}")
        return None

def make_request(method, url, data=None, token=None):
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header('Content-Type', 'application/json')
        if token:
             req.add_header('Authorization', f"Bearer {token}")
             
        if data:
            json_data = json.dumps(data).encode('utf-8')
            req.data = json_data
            
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 0, None

def run_rare_test(token: str):
    label = "Rare Query (Force Expansion)"
    query = RARE_QUERY
    print(f"\n--- TEST: {label} ('{query}') ---")
    
    task_id = str(uuid.uuid4())
    stop_event = threading.Event()
    
    final_stats = {"queries_total": 0, "progress_captured": False}
    
    def poll():
        while not stop_event.is_set():
            try:
                status, data = make_request("GET", f"{BASE_URL}/research/progress/{task_id}", token=token)
                if status == 200 and data:
                    final_stats["progress_captured"] = True
                    phase = data.get('phase')
                    q_comp = data.get('queries_completed', '?')
                    q_tot = data.get('queries_total', '?')
                    p_found = data.get('papers_found', 0)
                    
                    if not phase:
                         print("[Warning] 'phase' missing in progress data")
                    
                    print(f"[Progress] {phase} | Q: {q_comp}/{q_tot} | P: {p_found}")
                    
                    if data.get('queries_total'):
                        final_stats["queries_total"] = data['queries_total']
                        
                    if phase in ["COMPLETED", "FAILED"]:
                        break
            except Exception as e:
                print(f"[Progress Poll Error] {e}")
            time.sleep(1)

    t = threading.Thread(target=poll)
    t.start()
    
    print(f"Starting research task: {task_id}")
    try:
        status, result = make_request("POST", f"{BASE_URL}/research/", {
            "query": query,
            "audience": "phd",
            "task_id": task_id
        }, token=token)
        
        stop_event.set()
        t.join()
        
        if status == 200 and result:
            print("Research Request Returned.")
            data = result.get("data", {})
            papers = data.get("papers", [])
            
            # CHECK 1: Did we expand?
            # We check if progress showed > 1 total queries
            if not final_stats["progress_captured"]:
                 print("⚠️ No progress captured (possible endpoint/auth failure). Cannot verify expansion logic.")
            elif final_stats["queries_total"] > 1:
                print(f"✅ SUCCESS: Expansion triggered (Total Queries: {final_stats['queries_total']})")
            else:
                print(f"❌ FAILURE: No expansion triggered (Total Queries: {final_stats['queries_total']})")
            
        else:
            print(f"Request Failed: {status}")

    except Exception as e:
        stop_event.set()
        t.join()
        print(f"Test Exception: {e}")

if __name__ == "__main__":
    token = get_auth_token()
    if token:
        run_rare_test(token)
    else:
        print("Login failed")
