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

    def test_screener(self):
        """Test screener endpoints (Phase 3)"""
        print("\n" + "="*60)
        print("TESTING SCREENER (Phase 3)")
        print("="*60)

        # Test POST /screener/refresh with limit
        result = self.test_endpoint(
            "SCREENER", "POST /screener/refresh?limit=8",
            "POST", "screener/refresh", 200,
            params={"limit": 8},
            check_response=lambda r: "refreshed" in r and r.get("refreshed", 0) > 0
        )
        
        if result:
            print(f"  Refreshed {result.get('refreshed')} tickers")

        # Wait a moment for refresh to complete
        time.sleep(2)

        # Test GET /screener (no filters)
        result = self.test_endpoint(
            "SCREENER", "GET /screener (no filters)",
            "GET", "screener", 200,
            check_response=lambda r: "results" in r and "count" in r
        )
        
        if result:
            results = result.get("results", [])
            count = result.get("count", 0)
            print(f"  Found {count} results")
            if len(results) > 1:
                # Check if sorted by score desc
                scores = [r.get("score") for r in results if r.get("score") is not None]
                is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
                if is_sorted:
                    print(f"  ✓ Results sorted by score descending")
                else:
                    print(f"  ⚠️  Results may not be sorted correctly")

        # Test GET /screener with min_dividend filter
        result = self.test_endpoint(
            "SCREENER", "GET /screener?min_dividend=0.03",
            "GET", "screener", 200,
            params={"min_dividend": 0.03},
            check_response=lambda r: "results" in r and "count" in r
        )
        
        if result:
            results = result.get("results", [])
            print(f"  Found {len(results)} results with min_dividend=0.03")
            # Verify filter works
            if results:
                dividends = [r.get("dividend_yield") for r in results if r.get("dividend_yield") is not None]
                if dividends and all(d >= 0.03 for d in dividends):
                    print(f"  ✓ All results have dividend_yield >= 0.03")

        # Test GET /screener with classification filter
        result = self.test_endpoint(
            "SCREENER", "GET /screener?classification=buy",
            "GET", "screener", 200,
            params={"classification": "buy"},
            check_response=lambda r: "results" in r and "count" in r
        )
        
        if result:
            results = result.get("results", [])
            print(f"  Found {len(results)} results with classification=buy")
            # Verify filter works
            if results:
                classifications = [r.get("classification") for r in results]
                if all(c == "buy" for c in classifications):
                    print(f"  ✓ All results have classification=buy")

        # Test GET /screener/sectors
        result = self.test_endpoint(
            "SCREENER", "GET /screener/sectors",
            "GET", "screener/sectors", 200,
            check_response=lambda r: "sectors" in r and isinstance(r.get("sectors"), list)
        )
        
        if result:
            sectors = result.get("sectors", [])
            print(f"  Found {len(sectors)} sectors: {sectors[:5]}")

    def test_billing(self):
        """Test Stripe billing endpoints (Phase 3) - Updated for 3 paid plans"""
        print("\n" + "="*60)
        print("TESTING BILLING (3 Paid Plans: Starter, Pro, Investor)")
        print("="*60)

        # Test GET /billing/config - should return 6 packages (3 plans x 2 billing cycles)
        result = self.test_endpoint(
            "BILLING", "GET /billing/config",
            "GET", "billing/config", 200,
            check_response=lambda r: (
                "configured" in r and 
                "packages" in r and 
                "currency" in r and
                len(r.get("packages", {})) == 6
            )
        )
        
        if result:
            configured = result.get("configured")
            packages = result.get("packages", {})
            currency = result.get("currency")
            print(f"  Configured: {configured}, Currency: {currency}")
            print(f"  Packages ({len(packages)}): {list(packages.keys())}")
            
            # Verify exact prices
            expected_prices = {
                "starter_monthly": 4.97,
                "starter_annual": 47.71,
                "pro_monthly": 12.97,
                "pro_annual": 124.51,
                "investor_monthly": 24.99,
                "investor_annual": 239.90
            }
            
            for pkg_id, expected_amount in expected_prices.items():
                if pkg_id in packages:
                    actual_amount = packages[pkg_id].get("amount")
                    if actual_amount == expected_amount:
                        print(f"  ✓ {pkg_id}: ${actual_amount}")
                    else:
                        print(f"  ❌ {pkg_id}: expected ${expected_amount}, got ${actual_amount}")
                else:
                    print(f"  ❌ {pkg_id}: missing from packages")

        # Test POST /billing/checkout with valid packages
        valid_packages = ["starter_monthly", "pro_monthly", "investor_monthly", "starter_annual", "pro_annual", "investor_annual"]
        
        for pkg_id in valid_packages[:3]:  # Test first 3 to avoid too many Stripe sessions
            result = self.test_endpoint(
                "BILLING", f"POST /billing/checkout ({pkg_id})",
                "POST", "billing/checkout", 200,
                data={
                    "package_id": pkg_id,
                    "origin_url": "https://dipzee-mvp.preview.emergentagent.com"
                },
                check_response=lambda r: (
                    "url" in r and 
                    "session_id" in r and
                    r.get("session_id", "").startswith("cs_test_")
                )
            )
            
            if result:
                session_id = result.get("session_id")
                print(f"  ✓ Checkout session created: {session_id}")

        # Test POST /billing/checkout with invalid packages
        invalid_packages = ["pro_weekly", "free_monthly", "invalid_package"]
        
        for pkg_id in invalid_packages:
            self.test_endpoint(
                "BILLING", f"POST /billing/checkout ({pkg_id} - invalid)",
                "POST", "billing/checkout", 400,
                data={
                    "package_id": pkg_id,
                    "origin_url": "https://dipzee-mvp.preview.emergentagent.com"
                }
            )

    def test_regression_endpoints(self):
        """Test regression - ensure existing endpoints still work"""
        print("\n" + "="*60)
        print("TESTING REGRESSION (Existing Endpoints)")
        print("="*60)

        # Test GET /watchlist
        self.test_endpoint(
            "REGRESSION", "GET /watchlist",
            "GET", "watchlist", 200,
            check_response=lambda r: isinstance(r, list)
        )

        # Test GET /alerts
        self.test_endpoint(
            "REGRESSION", "GET /alerts",
            "GET", "alerts", 200,
            check_response=lambda r: isinstance(r, list)
        )

        # Test GET /screener (top opportunities)
        result = self.test_endpoint(
            "REGRESSION", "GET /screener?limit=10",
            "GET", "screener", 200,
            params={"limit": 10},
            check_response=lambda r: "results" in r and "count" in r
        )
        
        if result:
            print(f"  ✓ Screener returned {len(result.get('results', []))} results")

        # Test GET /news/market
        result = self.test_endpoint(
            "REGRESSION", "GET /news/market",
            "GET", "news/market", 200,
            check_response=lambda r: "news" in r and isinstance(r.get("news"), list)
        )
        
        if result:
            print(f"  ✓ Market news returned {len(result.get('news', []))} items")

    def test_admin_endpoints(self):
        """Test admin endpoints with superadmin credentials"""
        print("\n" + "="*60)
        print("TESTING ADMIN ENDPOINTS (Superadmin)")
        print("="*60)

        # Login as superadmin
        superadmin_email = "douglas@snipertec.com.br"
        superadmin_password = "Admin213021#"
        
        result = self.test_endpoint(
            "ADMIN", "POST /auth/login (superadmin)",
            "POST", "auth/login", 200,
            data={
                "email": superadmin_email,
                "password": superadmin_password
            },
            check_response=lambda r: "access_token" in r and "user" in r
        )
        
        if not result:
            print("  ⚠️  Could not login as superadmin, skipping admin tests")
            return
        
        # Save current token and switch to superadmin
        old_token = self.token
        self.token = result.get("access_token")
        user = result.get("user", {})
        print(f"  ✓ Superadmin logged in: {user.get('email')}")
        print(f"    Role: {user.get('role')}, Plan: {user.get('plan')}")

        # Test GET /admin/stats
        result = self.test_endpoint(
            "ADMIN", "GET /admin/stats",
            "GET", "admin/stats", 200,
            check_response=lambda r: (
                "users_total" in r and
                "plan_counts" in r and
                "assets_total" in r and
                "alerts_total" in r
            )
        )
        
        if result:
            print(f"  ✓ Admin stats:")
            print(f"    Users: {result.get('users_total')}")
            print(f"    Plan counts: {result.get('plan_counts')}")
            print(f"    Assets: {result.get('assets_total')}")
            print(f"    Alerts: {result.get('alerts_total')}")

        # Test POST /admin/run-daily-refresh
        result = self.test_endpoint(
            "ADMIN", "POST /admin/run-daily-refresh",
            "POST", "admin/run-daily-refresh", 200,
            check_response=lambda r: "ok" in r or "refreshed" in r or "message" in r
        )
        
        if result:
            print(f"  ✓ Manual refresh triggered: {result}")

        # Restore original token
        self.token = old_token

    def test_finnhub_integration(self):
        """Test Finnhub integration features (NEW)"""
        print("\n" + "="*60)
        print("TESTING FINNHUB INTEGRATION (NEW)")
        print("="*60)

        # Test 1: Superadmin login
        print("\n--- Testing Superadmin Account ---")
        superadmin_email = "douglas@snipertec.com.br"
        superadmin_password = "Admin213021#"
        
        result = self.test_endpoint(
            "FINNHUB", "POST /auth/login (superadmin)",
            "POST", "auth/login", 200,
            data={
                "email": superadmin_email,
                "password": superadmin_password
            },
            check_response=lambda r: "access_token" in r and "user" in r
        )
        
        superadmin_token = None
        if result:
            superadmin_token = result.get("access_token")
            user = result.get("user", {})
            print(f"  ✓ Superadmin logged in: {user.get('email')}")
            print(f"  Role: {user.get('role')}, Plan: {user.get('plan')}, Currency: {user.get('currency')}")
        
        # Test GET /auth/me for superadmin
        if superadmin_token:
            old_token = self.token
            self.token = superadmin_token
            
            result = self.test_endpoint(
                "FINNHUB", "GET /auth/me (superadmin)",
                "GET", "auth/me", 200,
                check_response=lambda r: (
                    r.get("role") == "superadmin" and
                    r.get("plan") == "investor" and
                    r.get("currency") == "USD"
                )
            )
            
            if result:
                print(f"  ✓ Superadmin verified: role={result.get('role')}, plan={result.get('plan')}, currency={result.get('currency')}")
            
            self.token = old_token

        # Test 2: POST /assets/refresh/AAPL with Finnhub data
        print("\n--- Testing Finnhub Asset Refresh (AAPL) ---")
        result = self.test_endpoint(
            "FINNHUB", "POST /assets/refresh/AAPL",
            "POST", "assets/refresh/AAPL", 200,
            check_response=lambda r: (
                r.get("ticker") == "AAPL" and
                r.get("source") == "finnhub" and
                "change_pct" in r and
                isinstance(r.get("change_pct"), (int, float)) and
                "price" in r and
                "low_52w" in r and
                "high_52w" in r and
                "dividend_yield" in r and
                "target_mean" in r and
                "score" in r and
                "classification" in r
            )
        )
        
        if result:
            print(f"  ✓ AAPL data from Finnhub:")
            print(f"    Source: {result.get('source')}")
            print(f"    Price: {result.get('price')}")
            print(f"    Change %: {result.get('change_pct')}")
            print(f"    52w Low: {result.get('low_52w')}, High: {result.get('high_52w')}")
            print(f"    Dividend Yield: {result.get('dividend_yield')} (decimal)")
            print(f"    Target Mean: {result.get('target_mean')} (from yfinance)")
            print(f"    Score: {result.get('score')}, Classification: {result.get('classification')}")

        # Test 3: GET /assets/MSFT/news
        print("\n--- Testing Company News (MSFT) ---")
        result = self.test_endpoint(
            "FINNHUB", "GET /assets/MSFT/news",
            "GET", "assets/MSFT/news", 200,
            check_response=lambda r: (
                "news" in r and
                isinstance(r.get("news"), list) and
                len(r.get("news", [])) > 0
            )
        )
        
        if result:
            news = result.get("news", [])
            print(f"  ✓ Found {len(news)} news items for MSFT")
            if news:
                first = news[0]
                print(f"    First headline: {first.get('headline', '')[:60]}...")
                print(f"    URL: {first.get('url', '')[:60]}...")
                print(f"    Source: {first.get('source')}")

        # Test 4: GET /news/market
        print("\n--- Testing Market News ---")
        result = self.test_endpoint(
            "FINNHUB", "GET /news/market",
            "GET", "news/market", 200,
            check_response=lambda r: (
                "news" in r and
                isinstance(r.get("news"), list) and
                len(r.get("news", [])) > 0
            )
        )
        
        if result:
            news = result.get("news", [])
            print(f"  ✓ Found {len(news)} market news items")
            if news:
                first = news[0]
                print(f"    First headline: {first.get('headline', '')[:60]}...")

        # Test 5: GET /public/top-opportunities (NO AUTH)
        print("\n--- Testing Public Top Opportunities ---")
        old_token = self.token
        self.token = None  # No auth for public endpoint
        
        result = self.test_endpoint(
            "FINNHUB", "GET /public/top-opportunities?limit=8",
            "GET", "public/top-opportunities", 200,
            params={"limit": 8},
            check_response=lambda r: (
                "results" in r and
                isinstance(r.get("results"), list)
            )
        )
        
        if result:
            results = result.get("results", [])
            print(f"  ✓ Found {len(results)} top opportunities (public, no auth)")
            if len(results) > 1:
                # Check if sorted by score desc
                scores = [r.get("score") for r in results if r.get("score") is not None]
                is_sorted = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
                if is_sorted:
                    print(f"  ✓ Results sorted by score descending")
                    print(f"    Top 3 scores: {scores[:3]}")
                else:
                    print(f"  ⚠️  Results may not be sorted correctly")
        
        self.token = old_token

        # Test 6: Create 'news' type alert
        print("\n--- Testing News Alert Creation ---")
        result = self.test_endpoint(
            "FINNHUB", "POST /alerts (news type)",
            "POST", "alerts", 200,
            data={
                "ticker": "AAPL",
                "type": "news",
                "params": {}
            },
            check_response=lambda r: (
                r.get("type") == "news" and
                r.get("ticker") == "AAPL" and
                r.get("active") == True and
                "params" in r and
                "since" in r.get("params", {})
            )
        )
        
        if result:
            print(f"  ✓ News alert created for AAPL")
            print(f"    Alert ID: {result.get('id')}")
            print(f"    Params.since: {result.get('params', {}).get('since')} (timestamp)")

        # Test 7: New-user registration defaults currency to USD
        print("\n--- Testing Registration Currency Default ---")
        test_email_usd = f"test_usd_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        result = self.test_endpoint(
            "FINNHUB", "POST /auth/register (no currency)",
            "POST", "auth/register", 200,
            data={
                "email": test_email_usd,
                "password": "TestPass123!",
                "locale": "en"
                # Note: no currency field
            },
            check_response=lambda r: (
                "user" in r and
                r.get("user", {}).get("currency") == "USD"
            )
        )
        
        if result:
            user = result.get("user", {})
            print(f"  ✓ New user registered without currency field")
            print(f"    Default currency: {user.get('currency')} (expected: USD)")

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
        
        # Phase 3 tests
        tester.test_screener()
        tester.test_billing()
        
        # Regression tests
        tester.test_regression_endpoints()
        
        # Admin tests (with superadmin credentials)
        tester.test_admin_endpoints()
        
        # NEW: Finnhub integration tests
        tester.test_finnhub_integration()
        
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
