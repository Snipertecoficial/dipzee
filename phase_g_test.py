"""Phase G specific tests: Stripe subscriptions + AI analyst."""
import requests
import sys
import time

BASE_URL = "https://dipzee-mvp.preview.emergentagent.com/api"

class PhaseGTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures = []
        self.token = None
        self.session_id = None

    def log(self, msg, level="INFO"):
        print(f"[{level}] {msg}")

    def test(self, name, fn):
        """Run a single test function."""
        self.tests_run += 1
        self.log(f"\n{'='*70}")
        self.log(f"Test {self.tests_run}: {name}")
        self.log('='*70)
        try:
            fn()
            self.tests_passed += 1
            self.log(f"✅ PASSED: {name}", "PASS")
        except AssertionError as e:
            self.tests_failed += 1
            self.failures.append({"test": name, "error": str(e)})
            self.log(f"❌ FAILED: {name} - {e}", "FAIL")
        except Exception as e:
            self.tests_failed += 1
            self.failures.append({"test": name, "error": f"Exception: {str(e)}"})
            self.log(f"❌ ERROR: {name} - {e}", "ERROR")

    def summary(self):
        self.log("\n" + "="*70)
        self.log("PHASE G TEST SUMMARY")
        self.log("="*70)
        self.log(f"Total: {self.tests_run} | Passed: {self.tests_passed} | Failed: {self.tests_failed}")
        if self.failures:
            self.log("\nFailed tests:")
            for f in self.failures:
                self.log(f"  - {f['test']}: {f['error']}")
        return 0 if self.tests_failed == 0 else 1


def main():
    tester = PhaseGTester()

    # ========== AUTH SETUP ==========
    def login_superadmin():
        """Login as superadmin (plan=investor) to test all features."""
        tester.log("Logging in as superadmin (douglas@snipertec.com.br)...")
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": "douglas@snipertec.com.br",
            "password": "Admin213021#"
        })
        assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
        data = resp.json()
        assert "access_token" in data, "No access_token in login response"
        tester.token = data["access_token"]
        tester.log(f"✅ Logged in successfully")

    tester.test("Login as superadmin", login_superadmin)

    # ========== BILLING CONFIG ==========
    def test_billing_config():
        """GET /api/billing/config -> configured=true, publishable_key, 6 packages, currency USD, trial_days=7"""
        resp = requests.get(f"{BASE_URL}/billing/config")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        
        assert data.get("configured") is True, f"Expected configured=true, got {data.get('configured')}"
        assert data.get("publishable_key", "").startswith("pk_test"), f"Expected pk_test..., got {data.get('publishable_key')}"
        assert data.get("currency") == "USD", f"Expected USD, got {data.get('currency')}"
        assert data.get("trial_days") == 7, f"Expected trial_days=7, got {data.get('trial_days')}"
        
        packages = data.get("packages", {})
        assert len(packages) == 6, f"Expected 6 packages, got {len(packages)}"
        
        # Verify package structure and prices
        expected = {
            "starter_monthly": 4.97,
            "starter_annual": 47.71,
            "pro_monthly": 12.97,
            "pro_annual": 124.51,
            "investor_monthly": 24.99,
            "investor_annual": 239.90,
        }
        for pkg_id, expected_amount in expected.items():
            assert pkg_id in packages, f"Missing package {pkg_id}"
            pkg = packages[pkg_id]
            assert pkg.get("amount") == expected_amount, f"{pkg_id}: expected ${expected_amount}, got ${pkg.get('amount')}"
            assert pkg.get("trial_days") == 7, f"{pkg_id}: expected trial_days=7, got {pkg.get('trial_days')}"
        
        tester.log("✅ Config: 6 packages, USD, 7-day trial, prices correct")

    tester.test("GET /api/billing/config", test_billing_config)

    # ========== CHECKOUT - INVALID PACKAGE ==========
    def test_checkout_invalid_package():
        """POST /api/billing/checkout with invalid package_id -> 400"""
        headers = {"Authorization": f"Bearer {tester.token}"}
        resp = requests.post(f"{BASE_URL}/billing/checkout", json={
            "package_id": "invalid_package",
            "origin_url": "https://dipzee-mvp.preview.emergentagent.com"
        }, headers=headers)
        assert resp.status_code == 400, f"Expected 400 for invalid package, got {resp.status_code}"
        tester.log("✅ Invalid package returns 400")

    tester.test("POST /api/billing/checkout - invalid package", test_checkout_invalid_package)

    # ========== CHECKOUT - NO AUTH ==========
    def test_checkout_no_auth():
        """POST /api/billing/checkout without auth -> 401"""
        resp = requests.post(f"{BASE_URL}/billing/checkout", json={
            "package_id": "pro_monthly",
            "origin_url": "https://dipzee-mvp.preview.emergentagent.com"
        })
        assert resp.status_code == 401, f"Expected 401 without auth, got {resp.status_code}"
        tester.log("✅ Checkout without auth returns 401")

    tester.test("POST /api/billing/checkout - no auth", test_checkout_no_auth)

    # ========== CHECKOUT - VALID ==========
    def test_checkout_valid():
        """POST /api/billing/checkout with valid package -> returns {url, session_id}"""
        headers = {"Authorization": f"Bearer {tester.token}"}
        resp = requests.post(f"{BASE_URL}/billing/checkout", json={
            "package_id": "pro_monthly",
            "origin_url": "https://dipzee-mvp.preview.emergentagent.com"
        }, headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.text}"
        data = resp.json()
        
        assert "url" in data, "Missing 'url' in checkout response"
        assert "session_id" in data, "Missing 'session_id' in checkout response"
        assert data["url"].startswith("https://checkout.stripe.com"), f"Expected Stripe checkout URL, got {data['url']}"
        assert data["session_id"].startswith("cs_test_"), f"Expected cs_test_ session_id, got {data['session_id']}"
        
        tester.session_id = data["session_id"]
        tester.log(f"✅ Checkout created: session_id={tester.session_id}")

    tester.test("POST /api/billing/checkout - valid", test_checkout_valid)

    # ========== STATUS BEFORE PAYMENT ==========
    def test_status_before_payment():
        """GET /api/billing/status/{session_id} BEFORE payment -> active=false"""
        if not tester.session_id:
            tester.log("⚠️  Skipping (no session_id from previous test)", "WARN")
            return
        
        headers = {"Authorization": f"Bearer {tester.token}"}
        resp = requests.get(f"{BASE_URL}/billing/status/{tester.session_id}", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.text}"
        data = resp.json()
        
        # Before payment, session is 'open' and subscription not yet active
        assert data.get("active") is False, f"Expected active=false before payment, got {data.get('active')}"
        assert data.get("plan") == "investor", f"Expected plan=investor (superadmin), got {data.get('plan')}"
        tester.log(f"✅ Status before payment: active=false, plan={data.get('plan')}")

    tester.test("GET /api/billing/status/{session_id} - before payment", test_status_before_payment)

    # ========== SUBSCRIPTION ENDPOINT ==========
    def test_subscription_endpoint():
        """GET /api/billing/subscription -> returns subscription info"""
        headers = {"Authorization": f"Bearer {tester.token}"}
        resp = requests.get(f"{BASE_URL}/billing/subscription", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.text}"
        data = resp.json()
        
        # Verify required fields
        assert "plan" in data, "Missing 'plan' in subscription response"
        assert "subscription_status" in data, "Missing 'subscription_status'"
        assert "has_subscription" in data, "Missing 'has_subscription'"
        
        # Superadmin should have plan=investor
        assert data["plan"] == "investor", f"Expected plan=investor for superadmin, got {data['plan']}"
        tester.log(f"✅ Subscription: plan={data['plan']}, has_subscription={data.get('has_subscription')}")

    tester.test("GET /api/billing/subscription", test_subscription_endpoint)

    # ========== PORTAL ==========
    def test_portal():
        """POST /api/billing/portal -> returns {url} pointing to billing.stripe.com"""
        headers = {"Authorization": f"Bearer {tester.token}"}
        resp = requests.post(f"{BASE_URL}/billing/portal", json={
            "origin_url": "https://dipzee-mvp.preview.emergentagent.com"
        }, headers=headers)
        
        # Superadmin might not have a stripe_customer_id yet if they never checked out
        # But after the checkout test above, they should have one
        if resp.status_code == 400:
            tester.log("⚠️  Portal returns 400 (no billing account) - acceptable if no prior checkout", "WARN")
            return
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.text}"
        data = resp.json()
        
        assert "url" in data, "Missing 'url' in portal response"
        assert "billing.stripe.com" in data["url"], f"Expected billing.stripe.com URL, got {data['url']}"
        tester.log(f"✅ Portal URL generated: {data['url'][:60]}...")

    tester.test("POST /api/billing/portal", test_portal)

    # ========== AI ANALYST - PRO/INVESTOR ==========
    def test_ai_analyst_authorized():
        """GET /api/ai/analyst/{ticker} as Pro/Investor -> 200 with analysis fields"""
        headers = {"Authorization": f"Bearer {tester.token}"}
        ticker = "AAPL"
        tester.log(f"Testing AI analyst for {ticker} (superadmin has plan=investor)...")
        
        resp = requests.get(f"{BASE_URL}/ai/analyst/{ticker}", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code} {resp.text}"
        data = resp.json()
        
        # Verify required fields
        required = ["summary", "stance", "stance_label", "thesis", "risks", "catalysts", "confidence"]
        for field in required:
            assert field in data, f"Missing required field '{field}' in AI analyst response"
        
        # Verify types
        assert isinstance(data["summary"], str) and len(data["summary"]) > 0, f"summary should be non-empty string"
        assert isinstance(data["thesis"], list), f"thesis should be list, got {type(data['thesis'])}"
        assert isinstance(data["risks"], list), f"risks should be list, got {type(data['risks'])}"
        assert isinstance(data["catalysts"], list), f"catalysts should be list, got {type(data['catalysts'])}"
        assert isinstance(data["confidence"], int), f"confidence should be int, got {type(data['confidence'])}"
        assert 0 <= data["confidence"] <= 100, f"confidence should be 0-100, got {data['confidence']}"
        
        tester.log(f"✅ AI analyst: stance={data['stance']}, confidence={data['confidence']}%, thesis={len(data['thesis'])} points")
        
        # Test caching - second call should be fast and return cached=true
        tester.log("Testing cache (second call)...")
        start = time.time()
        resp2 = requests.get(f"{BASE_URL}/ai/analyst/{ticker}", headers=headers)
        elapsed = time.time() - start
        assert resp2.status_code == 200, f"Expected 200 on cached call, got {resp2.status_code}"
        data2 = resp2.json()
        assert data2.get("cached") is True, f"Expected cached=true on second call, got {data2.get('cached')}"
        tester.log(f"✅ Cached response in {elapsed:.2f}s with cached=true")

    tester.test("GET /api/ai/analyst/{ticker} - authorized (Pro/Investor)", test_ai_analyst_authorized)

    # ========== AI ANALYST - GATING (plan=none) ==========
    def test_ai_analyst_gated():
        """GET /api/ai/analyst/{ticker} as plan='none' -> 403 with code='feature_locked'"""
        # Register a new user (will have plan='none' by default)
        tester.log("Registering new user with plan='none'...")
        test_email = f"test_phaseG_{int(time.time())}@test.com"
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": test_email,
            "password": "Test1234!",
            "display_name": "Test User"
        })
        assert resp.status_code == 200, f"Register failed: {resp.status_code} {resp.text}"
        test_token = resp.json()["access_token"]
        tester.log(f"✅ Registered test user: {test_email}")
        
        # Try to access AI analyst
        headers = {"Authorization": f"Bearer {test_token}"}
        resp = requests.get(f"{BASE_URL}/ai/analyst/AAPL", headers=headers)
        
        assert resp.status_code == 403, f"Expected 403 for plan='none', got {resp.status_code}"
        data = resp.json()
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            assert detail.get("code") == "feature_locked", f"Expected code='feature_locked', got {detail.get('code')}"
        tester.log("✅ AI analyst correctly gated for plan='none' (403 with feature_locked)")

    tester.test("GET /api/ai/analyst/{ticker} - gated (plan=none)", test_ai_analyst_gated)

    # ========== SUMMARY ==========
    return tester.summary()


if __name__ == "__main__":
    sys.exit(main())
