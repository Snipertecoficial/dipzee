// Mirror of the backend password policy (backend/routes_auth.py:_PASSWORD_RE):
// at least 8 characters, with a letter and a digit. Client-side validation is
// UX only — the server enforces the same rule, since a client can be bypassed.
export const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/;

export function isStrongPassword(pw) {
  return PASSWORD_RE.test(pw || '');
}
