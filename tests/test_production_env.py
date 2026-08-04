import base64
from pathlib import Path
import tempfile
import unittest

from scripts.bootstrap_production_env import bootstrap


BASE_ENV = """ENV=development
DOMAIN=dipzee.com
MONGO_ROOT_USER=root
MONGO_ROOT_PASSWORD=root-password
MONGO_APP_USER=app
MONGO_APP_PASSWORD=app-password
DB_NAME=dipzee
JWT_SECRET=jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj
CORS_ORIGINS=https://dipzee.com
RESEND_API_KEY=re_existing
STRIPE_API_KEY=sk_live_existing
STRIPE_PUBLISHABLE_KEY=pk_live_existing
STRIPE_WEBHOOK_SECRET=whsec_existing
SUPERADMIN_EMAIL=admin@example.com
SUPERADMIN_PASSWORD=existing-password
UNRELATED_VALUE=preserve-me
"""


def _values(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            result[key] = value
    return result


class ProductionEnvTests(unittest.TestCase):
    def test_bootstrap_generates_independent_values_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(BASE_ENV, encoding="utf-8")

            result = bootstrap(path, "https://dipzee.com")
            first = path.read_text(encoding="utf-8")
            values = _values(path)

            self.assertEqual(values["ENV"], "production")
            self.assertEqual(values["PUBLIC_APP_URL"], "https://dipzee.com")
            self.assertEqual(values["ADMIN_MFA_REQUIRED"], "true")
            self.assertEqual(values["UNRELATED_VALUE"], "preserve-me")
            self.assertEqual(len(base64.b64decode(values["APP_ENCRYPTION_KEY"], validate=True)), 32)
            self.assertEqual(len(base64.b64decode(values["BACKUP_ENCRYPTION_KEY"], validate=True)), 32)
            self.assertNotEqual(values["APP_ENCRYPTION_KEY"], values["BACKUP_ENCRYPTION_KEY"])
            self.assertNotEqual(values["DATASET_SALT"], values["JWT_SECRET"])
            self.assertIn("BACKUP_ENCRYPTION_KEY", result["generated"])

            second_result = bootstrap(path, "https://dipzee.com")
            self.assertEqual(path.read_text(encoding="utf-8"), first)
            self.assertEqual(second_result, {"generated": [], "updated": []})

    def test_invalid_existing_key_is_rejected_without_rewriting_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            original = BASE_ENV + "APP_ENCRYPTION_KEY=not-base64\n"
            path.write_text(original, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "APP_ENCRYPTION_KEY"):
                bootstrap(path, "https://dipzee.com")
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_duplicate_required_setting_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            original = BASE_ENV + "JWT_SECRET=another-long-secret-value-that-must-not-win\n"
            path.write_text(original, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Duplicate production settings"):
                bootstrap(path, "https://dipzee.com")
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_existing_public_url_must_match_approved_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            original = BASE_ENV + "PUBLIC_APP_URL=https://wrong.example\n"
            path.write_text(original, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "PUBLIC_APP_URL"):
                bootstrap(path, "https://dipzee.com")
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_cors_must_include_approved_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            original = BASE_ENV.replace(
                "CORS_ORIGINS=https://dipzee.com",
                "CORS_ORIGINS=https://admin.dipzee.com",
            )
            path.write_text(original, encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "CORS_ORIGINS"):
                bootstrap(path, "https://dipzee.com")
            self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
