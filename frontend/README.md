# Dipzee Front-end

React 19 single-page application built with Vite and served by Nginx in
production.

## Commands

- `yarn start`: local development server.
- `yarn test:ci`: deterministic unit-test run.
- `yarn audit:ci`: dependency audit with the documented non-RSC exception.
- `yarn build`: optimized production build plus strict CSP generation.

Runtime API access uses `REACT_APP_BACKEND_URL`. Authentication keeps the
short-lived access token in memory and rotates the refresh token through a
Secure, HttpOnly, SameSite cookie.
