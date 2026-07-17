"""Comprehensive backend API tests for Dipzee feature gating and capabilities."""
import os
import requests
import sys
import uuid
from datetime import datetime

BASE_URL = os.environ.get("DIPZEE_TEST_BASE_URL", "http://localhost:8000/api")
SUPERADMIN_EMAIL = os.environ.get("SUPERADMIN_EMAIL")
SUPERADMIN_PASSWORD = os.environ.get("SUPERADMIN_PASSWORD")

class DipzeeAPITester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.superadmin_token = None
        self.test_user_id = None
        self.test_user_token = None
        self.test_position_id = None

    def log(self, msg, level="INFO"):
        print(f"[{level}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, params=None):
        """Run a single API test."""
        url = f"{BASE_URL}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}", "PASS")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}", "FAIL")
                try:
                    self.log(f"   Response: {response.json()}", "FAIL")
                except:
                    self.log(f"   Response: {response.text[:200]}", "FAIL")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}", "FAIL")
            return False, {}

    def test_plans_catalog(self):
        """Test GET /api/plans/catalog."""
        self.log("\n=== Testing Plans Catalog ===")
        success, response = self.run_test(
            "Plans Catalog",
            "GET",
            "plans/catalog",
            200
        )
        if success:
            plans = response.get("plans", {})
            if "starter" in plans and "pro" in plans and "investor" in plans:
                self.log("✅ All three plans present in catalog")
                # Check starter plan structure
                starter = plans.get("starter", {})
                if "features" in starter and "card_features" in starter:
                    self.log(f"✅ Starter plan has {len(starter['features'])} features")
                    self.log(f"   Features: {starter['features'][:5]}...")
                # Check investor plan
                investor = plans.get("investor", {})
                if "portfolio" in investor.get("features", []) and "backtest" in investor.get("features", []):
                    self.log("✅ Investor plan includes portfolio and backtest features")
                else:
                    self.log("❌ Investor plan missing portfolio or backtest features", "FAIL")
            else:
                self.log("❌ Missing plans in catalog", "FAIL")
        return success

    def test_superadmin_login(self):
        """Test superadmin login."""
        self.log("\n=== Testing Superadmin Login ===")
        if not SUPERADMIN_EMAIL or not SUPERADMIN_PASSWORD:
            self.log("SUPERADMIN_EMAIL/SUPERADMIN_PASSWORD not set — skipping.", "SKIP")
            return False
        success, response = self.run_test(
            "Superadmin Login",
            "POST",
            "auth/login",
            200,
            data={"email": SUPERADMIN_EMAIL, "password": SUPERADMIN_PASSWORD}
        )
        if success:
            self.superadmin_token = response.get("access_token")
            user = response.get("user", {})
            if user.get("role") == "superadmin" and user.get("plan") == "investor":
                self.log(f"✅ Superadmin logged in: {user.get('email')}, plan={user.get('plan')}, role={user.get('role')}")
            else:
                self.log(f"❌ Superadmin has wrong role or plan: role={user.get('role')}, plan={user.get('plan')}", "FAIL")
        return success

    def test_auth_me_capabilities(self):
        """Test GET /api/auth/me with superadmin - check capabilities."""
        self.log("\n=== Testing Auth Me (Capabilities) ===")
        success, response = self.run_test(
            "Auth Me (Superadmin)",
            "GET",
            "auth/me",
            200,
            token=self.superadmin_token
        )
        if success:
            caps = response.get("capabilities", {})
            features = caps.get("features", [])
            rank = caps.get("rank")
            
            required_features = ["portfolio", "backtest", "charts", "options"]
            missing = [f for f in required_features if f not in features]
            
            if not missing and rank == 3:
                self.log(f"✅ Capabilities correct: rank={rank}, features include {required_features}")
            else:
                if missing:
                    self.log(f"❌ Missing features in capabilities: {missing}", "FAIL")
                if rank != 3:
                    self.log(f"❌ Wrong rank: expected 3, got {rank}", "FAIL")
        return success

    def test_profile_update(self):
        """Test PUT /api/auth/profile with various fields."""
        self.log("\n=== Testing Profile Update ===")
        
        # Test 1: Update basic profile fields
        success1, _ = self.run_test(
            "Profile Update (Basic)",
            "PUT",
            "auth/profile",
            200,
            data={
                "display_name": "Douglas Test",
                "bio": "Testing profile updates",
                "phone": "+55123456789",
                "country": "Brazil",
                "telegram_chat_id": "123456789",
                "webhook_url": "https://example.com/webhook"
            },
            token=self.superadmin_token
        )
        
        # Test 2: Valid small avatar
        small_avatar = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        success2, _ = self.run_test(
            "Profile Update (Valid Avatar)",
            "PUT",
            "auth/profile",
            200,
            data={"avatar": small_avatar},
            token=self.superadmin_token
        )
        
        # Test 3: Invalid avatar (not data:image)
        success3, _ = self.run_test(
            "Profile Update (Invalid Avatar)",
            "PUT",
            "auth/profile",
            400,
            data={"avatar": "not-a-valid-data-url"},
            token=self.superadmin_token
        )
        
        # Test 4: Huge avatar (>2M chars)
        huge_avatar = "data:image/png;base64," + ("A" * 2_000_001)
        success4, _ = self.run_test(
            "Profile Update (Huge Avatar)",
            "PUT",
            "auth/profile",
            413,
            data={"avatar": huge_avatar},
            token=self.superadmin_token
        )
        
        return success1 and success2 and success3 and success4

    def test_portfolio_crud(self):
        """Test Portfolio CRUD operations (investor feature)."""
        self.log("\n=== Testing Portfolio (Investor Feature) ===")
        
        # Test 1: POST - Add position
        success1, response1 = self.run_test(
            "Portfolio Add Position",
            "POST",
            "portfolio",
            200,
            data={"ticker": "AAPL", "quantity": 10, "avg_cost": 150},
            token=self.superadmin_token
        )
        if success1:
            positions = response1.get("positions", [])
            totals = response1.get("totals", {})
            if positions and "pnl" in totals:
                self.log(f"✅ Portfolio has {len(positions)} position(s), totals include P&L")
                if positions:
                    self.test_position_id = positions[0].get("id")
            else:
                self.log("❌ Portfolio response missing positions or totals", "FAIL")
        
        # Test 2: GET - Retrieve portfolio
        success2, response2 = self.run_test(
            "Portfolio Get",
            "GET",
            "portfolio",
            200,
            token=self.superadmin_token
        )
        
        # Test 3: DELETE - Remove position
        if self.test_position_id:
            success3, _ = self.run_test(
                "Portfolio Delete Position",
                "DELETE",
                f"portfolio/{self.test_position_id}",
                200,
                token=self.superadmin_token
            )
        else:
            self.log("⚠️  Skipping delete test (no position ID)", "WARN")
            success3 = True
        
        return success1 and success2 and success3

    def test_backtest(self):
        """Test GET /api/backtest (investor feature)."""
        self.log("\n=== Testing Backtest (Investor Feature) ===")
        success, response = self.run_test(
            "Backtest",
            "GET",
            "backtest",
            200,
            params={"ticker": "AAPL", "period": "2y", "hold_days": 10},
            token=self.superadmin_token
        )
        if success:
            if response.get("ok") and "num_trades" in response and "win_rate" in response:
                self.log(f"✅ Backtest returned: {response.get('num_trades')} trades, {response.get('win_rate')}% win rate")
                self.log(f"   Strategy return: {response.get('strategy_return_pct')}%, Buy&Hold: {response.get('buy_hold_return_pct')}%")
            else:
                self.log("❌ Backtest response incomplete", "FAIL")
        return success

    def test_feature_gating(self):
        """Test feature gating by creating user and changing plans."""
        self.log("\n=== Testing Feature Gating ===")
        
        # Step 1: Register a new test user
        test_email = f"test_{uuid.uuid4().hex[:8]}@test.com"
        success1, response1 = self.run_test(
            "Register Test User",
            "POST",
            "auth/register",
            200,
            data={"email": test_email, "password": "Test1234!"}
        )
        if not success1:
            return False
        
        self.test_user_token = response1.get("access_token")
        user = response1.get("user", {})
        self.test_user_id = user.get("id")
        self.log(f"✅ Test user created: {test_email}, plan={user.get('plan')}")
        
        # Step 2: Set plan to 'starter' using superadmin
        success2, _ = self.run_test(
            "Set User Plan to Starter",
            "PUT",
            f"admin/users/{self.test_user_id}",
            200,
            data={"plan": "starter"},
            token=self.superadmin_token
        )
        
        # Step 3: Test portfolio access with starter (should be 403)
        success3, response3 = self.run_test(
            "Portfolio Access (Starter - Should Fail)",
            "GET",
            "portfolio",
            403,
            token=self.test_user_token
        )
        if success3:
            detail = response3.get("detail", {})
            if isinstance(detail, dict) and detail.get("code") == "feature_locked":
                self.log("✅ Feature gating working: portfolio locked for starter")
            else:
                self.log(f"❌ Wrong error response: {detail}", "FAIL")
        
        # Step 4: Test backtest access with starter (should be 403)
        success4, response4 = self.run_test(
            "Backtest Access (Starter - Should Fail)",
            "GET",
            "backtest",
            403,
            params={"ticker": "AAPL", "period": "1y", "hold_days": 10},
            token=self.test_user_token
        )
        if success4:
            detail = response4.get("detail", {})
            if isinstance(detail, dict) and detail.get("code") == "feature_locked":
                self.log("✅ Feature gating working: backtest locked for starter")
        
        # Step 5: Set plan to 'pro'
        success5, _ = self.run_test(
            "Set User Plan to Pro",
            "PUT",
            f"admin/users/{self.test_user_id}",
            200,
            data={"plan": "pro"},
            token=self.superadmin_token
        )
        
        # Step 6: Test portfolio access with pro (should still be 403)
        success6, response6 = self.run_test(
            "Portfolio Access (Pro - Should Still Fail)",
            "GET",
            "portfolio",
            403,
            token=self.test_user_token
        )
        if success6:
            self.log("✅ Portfolio still locked for pro plan (investor-only feature)")
        
        # Step 7: Set plan to 'investor'
        success7, _ = self.run_test(
            "Set User Plan to Investor",
            "PUT",
            f"admin/users/{self.test_user_id}",
            200,
            data={"plan": "investor"},
            token=self.superadmin_token
        )
        
        # Step 8: Test portfolio access with investor (should be 200)
        success8, _ = self.run_test(
            "Portfolio Access (Investor - Should Work)",
            "GET",
            "portfolio",
            200,
            token=self.test_user_token
        )
        
        # Cleanup: Delete test user
        if self.test_user_id:
            self.run_test(
                "Cleanup Test User",
                "DELETE",
                f"admin/users/{self.test_user_id}",
                200,
                token=self.superadmin_token
            )
        
        return success1 and success2 and success3 and success4 and success5 and success6 and success7 and success8

    def test_market_endpoints(self):
        """Test market data endpoints."""
        self.log("\n=== Testing Market Endpoints ===")
        
        success1, response1 = self.run_test(
            "Market Screener (Day Gainers)",
            "GET",
            "market/screener",
            200,
            params={"type": "day_gainers"},
            token=self.superadmin_token
        )
        
        success2, _ = self.run_test(
            "Market Quote (AAPL)",
            "GET",
            "market/quote/AAPL",
            200,
            token=self.superadmin_token
        )
        
        success3, _ = self.run_test(
            "Market History (AAPL)",
            "GET",
            "market/history/AAPL",
            200,
            token=self.superadmin_token
        )
        
        return success1 and success2 and success3

    def run_all_tests(self):
        """Run all backend tests."""
        self.log("=" * 60)
        self.log("DIPZEE BACKEND API TESTS")
        self.log("=" * 60)
        
        # Test sequence
        if not self.test_superadmin_login():
            self.log("\n❌ CRITICAL: Superadmin login failed. Cannot proceed.", "FAIL")
            return False
        
        self.test_plans_catalog()
        self.test_auth_me_capabilities()
        self.test_profile_update()
        self.test_portfolio_crud()
        self.test_backtest()
        self.test_feature_gating()
        self.test_market_endpoints()
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log(f"TESTS COMPLETED: {self.tests_passed}/{self.tests_run} passed")
        self.log("=" * 60)
        
        return self.tests_passed == self.tests_run

def main():
    tester = DipzeeAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
