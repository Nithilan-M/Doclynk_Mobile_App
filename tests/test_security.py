"""
Security Testing Script for MediCare Application
=================================================
This script tests rate limiting and security features.
Only use this on YOUR OWN applications that you have permission to test.

Tests:
1. Rate limiting on login endpoint
2. Rate limiting on registration endpoint  
3. Account lockout after failed attempts
"""

import requests
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# ANSI Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_banner():
    print(f"""
{BLUE}╔══════════════════════════════════════════════════════════╗
║       MediCare Security Testing Suite                    ║
║       Rate Limiting & Security Feature Verification      ║
╚══════════════════════════════════════════════════════════╝{RESET}
    """)


def test_rate_limiting(base_url, endpoint, num_requests=10):
    """
    Test rate limiting by sending multiple requests rapidly.
    Expected: After 5 requests/minute, should get 429 Too Many Requests
    """
    print(f"\n{YELLOW}[TEST] Rate Limiting on {endpoint}{RESET}")
    print(f"Sending {num_requests} rapid requests...")
    
    url = f"{base_url}{endpoint}"
    results = {"success": 0, "rate_limited": 0, "errors": 0}
    
    for i in range(num_requests):
        try:
            if endpoint == "/login":
                response = requests.post(url, data={
                    "email": f"test{i}@example.com",
                    "password": "wrongpassword123"
                }, allow_redirects=False, timeout=10)
            elif endpoint == "/register":
                response = requests.post(url, data={
                    "role": "patient",
                    "name": f"Test User {i}",
                    "email": f"test{i}_{int(time.time())}@example.com",
                    "password": "TestPass123"
                }, allow_redirects=False, timeout=10)
            else:
                response = requests.get(url, timeout=10)
            
            if response.status_code == 429:
                results["rate_limited"] += 1
                print(f"  Request {i+1}: {RED}429 RATE LIMITED ✓{RESET}")
            elif response.status_code in [200, 302]:
                results["success"] += 1
                print(f"  Request {i+1}: {GREEN}200 OK{RESET}")
            else:
                results["errors"] += 1
                print(f"  Request {i+1}: {YELLOW}{response.status_code}{RESET}")
                
        except requests.exceptions.RequestException as e:
            results["errors"] += 1
            print(f"  Request {i+1}: {RED}ERROR - {str(e)[:50]}{RESET}")
        
        # Small delay to avoid overwhelming
        time.sleep(0.1)
    
    # Analysis
    print(f"\n{BLUE}Results:{RESET}")
    print(f"  Successful: {results['success']}")
    print(f"  Rate Limited (429): {results['rate_limited']}")
    print(f"  Errors: {results['errors']}")
    
    if results["rate_limited"] > 0:
        print(f"\n{GREEN}✓ PASS: Rate limiting is working!{RESET}")
        return True
    else:
        print(f"\n{RED}✗ FAIL: Rate limiting may not be configured correctly{RESET}")
        return False


def test_concurrent_requests(base_url, endpoint, num_workers=10):
    """
    Test with concurrent requests to simulate multiple users.
    """
    print(f"\n{YELLOW}[TEST] Concurrent Request Load Test on {endpoint}{RESET}")
    print(f"Sending {num_workers} concurrent requests...")
    
    url = f"{base_url}{endpoint}"
    results = {"success": 0, "rate_limited": 0, "errors": 0}
    
    def make_request(worker_id):
        try:
            response = requests.post(url, data={
                "email": f"concurrent{worker_id}@example.com",
                "password": "wrongpassword"
            }, allow_redirects=False, timeout=10)
            return response.status_code
        except:
            return -1
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(make_request, i) for i in range(num_workers)]
        for future in as_completed(futures):
            status = future.result()
            if status == 429:
                results["rate_limited"] += 1
            elif status in [200, 302]:
                results["success"] += 1
            else:
                results["errors"] += 1
    
    print(f"\n{BLUE}Concurrent Test Results:{RESET}")
    print(f"  Successful: {results['success']}")
    print(f"  Rate Limited: {results['rate_limited']}")
    print(f"  Errors: {results['errors']}")
    
    return results["rate_limited"] > 0


def test_account_lockout(base_url, test_email="lockout_test@example.com"):
    """
    Test account lockout after 5 failed login attempts.
    """
    print(f"\n{YELLOW}[TEST] Account Lockout (5 failed attempts = 15min lock){RESET}")
    print(f"Testing with email: {test_email}")
    
    url = f"{base_url}/login"
    
    for i in range(7):
        try:
            response = requests.post(url, data={
                "email": test_email,
                "password": "wrongpassword"
            }, timeout=10)
            
            if "locked" in response.text.lower():
                print(f"  Attempt {i+1}: {GREEN}ACCOUNT LOCKED ✓{RESET}")
                print(f"\n{GREEN}✓ PASS: Account lockout is working!{RESET}")
                return True
            else:
                print(f"  Attempt {i+1}: {YELLOW}Login failed (not locked yet){RESET}")
                
        except requests.exceptions.RequestException as e:
            print(f"  Attempt {i+1}: {RED}ERROR{RESET}")
        
        time.sleep(0.2)
    
    print(f"\n{RED}✗ Account lockout may need database columns configured{RESET}")
    return False


def test_security_headers(base_url):
    """
    Test that security headers are present.
    """
    print(f"\n{YELLOW}[TEST] Security Headers{RESET}")
    
    try:
        response = requests.get(f"{base_url}/login", timeout=10)
        headers = response.headers
        
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": None,  # Just check presence
            "Strict-Transport-Security": None,
        }
        
        all_present = True
        for header, expected in security_headers.items():
            value = headers.get(header)
            if value:
                if expected and expected not in value:
                    print(f"  {header}: {YELLOW}Present but unexpected value{RESET}")
                    all_present = False
                else:
                    print(f"  {header}: {GREEN}✓ Present{RESET}")
            else:
                print(f"  {header}: {RED}✗ Missing{RESET}")
                all_present = False
        
        if all_present:
            print(f"\n{GREEN}✓ PASS: All security headers present!{RESET}")
        else:
            print(f"\n{YELLOW}⚠ Some security headers missing (may be OK in dev){RESET}")
            
        return all_present
        
    except requests.exceptions.RequestException as e:
        print(f"{RED}Error: {e}{RESET}")
        return False


def run_all_tests(base_url):
    """Run all security tests."""
    print_banner()
    print(f"Target: {base_url}")
    print("=" * 60)
    
    results = {
        "rate_limiting_login": test_rate_limiting(base_url, "/login", 8),
        "rate_limiting_register": test_rate_limiting(base_url, "/register", 8),
        "concurrent_load": test_concurrent_requests(base_url, "/login", 15),
        "security_headers": test_security_headers(base_url),
        # "account_lockout": test_account_lockout(base_url),  # Uncomment if DB is set up
    }
    
    # Summary
    print("\n" + "=" * 60)
    print(f"{BLUE}TEST SUMMARY{RESET}")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {test}: {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"\n{GREEN}🎉 All security features working correctly!{RESET}")
    else:
        print(f"\n{YELLOW}⚠ Some tests failed - review configuration{RESET}")


if __name__ == "__main__":
    # Default to localhost, or pass URL as argument
    if len(sys.argv) > 1:
        target_url = sys.argv[1].rstrip("/")
    else:
        target_url = "http://localhost:5000"
    
    print(f"\n{YELLOW}⚠ WARNING: Only run this on applications you own!{RESET}")
    print(f"Target URL: {target_url}")
    
    confirm = input("\nProceed with security testing? (yes/no): ")
    if confirm.lower() in ["yes", "y"]:
        run_all_tests(target_url)
    else:
        print("Aborted.")
