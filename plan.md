# Dipzee — plan.md (Planos + Paywall + Mercado resiliente + App Premium) — ATUALIZADO (Fase: Qualidade & Refactor)

## 1) Objectives

### Objetivos já concluídos (baseline do produto) — ✅
- **Estrutura de planos paga (USD) concluída** com 3 tiers e pricing server-side:
  - **Starter (`starter`) — US$ 4,97/mês**
  - **Pro (`pro`) — US$ 12,97/mês**
  - **Investor (`investor`) — US$ 24,99/mês**
  - **Trial de 7 dias com cartão + paywall** (usuários `plan="none"` não acessam áreas logadas até assinar).
- **Redesign das áreas logadas concluído** (AppShell profissional com sidebar/topbar, rotas consistentes).
- **Redesign da landing/auth concluído**, remoção do badge “Made with Emergent”, favicon/título configurados.
- **Camada resiliente de dados de mercado concluída** (`/api/market/*`) com cache agressivo + persistência Mongo + fallback stale para evitar rate limit do Yahoo/yfinance.
- **Dark Mode** completo (toggle + persistência).
- **Perfil editável** com avatar Base64 e integrações (Telegram/Webhook).
- **Mercados** (abas + filtro) + **Asset Detail** com Insights (Chart/Fundamentals/Options/Backtest com gating).
- **Investidor entregue**: Portfolio P&L + export CSV + Backtesting.
- **Dual-superadmin**: múltiplos e-mails permitidos.

### Objetivos desta fase (Qualidade de Código + Refatoração Admin) — STATUS: ⏳ EM ANDAMENTO
1. **Aplicar correções de Qualidade de Código (baixo risco, melhores práticas)**
   - Frontend: eliminar `key={index}` onde há lista dinâmica e substituir por chave estável.
   - Backend: remover imports/variáveis não usadas (pyflakes), mantendo comportamento idêntico.
   - Evitar refactors que mudem arquitetura (ex.: migração de localStorage → cookies **não** entra agora).
2. **Refatorar `Admin.jsx` (manutenibilidade)**
   - Extrair as tabs em subcomponentes pequenos e testáveis.
   - Preservar **100%** dos `data-testid`, rotas e chamadas de API.
   - Manter o container Admin como “orquestrador” (estado, loaders, handlers), e os subcomponentes como “presentational”.
3. **Verificação básica pós-alteração (sem agente E2E completo)**
   - `frontend build`/compilação, logs, sanity-check de navegação e chamadas principais (curl) e screenshots pontuais.

> Observação: **Sem integrações** (Stripe subscriptions/Resend/Telegram) nesta fase, pois chaves/API keys ainda não foram fornecidas.

---

## 2) Implementation Steps

### Phase 0 — Auditoria/Inventário (curto, antes de mexer) — ✅ CONCLUÍDA
**Entregue**
- Auditoria de limites, intraday, alert types, UI do Upgrade.
- Tabela interna “Plano → features → status”.
- Ajuste de copy/i18n para evitar overpromising.

---

### Phase A — Fundação (Capacidades por plano + Perfil + Dark Mode) — ✅ CONCLUÍDA

#### A1) Backend: catálogo de planos por capacidades — ✅
- `plans.py`: `PLAN_LIMITS`, `PLAN_FEATURES`, `PLAN_RANK`, `PLAN_CARD_FEATURES`.
- Helpers: `has_feature`, `plan_capabilities`, `catalog`.
- `serialize_user` retorna `capabilities`.
- `require_feature(feature)` (403 `feature_locked`).
- `GET /api/plans/catalog`.

#### A2) Backend: Perfil editável (dados + avatar base64) — ✅
- `PUT /api/auth/profile` com validações (tamanho/formato avatar, sanitização).

#### A3) Frontend: Settings em abas + Perfil — ✅
- Settings com abas: Perfil / Aparência / Alertas / Assinatura.

#### A4) Dark Mode completo — ✅
- `ThemeContext` com persistência + opção system.
- Toggle no TopBar e opção em Settings.

---

### Phase B — Mercados + Ativos/Notícias — ✅ CONCLUÍDA

#### B1) Página “Mercados” — ✅
- `/app/markets` com abas `day_gainers`, `day_losers`, `most_actives`, `crypto`, `news`.
- Integrações: `GET /api/market/screener` e `GET /api/news/market`.

#### B2) Asset Detail (Pro+) — ✅
- `AssetInsights` com Tabs:
  - Chart: `GET /api/market/history`
  - Fundamentals: `GET /api/market/fundamentals`
  - Options: `GET /api/market/options`
  - Backtest (Investidor): `GET /api/backtest`
- Gating 1:1 com a matriz.

---

### Phase C — Investidor (Portfolio P&L + Backtest + Canais) — ✅ CONCLUÍDA

#### C1) Portfolio P&L — ✅
- Backend: `routes_portfolio.py` + coleção `positions`.
- Cálculo: P&L, market value, cost basis, dividendos anuais estimados.
- Frontend: CRUD + métricas + export CSV.

#### C2) Backtest — ✅
- Backend: `routes_backtest.py`.
- Frontend: tab Backtest no AssetInsights.

#### C3) Alertas por Mensagem (estrutura) — ✅ (dependente de config)
- `notify_service.py` com Email (mock), Webhook (real), Telegram (quando token).

---

### Phase D — Gating, Upsell, Qualidade e “Lista 100%” — ✅ CONCLUÍDA (MVP) / ⏳ PENDÊNCIAS (produção)

**Entregue (MVP)**
- Gating consistente:
  - Backend: `require_feature`
  - Frontend: `FeatureGate`
- Testes E2E anteriores (iteration_8/9) passaram sem regressões.

**Pendências para 100% produção (fora do escopo desta fase)**
1. Stripe Subscriptions + trial real + Customer Portal.
2. Resend real + reset/verify e-mails.
3. `TELEGRAM_BOT_TOKEN` em produção.
4. Dividend tracker dedicado.
5. Advanced Screener Builder.
6. Provider licenciado.
7. Termos/Privacidade + hardening/observabilidade.

---

### Phase E — Qualidade de Código + Refatoração Admin (fase atual) — ✅ CONCLUÍDA

> Resultado: backend sem warnings de pyflakes nos módulos de runtime; keys instáveis (index) substituídas por chaves estáveis; `Admin.jsx` reduzido de 376 → ~145 linhas e dividido em 7 subcomponentes em `frontend/src/pages/admin/` (AdminShared, Overview, Users, Assets, Alerts, Billing, Settings). Todas as abas verificadas via screenshot (Overview/Users/Settings) sem regressão. Compilação esbuild OK e login superadmin OK.

#### E1) Backend: limpar variáveis/imports não usados (pyflakes) — ⏳
**Descobertas reais (pyflakes):**
- `alert_service.py`: variável `prefs` atribuída e não usada.
- `explain.py`: variável `high` atribuída e não usada.
- `server.py`: import `daily_refresh_job` não usado.
- `routes_assets.py`: imports `compute_opportunity_score` e `SETTINGS` não usados.
- `poc_core.py`: imports não usados (`math`, `dataclass`, `field`, `Optional`).
- `backend_test.py`: import não usado (arquivo de teste; manter sem impacto em runtime, mas ideal limpar também).

**Plano de execução:**
- Remover variáveis/imports não usados sem alterar lógica.
- Rodar `python -m pyflakes` novamente até “limpo” (ou minimamente sem warnings nos módulos de runtime).

#### E2) Frontend: substituir `key={index}` por chaves estáveis — ⏳
**Alvos confirmados via grep:**
- `Portfolio.jsx`: cards de métricas usam `key={i}` → trocar para `key={m.label}` (ou `key={m.testId}` se criado).
- `AuthLayout.jsx`: perks usam `key={i}` → trocar para `key={p.text}` (ou `key={p.textKey}` se padronizar).
- `AssetInsights.jsx`:
  - `income.map((row, i))` → usar `key={row.item}`.
  - options chain map usa `key={i}` → usar `key={o.contractSymbol || o.strike}` (fallback controlado se não existir).
- `Landing.jsx`:
  - `steps.map((s, i))` → `key={s.title}`.
  - `features.map((f, i))` → `key={f.title}`.
  - `faqs.map((f, i))` → `key={f.q}` e `value={f.q}` (ou manter `value` estável derivado do texto).

**Notas de boas práticas:**
- Keys de skeletons gerados de arrays literais `[1,2,3]` são aceitáveis e podem ser mantidos.
- Onde o dado não tem id estável, criar uma chave derivada consistente (ex.: `label/title/q`) antes de cair em index.

#### E3) Refatoração do Admin.jsx em subcomponentes — ⏳
**Objetivo:** reduzir complexidade/custo de manutenção mantendo comportamento.

**Estratégia (segura):**
- Criar pasta: `frontend/src/pages/admin/` (ou `frontend/src/components/admin/`).
- Extrair componentes por tab:
  1. `AdminOverviewTab.jsx`
  2. `AdminUsersTab.jsx`
  3. `AdminAssetsTab.jsx`
  4. `AdminAlertsTab.jsx`
  5. `AdminBillingTab.jsx`
  6. `AdminSettingsTab.jsx`
- `Admin.jsx` mantém:
  - estado (`stats`, `config`, `users`, `assets`, etc.)
  - loaders/busy flags
  - handlers (update/delete/refresh/save)
  - funções utilitárias comuns (`fmtDate`, classes `th/td`)
- Subcomponentes recebem via props:
  - data + callbacks + busy flags
  - `t`, `locale` (ou strings já prontas)
- **Preservar `data-testid` existentes** e o layout atual.

**Critérios de aceite:**
- UI idêntica (sem regressões visuais e funcionais).
- Todas as chamadas de API permanecem iguais.
- `Admin.jsx` reduzido e legível.

#### E4) Verificação básica (sem E2E completo) — ⏳
- Frontend:
  - `yarn build` (ou `craco build`) para confirmar compilação.
  - Navegação rápida: login superadmin → Admin → alternar tabs.
- Backend:
  - subir serviços (já estão rodando) e validar endpoints principais via curl:
    - `/api/admin/stats`
    - `/api/admin/users`
    - `/api/market/quote/AAPL`
  - checar logs por erros.

---

## 3) Next Actions (a partir de agora)

### Imediato (esta fase)
1. Aplicar limpezas do backend (pyflakes) com PR pequeno e seguro.
2. Corrigir `key` instáveis no frontend.
3. Refatorar `Admin.jsx` em subcomponentes (com preservação de testids).
4. Fazer verificação básica (build + sanity check) e registrar evidências (logs/screenshot).

### Próximo (quando usuário fornecer chaves)
1. Stripe Subscriptions (trial real) + Customer Portal.
2. Resend real + reset/verify.
3. Ativar Telegram em produção.

---

## 4) Success Criteria

### Já atingidos (baseline + MVP)
- 3 planos pagos em USD + paywall trial 7 dias.
- UI premium (landing/auth + app shell) e gating consistente.
- Dados de mercado resilientes com cache e fallback.
- Perfil + avatar base64 + dark mode.
- Mercados + Asset Detail Pro+ + Portfolio/Backtest Investor.

### Para concluir a fase atual (Qualidade & Refactor)
- Backend sem warnings relevantes de `pyflakes` em módulos de runtime.
- Frontend sem `key={index}` em listas dinâmicas (chaves estáveis).
- `Admin.jsx` refatorado em subcomponentes sem alteração de comportamento.
- Build frontend ok + sanity checks ok (sem necessidade de rodar o agente E2E completo nesta iteração).

### Para considerar “100% produção” (futuro)
- Stripe Subscriptions + Portal.
- Resend real + reset/verify.
- Token Telegram configurado.
- Dividend tracker dedicado.
- Provider licenciado + compliance/observabilidade.
