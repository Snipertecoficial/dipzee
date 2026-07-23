---
name: dipzee-i18n
description: Add, change, or audit any user-facing text in the Dipzee frontend. Use whenever adding a new UI string, fixing a hardcoded/untranslated string, or checking that all 4 languages stay in sync.
---

# Dipzee i18n

Dipzee supports 4 languages via i18next: `en`, `pt`, `es`, `fr`. Locale
files live at `frontend/src/locales/{en,pt,es,fr}.json`, one big nested JSON
object per language (namespaces like `common`, `nav`, `auth`, `landing`,
`admin.tabs`, `admin.ads`, etc.).

**English is the product default**, not Portuguese, even though this team
communicates in Portuguese. `frontend/src/i18n/index.js` sets
`fallbackLng: 'en'` and detection `order: ['localStorage']` only — no
browser/`navigator`-based auto-detection. A visitor's OS/browser language
must never silently switch the site language; only an explicit pick
(persisted to `localStorage['dz_locale']`, and to the user's profile once
logged in) does that.

## The rule that matters most

**Never add or edit a string in only one locale file.** Every new
user-facing string needs the same key added to all 4 files, even if the
translation is rough — a missing key silently falls back to English (not a
crash), which is a real but low-visibility bug: it means a PT/ES/FR user
sees a stray English string with no error anywhere. This exact bug pattern
has already been found and fixed multiple times in this codebase (missing
`admin.*` namespace in es/fr, hardcoded PT strings bypassing `t()` entirely
in `TopBar.jsx`, `Dashboard.jsx`, `AdminAdsTab.jsx`, etc.).

Also watch for **hardcoded strings that bypass `t()` entirely** — these are
worse than missing keys because they show the wrong language to 100% of
users regardless of their selection, not just es/fr users falling back to
en. Grep for literal Portuguese text (accented characters, common words
like "Excluir", "Salvar", "Erro ao") in any file you touch — this has been
the single most common i18n bug in this codebase.

## Workflow

1. Add the key to `en.json` first (source of truth for structure/wording).
2. Add the matching key to `pt.json`, `es.json`, `fr.json` — same nesting
   path, real translations (not machine-literal placeholders).
3. Wire it into the component with `t('namespace.key')`. Confirm the
   component actually has `const { t } = useTranslation();` in scope —
   several files import `useTranslation` but never destructure `t`, so a
   naive `{t(...)}` insertion throws.
4. Validate all 4 files parse and have matching key counts for whatever
   namespace you touched:
   ```
   python -c "
   import json
   for f in ['en','pt','es','fr']:
       with open(f'frontend/src/locales/{f}.json', encoding='utf-8') as fh:
           d = json.load(fh)
           print(f, len(d['<namespace>']))
   "
   ```
5. Rebuild the frontend to confirm no compile errors:
   `docker compose build frontend` (must end in `Compiled successfully`).

## Gotchas

- JSON string values are plain JSON — never HTML-entity-escape characters
  like `&` (i.e. write `"Partners & Campaigns"`, not `"Partners &amp;
  Campaigns"`). Easy mistake when copy-pasting from HTML context.
- The `es`/`fr` files historically drifted from `en`/`pt` (missing an
  entire `admin` sub-namespace at one point) because new keys were added
  to en/pt only. Always re-check parity after any batch of UI work, not
  just when adding one string.
- Static, non-React text (meta tags, JSON-LD, `<title>` in
  `frontend/public/index.html`) is English-only by design — it's read by
  crawlers before any JS/i18n runs, so it intentionally doesn't localize.
  Don't try to make it dynamic; that's a separate, larger SSR/hreflang
  project, deliberately out of scope unless explicitly asked for.
