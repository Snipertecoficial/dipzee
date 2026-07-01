# Dipzee — plan.md (Correção de Planos + Redesign Áreas Logadas)

## 1) Objectives
- Corrigir **estrutura de preços** para 3 planos pagos: **Iniciante (US$ 4,97)**, **Pro (US$ 12,97)**, **Investidor (US$ 24,99 — mantém)**, preservando trial/gating e evitando regressões.
- Executar **redesign completo das áreas logadas** (App Shell + páginas internas) conforme `/app/design_guidelines.md`, mantendo identidade Dipzee e reutilizando componentes existentes.
- Garantir consistência de i18n (EN/FR/PT/ES), estados (loading/empty/error) e qualidade de UX.

---

## 2) Implementation Steps

### Phase 1 — POC (Isolado) do Core de Billing/Planos (Stripe + Packages)
**User stories**
1. Como usuário, quero ver 3 planos claros e coerentes (Iniciante/Pro/Investidor) com preços corretos.
2. Como usuário, quero iniciar checkout do plano escolhido sem risco de manipulação de preço no client.
3. Como sistema, quero mapear `package_id → plan` corretamente e atualizar `users.plan` ao pagamento.
4. Como sistema, quero manter compatibilidade com trial de 7 dias com cartão (quando habilitado).
5. Como superadmin/dev, quero validar rapidamente os pacotes do backend e o retorno de `/billing/config`.

**Steps**
- Websearch rápido: boas práticas para “multiple subscription tiers + trial requiring card” em Stripe Checkout (sem alterar a integração emergentintegrations).
- Criar script Python mínimo (ex.: `/app/backend/poc_billing_plans.py`) para validar:
  - `GET /api/billing/config` retorna 3 planos pagos + moeda USD.
  - `POST /api/billing/checkout` aceita `starter_monthly`, `pro_monthly`, `investor_monthly` (e annual) e rejeita inválidos.
  - Verificar que `amount` é 100% server-side.
- Critério de “go”: config e validação de package_id funcionando; nenhum package antigo inválido quebrando o frontend.

---

### Phase 2 — V1 App Development (Planos + App Shell com Sidebar)
**User stories**
1. Como usuário logado, quero navegar com facilidade por um **menu lateral persistente** (desktop) e um menu mobile (Sheet).
2. Como usuário, quero um **topbar** consistente com busca global e quick actions.
3. Como usuário, quero ver os preços e nomes corretos dos planos no Upgrade e no gating.
4. Como usuário, quero que todas as páginas logadas tenham estados de **loading/empty/error** elegantes.
5. Como usuário multilíngue, quero que a UI continue natural e responsiva mesmo com textos longos.

**Backend (planos + gating)**
- Atualizar `routes_billing.py`:
  - Trocar `PACKAGES`: `starter_monthly/annual` (plan `starter`), `pro_monthly/annual` (plan `pro`), `investor_monthly/annual` (plan `investor`).
  - Preços: 4.97 / 12.97 / 24.99 (annual conforme regra atual do app ou definição explícita).
  - Manter `CURRENCY='usd'`.
- Atualizar `plans.py`:
  - Introduzir plano `starter` (ou renomear corretamente conforme decisão final) e ajustar limites.
  - Garantir compatibilidade com usuários existentes (`free`/`pro`/`investor`).

**Frontend (Upgrade + App Shell)**
- Atualizar `Upgrade.jsx`:
  - Pricing cards: `starter`, `pro`, `investor` (3 cards pagos + eventualmente Free se continuar existindo no app).
  - Ajustar `BASE_PRICES` e `package_id` (`starter_monthly`, etc.).
- Atualizar i18n (EN/FR/PT/ES):
  - Adicionar chaves para `plans.starter` + descrição/features coerentes.
  - Revisar textos de trial (cartão obrigatório) e labels.
- Implementar novo **AppShell**:
  - Sidebar responsiva (persistente/colapsável em desktop; Sheet em mobile).
  - Topbar com breadcrumb/título, search, language/currency, notificações e user menu.
  - Migrar rotas logadas para o novo shell sem quebrar navegação existente.

**Checkpoint**
- Rodar 1 teste E2E básico manual: login → navegar (dashboard/screener/news/upgrade/admin) → abrir search → trocar idioma/moeda.

---

### Phase 3 — Redesign das Páginas Logadas (Layouts + Estados)
**User stories**
1. Como usuário, quero um Dashboard em “bento grid” que destaque oportunidades (3 segundos para decidir).
2. Como usuário, quero um Screener com filtros à esquerda e resultados densos à direita (tabela).
3. Como usuário, quero uma página de ativo com tabs (Overview/Dividends/Target/News) e CTAs claros.
4. Como usuário, quero ver Notícias em feed com filtros + trilho lateral de trending.
5. Como usuário, quero gerenciar alertas/notificações/configurações em layouts consistentes e rápidos.

**Steps**
- Dashboard: reorganizar em grid 12 col (main + right rail) + watchlist tabela em desktop.
- Screener: implementar two-panel (filters sticky + results table) com skeleton/empty/error.
- AssetDetail: header forte + tabs + right rail (alertas + news) com skeleton/empty/error.
- News: feed + filtros/trending.
- Alerts / Notifications / Settings / Admin: alinhar com blueprint (tabs, tabelas densas, split view quando aplicável).

---

### Phase 4 — Polish, Consistência, Acessibilidade
**User stories**
1. Como usuário, quero micro-interações suaves (sem “UI travada” ou saltos).
2. Como usuário, quero números alinhados e formatação consistente (tnum, moeda/percent).
3. Como usuário, quero que dark mode continue legível.
4. Como usuário, quero tooltips/ajudas para métricas sem poluir a tela.
5. Como usuário, quero performance boa (sem re-renders excessivos em listas/tabelas).

**Steps**
- Garantir `data-testid` onde necessário (conforme guidelines).
- Revisar componentes para `transition-*` (evitar `transition: all`).
- Ajustar responsividade (mobile-first) e tolerância i18n.

---

### Phase 5 — Testes (Backend + Frontend) e Regressão
**User stories**
1. Como usuário, quero conseguir fazer upgrade sem erros de package_id.
2. Como usuário, quero navegar em todas as páginas logadas sem layout quebrado.
3. Como superadmin, quero acessar /admin sem erros e ver dados carregando.
4. Como usuário, quero criar/editar alertas e ver notificações.
5. Como usuário, quero buscar e abrir tickers via search sem travar.

**Steps**
- Rodar `testing_agent_v3` cobrindo:
  - `/login`, `/app/dashboard`, `/app/screener`, `/app/news`, `/app/asset/:ticker`, `/app/alerts`, `/app/notifications`, `/app/settings`, `/app/upgrade`, `/app/admin`.
- Ajustar bugs encontrados e repetir até passar.

---

## 3) Next Actions
1. Confirmar decisão de nomenclatura no código: manter `free` + 3 pagos, ou converter `free → starter`.
2. Implementar Phase 1 (POC billing) e corrigir backend/Upgrade/i18n.
3. Implementar novo AppShell com sidebar (Phase 2) e migrar rotas.
4. Redesign incremental das páginas começando por Dashboard + Upgrade.
5. Rodar `testing_agent_v3` ao final de cada fase.

---

## 4) Success Criteria
- Preços corretos e coerentes em **backend + frontend + i18n**: Iniciante 4,97; Pro 12,97; Investidor 24,99 (USD).
- `package_id`/checkout funcionando e impossível de manipular preço via client.
- App Shell com sidebar responsiva implementado sem quebrar rotas/logged-in UX.
- Dashboard/Screener/Asset/News/Alerts/Notifications/Settings/Admin com estados loading/empty/error e layout conforme guidelines.
- `testing_agent_v3` passa sem erros críticos e sem regressões visuais/funcionais.
