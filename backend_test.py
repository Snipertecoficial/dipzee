"""Comprehensive backend API tests for Dipzee."""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://dipzee-mvp.preview.emergentagent.com/api"

class DipzeeAPITester:
    def __init__(self):
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.test_email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        self.test_password = "TestPass123!"
        self.demo_email = "demo@dipzee.com"
        self.demo_password = "Demo1234!"

    def log(self, category, name, passed, message="", expected="", actual=""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        result = {
            "category": category,
            "name": name,
            "passed": passed,
            "message": message,
            "expected": expected,
            "actual": actual
        }
        self.test_results.append(result)
        
        print(f"\n{status} [{category}] {name}")
        if message:
            print(f"  → {message}")
        if not passed and expected:
            print(f"  Expected: {expected}")
            print(f"  Actual: {actual}")

    def test_endpoint(self, category, name, method, endpoint, expected_status, 
                     data=None, params=None, check_response=None):
        """Generic endpoint test"""
        url = f"{BASE_URL}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                self.log(category, name, False, f"Unknown method: {method}")
                return None

            passed = response.status_code == expected_status
            
            if passed and check_response:
                try:
                    resp_data = response.json()
                    check_result = check_response(resp_data)
                    if not check_result:
                        passed = False
                        self.log(category, name, False, "Response validation failed", 
                               "Valid response structure", str(resp_data))
                        return None
                except Exception as e:
                    passed = False
                    self.log(category, name, False, f"Response check error: {str(e)}")
                    return None

            if passed:
                self.log(category, name, True, f"Status: {response.status_code}")
                try:
                    return response.json()
                except:
                    return {}
            else:
                try:
                    error_detail = response.json()
                except:
                    error_detail = response.text[:200]
                self.log(category, name, False, 
                       f"Status code mismatch", 
                       f"{expected_status}", 
                       f"{response.status_code} - {error_detail}")
                return None

        except requests.exceptions.Timeout:
            self.log(category, name, False, "Request timeout (30s)")
            return None
        except Exception as e:
            self.log(category, name, False, f"Exception: {str(e)}")
            return None

    def test_auth(self):
        """Test authentication endpoints"""
        print("\n" + "="*60)
        print("TESTING AUTHENTICATION")
        print("="*60)

        # Try demo account first
        print("Attempting to login with demo account...")
        result = self.test_endpoint(
            "AUTH", "POST /auth/login (demo account)",
            "POST", "auth/login", 200,
            data={
                "email": self.demo_email,
                "password": self.demo_password
            },
            check_response=lambda r: "access_token" in r and "user" in r
        )
        
        if result:
            print("  ✓ Demo account exists, using it for tests")
            self.token = result.get("access_token")
            self.user_id = result.get("user", {}).get("id")
            self.test_email = self.demo_email
            self.test_password = self.demo_password
        else:
            print("  Demo account not found, creating new test account...")
            # Test registration
            result = self.test_endpoint(
                "AUTH", "POST /auth/register",
                "POST", "auth/register", 200,
                data={
                    "email": self.test_email,
                    "password": self.test_password,
                    "locale": "en",
                    "currency": "CAD"
                },
                check_response=lambda r: "access_token" in r and "user" in r
            )
            
            if result:
                self.token = result.get("access_token")
                self.user_id = result.get("user", {}).get("id")

        # Test duplicate registration
        self.test_endpoint(
            "AUTH", "POST /auth/register (duplicate)",
            "POST", "auth/register", 400,
            data={
                "email": self.test_email,
                "password": self.test_password
            }
        )

        # Test login with wrong password
        self.test_endpoint(
            "AUTH", "POST /auth/login (wrong password)",
            "POST", "auth/login", 401,
            data={
                "email": self.test_email,
                "password": "WrongPassword123!"
            }
        )

        # Test login with correct credentials
        result = self.test_endpoint(
            "AUTH", "POST /auth/login",
            "POST", "auth/login", 200,
            data={
                "email": self.test_email,
                "password": self.test_password
            },
            check_response=lambda r: "access_token" in r and "user" in r
        )
        
        if result:
            self.token = result.get("access_token")

        # Test GET /auth/me
        self.test_endpoint(
            "AUTH", "GET /auth/me",
            "GET", "auth/me", 200,
            check_response=lambda r: r.get("email") == self.test_email
        )

        # Test PUT /auth/profile
        result = self.test_endpoint(
            "AUTH", "PUT /auth/profile",
            "PUT", "auth/profile", 200,
            data={
                "locale": "fr",
                "currency": "USD",
                "default_alert_prefs": {"email": False, "in_app": True}
            },
            check_response=lambda r: r.get("locale") == "fr" and r.get("currency") == "USD"
        )

    def test_scoring(self):
        """Test scoring endpoints"""
        print("\n" + "="*60)
        print("TESTING SCORING & ASSETS")
        print("="*60)

        # Test GET /score/{ticker} for T.TO (TELUS)
        result = self.test_endpoint(
            "SCORING", "GET /score/T.TO",
            "GET", "score/T.TO", 200,
            check_response=lambda r: (
                "score" in r and 
                "sub_scores" in r and 
                "classification" in r and 
                "flags" in r and
                "explanation" in r and
                r.get("ticker") == "T.TO"
            )
        )
        
        if result:
            score = result.get("score")
            classification = result.get("classification")
            flags = result.get("flags", {})
            print(f"  T.TO Score: {score}, Classification: {classification}")
            print(f"  Flags: buy_zone={flags.get('buy_zone')}, sell_zone={flags.get('sell_zone')}, income={flags.get('income')}")

        # Test GET /score/{ticker} for AAPL
        result = self.test_endpoint(
            "SCORING", "GET /score/AAPL",
            "GET", "score/AAPL", 200,
            check_response=lambda r: (
                "score" in r and 
                r.get("ticker") == "AAPL"
            )
        )
        
        if result:
            score = result.get("score")
            classification = result.get("classification")
            print(f"  AAPL Score: {score}, Classification: {classification}")

    def test_assets(self):
        """Test asset endpoints"""
        print("\n" + "="*60)
        print("TESTING ASSET ENDPOINTS")
        print("="*60)

        # Test POST /assets/refresh/{ticker}
        result = self.test_endpoint(
            "ASSETS", "POST /assets/refresh/T.TO",
            "POST", "assets/refresh/T.TO", 200,
            check_response=lambda r: (
                r.get("ticker") == "T.TO" and
                "price" in r and
                "score" in r
            )
        )

        # Test GET /assets/{ticker}
        self.test_endpoint(
            "ASSETS", "GET /assets/T.TO",
            "GET", "assets/T.TO", 200,
            check_response=lambda r: r.get("ticker") == "T.TO"
        )

        # Test GET /assets/search
        result = self.test_endpoint(
            "ASSETS", "GET /assets/search?q=apple",
            "GET", "assets/search", 200,
            params={"q": "apple"},
            check_response=lambda r: "results" in r and len(r.get("results", [])) > 0
        )
        
        if result:
            print(f"  Found {len(result.get('results', []))} results for 'apple'")

    def test_watchlist(self):
        """Test watchlist endpoints with Free-plan limits"""
        print("\n" + "="*60)
        print("TESTING WATCHLIST (Free plan limit: 10)")
        print("="*60)

        # Test GET /watchlist (empty)
        self.test_endpoint(
            "WATCHLIST", "GET /watchlist (empty)",
            "GET", "watchlist", 200,
            check_response=lambda r: isinstance(r, list)
        )

        # Test POST /watchlist (add T.TO)
        self.test_endpoint(
            "WATCHLIST", "POST /watchlist (T.TO)",
            "POST", "watchlist", 200,
            data={"ticker": "T.TO"},
            check_response=lambda r: r.get("ticker") == "T.TO"
        )

        # Test POST /watchlist (duplicate)
        self.test_endpoint(
            "WATCHLIST", "POST /watchlist (duplicate)",
            "POST", "watchlist", 400,
            data={"ticker": "T.TO"}
        )

        # Add more tickers to test limit
        test_tickers = ["AAPL", "KO", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM"]
        for ticker in test_tickers:
            self.test_endpoint(
                "WATCHLIST", f"POST /watchlist ({ticker})",
                "POST", "watchlist", 200,
                data={"ticker": ticker},
                check_response=lambda r: "ticker" in r
            )

        # Test limit enforcement (11th item should fail with 403)
        result = self.test_endpoint(
            "WATCHLIST", "POST /watchlist (limit test - 11th item)",
            "POST", "watchlist", 403,
            data={"ticker": "BAC"}
        )

        # Test GET /watchlist (should have 10 items)
        result = self.test_endpoint(
            "WATCHLIST", "GET /watchlist (full)",
            "GET", "watchlist", 200,
            check_response=lambda r: isinstance(r, list) and len(r) == 10
        )
        
        if result:
            print(f"  Watchlist has {len(result)} items (limit: 10)")

        # Test DELETE /watchlist/{ticker}
        self.test_endpoint(
            "WATCHLIST", "DELETE /watchlist/AAPL",
            "DELETE", "watchlist/AAPL", 200,
            check_response=lambda r: r.get("ok") == True
        )

        # Test DELETE /watchlist/{ticker} (not in watchlist)
        self.test_endpoint(
            "WATCHLIST", "DELETE /watchlist/INVALID",
            "DELETE", "watchlist/INVALID", 404
        )

    def test_alerts(self):
        """Test alerts endpoints with Free-plan limits"""
        print("\n" + "="*60)
        print("TESTING ALERTS (Free plan limit: 3 active)")
        print("="*60)

        # Test GET /alerts (empty)
        self.test_endpoint(
            "ALERTS", "GET /alerts (empty)",
            "GET", "alerts", 200,
            check_response=lambda r: isinstance(r, list)
        )

        # Test POST /alerts (buy_zone)
        alert1 = self.test_endpoint(
            "ALERTS", "POST /alerts (buy_zone)",
            "POST", "alerts", 200,
            data={
                "ticker": "T.TO",
                "type": "buy_zone",
                "params": {}
            },
            check_response=lambda r: r.get("type") == "buy_zone" and r.get("active") == True
        )
        alert1_id = alert1.get("id") if alert1 else None

        # Test POST /alerts (price_above)
        alert2 = self.test_endpoint(
            "ALERTS", "POST /alerts (price_above)",
            "POST", "alerts", 200,
            data={
                "ticker": "AAPL",
                "type": "price_above",
                "params": {"value": 150.0}
            },
            check_response=lambda r: r.get("type") == "price_above"
        )
        alert2_id = alert2.get("id") if alert2 else None

        # Test POST /alerts (score_threshold)
        alert3 = self.test_endpoint(
            "ALERTS", "POST /alerts (score_threshold)",
            "POST", "alerts", 200,
            data={
                "ticker": "KO",
                "type": "score_threshold",
                "params": {"value": 70}
            },
            check_response=lambda r: r.get("type") == "score_threshold"
        )
        alert3_id = alert3.get("id") if alert3 else None

        # Test limit enforcement (4th active alert should fail with 403)
        self.test_endpoint(
            "ALERTS", "POST /alerts (limit test - 4th active)",
            "POST", "alerts", 403,
            data={
                "ticker": "MSFT",
                "type": "sell_zone",
                "params": {}
            }
        )

        # Test GET /alerts (should have 3 active)
        result = self.test_endpoint(
            "ALERTS", "GET /alerts (3 active)",
            "GET", "alerts", 200,
            check_response=lambda r: isinstance(r, list) and len(r) == 3
        )

        # Test PUT /alerts/{alert_id} (deactivate)
        if alert1_id:
            self.test_endpoint(
                "ALERTS", f"PUT /alerts/{alert1_id} (deactivate)",
                "PUT", f"alerts/{alert1_id}", 200,
                data={"active": False},
                check_response=lambda r: r.get("active") == False
            )

        # Test PUT /alerts/{alert_id} (update params)
        if alert2_id:
            self.test_endpoint(
                "ALERTS", f"PUT /alerts/{alert2_id} (update params)",
                "PUT", f"alerts/{alert2_id}", 200,
                data={"params": {"value": 200.0}},
                check_response=lambda r: r.get("params", {}).get("value") == 200.0
            )

        # Test DELETE /alerts/{alert_id}
        if alert3_id:
            self.test_endpoint(
                "ALERTS", f"DELETE /alerts/{alert3_id}",
                "DELETE", f"alerts/{alert3_id}", 200,
                check_response=lambda r: r.get("ok") == True
            )

    def test_alert_triggering(self):
        """Test edge-triggered alert firing"""
        print("\n" + "="*60)
        print("TESTING ALERT TRIGGERING")
        print("="*60)

        # Create a price_above alert with a very low value (should trigger immediately)
        alert = self.test_endpoint(
            "ALERT_TRIGGER", "POST /alerts (price_above with low value)",
            "POST", "alerts", 200,
            data={
                "ticker": "AAPL",
                "type": "price_above",
                "params": {"value": 1.0}  # Very low value, should trigger
            },
            check_response=lambda r: r.get("type") == "price_above"
        )
        
        if not alert:
            print("  ⚠️  Could not create alert for triggering test")
            return

        # Refresh the asset to trigger the alert
        time.sleep(1)  # Brief pause
        self.test_endpoint(
            "ALERT_TRIGGER", "POST /assets/refresh/AAPL (trigger alert)",
            "POST", "assets/refresh/AAPL", 200,
            check_response=lambda r: r.get("ticker") == "AAPL"
        )

        # Check notifications
        time.sleep(1)  # Brief pause for alert processing
        result = self.test_endpoint(
            "ALERT_TRIGGER", "GET /notifications (check for alert event)",
            "GET", "notifications", 200,
            check_response=lambda r: "events" in r and "unread" in r
        )
        
        if result:
            events = result.get("events", [])
            unread = result.get("unread", 0)
            print(f"  Found {len(events)} notification events, {unread} unread")
            if len(events) > 0:
                print(f"  Latest event: {events[0].get('type')} for {events[0].get('ticker')}")

    def test_notifications(self):
        """Test notifications endpoints"""
        print("\n" + "="*60)
        print("TESTING NOTIFICATIONS")
        print("="*60)

        # Test GET /notifications
        result = self.test_endpoint(
            "NOTIFICATIONS", "GET /notifications",
            "GET", "notifications", 200,
            check_response=lambda r: "events" in r and "unread" in r
        )
        
        event_id = None
        if result and len(result.get("events", [])) > 0:
            event_id = result["events"][0].get("id")

        # Test POST /notifications/{event_id}/read
        if event_id:
            self.test_endpoint(
                "NOTIFICATIONS", f"POST /notifications/{event_id}/read",
                "POST", f"notifications/{event_id}/read", 200,
                check_response=lambda r: r.get("ok") == True
            )

        # Test POST /notifications/read-all
        self.test_endpoint(
            "NOTIFICATIONS", "POST /notifications/read-all",
            "POST", "notifications/read-all", 200,
            check_response=lambda r: r.get("ok") == True
        )

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Group by category
        categories = {}
        for result in self.test_results:
            cat = result["category"]
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0}
            if result["passed"]:
                categories[cat]["passed"] += 1
            else:
                categories[cat]["failed"] += 1
        
        print("\nBy category:")
        for cat, stats in categories.items():
            total = stats["passed"] + stats["failed"]
            print(f"  {cat}: {stats['passed']}/{total} passed")
        
        # List failed tests
        failed = [r for r in self.test_results if not r["passed"]]
        if failed:
            print("\nFailed tests:")
            for r in failed:
                print(f"  ❌ [{r['category']}] {r['name']}")
                if r["message"]:
                    print(f"     {r['message']}")

def main():
    tester = DipzeeAPITester()
    
    try:
        # Run all test suites
        tester.test_auth()
        tester.test_scoring()
        tester.test_assets()
        tester.test_watchlist()
        tester.test_alerts()
        tester.test_alert_triggering()
        tester.test_notifications()
        
        # Print summary
        tester.print_summary()
        
        # Return exit code based on results
        if tester.tests_passed == tester.tests_run:
            print("\n✅ All tests passed!")
            return 0
        else:
            print(f"\n❌ {tester.tests_run - tester.tests_passed} test(s) failed")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        tester.print_summary()
        return 1
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
