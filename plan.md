# Dipzee — plan.md (Planos + Paywall + Mercado resiliente + App Premium)

**Status:** ATUALIZADO — **Fase G (Stripe Recorrente + Trial 7 dias + IA Analista Virtual)** — ⏳ **EM ANDAMENTO (P0)**

> **Nota de idioma:** usuário primário pt-BR; todas as interações/UX devem manter pt-BR como primeira classe (com i18n EN/FR/ES já existente).

---

## 1) Objectives

### Objetivos já concluídos (baseline do produto) — ✅
- **Estrutura de planos paga (USD) concluída** com 3 tiers e pricing server-side:
  - **Starter (`starter`) — US$ 4,97/mês**
  - **Pro (`pro`) — US$ 12,97/mês**
  - **Investor (`investor`) — US$ 24,99/mês**
  - Anual: **`monthly * 12 * 0.8`** (~20% OFF)
- **Paywall upfront**: usuários com `plan="none"` são redirecionados para `/app/upgrade` antes de acessar o app.
- **Redesign das áreas logadas** (AppShell premium com sidebar/topbar).
- **Redesign da landing/auth** (premium), remoção do badge “Made with Emergent”, favicon/título configurados.
- **Dark Mode** completo.
- **Perfil editável** com avatar Base64 e preferências.
- **Mercados** (abas + filtro) + **Asset Detail** com Insights.
- **Portfolio P&L** + export CSV.
- **Multi-admin / dual-superadmin** (múltiplos e-mails; fallback hardcoded em `server.py`).

### Qualidade de Código + Refatoração Admin — ✅ CONCLUÍDA
- Backend sem warnings relevantes de `pyflakes` nos módulos de runtime.
- Frontend sem `key={index}` em listas dinâmicas.
- `Admin.jsx` refatorado em sub-tabs modulares e verificado.

### Phase F — Robustez + i18n + Backtest v2 + Segurança — ✅ CONCLUÍDA
- **F1 Depoimentos por idioma** (PT/EN/ES/FR) via `i18n.language`.
- **F2 Mercado resiliente (cascata)**: Finnhub → yfinance → Investing → Mongo cache stale.
- **F3 Backtest v2**: equity curve, estratégias (Buy the Dip / SMA Cross), tooltips, drawdown/time-in-market.
- **F4 Segurança**: rate limiting, brute-force lockout, headers de segurança e CSP.

---

## 2) Implementation Steps

### Phase 0 — Auditoria/Inventário — ✅ CONCLUÍDA
- Auditoria de limites, intraday, alert types, UI do Upgrade.
- Matriz “Plano → features → status”.

### Phase A — Fundação (Capacidades por plano + Perfil + Dark Mode) — ✅ CONCLUÍDA

### Phase B — Mercados + Ativos/Notícias — ✅ CONCLUÍDA

### Phase C — Investidor (Portfolio P&L + Backtest + Canais) — ✅ CONCLUÍDA

### Phase D — Gating, Upsell, Qualidade e “Lista 100%” — ✅ CONCLUÍDA (MVP)

### Phase E — Qualidade de Código + Refatoração Admin — ✅ CONCLUÍDA

### Phase F — Robustez sem chaves + i18n Depoimentos + Backtest v2 + Segurança — ✅ CONCLUÍDA

---

## Phase G — Reta Final (P0): Stripe REAL Recorrente + Trial 7 dias + IA Analista Virtual — ⏳ EM ANDAMENTO

### Contexto (decisões confirmadas pelo usuário)
- **Stripe**:
  - Usar as **mesmas chaves de teste já fornecidas** (`sk_test`, `pk_test`, `rk_test`).
  - **Criar Products/Prices dinamicamente via API** (sem Price IDs pré-criados).
  - Preços em **USD** iguais aos cards da home:
    - Starter: 4.97/mês
    - Pro: 12.97/mês
    - Investor: 24.99/mês
    - Anual: `monthly*12*0.8`
  - Trial de **7 dias** para **todos** os planos (mensal e anual), com **cartão obrigatório upfront** (`payment_method_collection="always"`).
- **Playbook Stripe**:
  - O playbook retornou o wrapper `emergentintegrations` (focado em pagamento único), **inadequado** para assinaturas.
  - Implementação correta: **SDK nativo do Stripe** (`stripe==14.4.1`, já instalado).
- **IA Analista Virtual**:
  - Usar **EMERGENT_LLM_KEY** (sem custo por enquanto) com **OpenAI `gpt-5.4`**.
  - Gating: **apenas Pro + Investor**.
- **Ordem de execução:** Stripe primeiro → depois IA. Usuário pediu “**seguir sem parar**”.

---

### G1) Stripe REAL (assinaturas recorrentes) + Trial 7 dias (Starter/Pro/Investor) — ⏳
**Objetivo:** trocar o fluxo atual (mock/one-time) por **assinatura recorrente** no Stripe, garantindo que **trialing/active** desbloqueie o app e **canceled/unpaid** volte para `plan="none"`.

#### Requisitos de produto
- Trial 7 dias em **Starter/Pro/Investor** (mensal e anual).
- Cartão obrigatório no trial (sem acesso sem CC).
- Self-service de upgrade/downgrade/cancelar via **Customer Portal**.
- Estado de plano consistente via **polling (primário)** + **webhook (quando configurado)**.
- Preços **server-side** (proteção contra manipulação do frontend).

#### Trabalho técnico — Backend (FastAPI)
1) **Variáveis de ambiente (.env)**
   - Substituir `STRIPE_API_KEY` (mock) pela **sk_test real** fornecida.
   - Adicionar:
     - `STRIPE_PUBLISHABLE_KEY=pk_test_...`
     - (Opcional no início) `STRIPE_WEBHOOK_SECRET=whsec_...` quando o endpoint for criado no dashboard.

2) **Reescrever `routes_billing.py` usando Stripe SDK (assinaturas)**
   - `POST /api/billing/checkout`
     - `stripe.checkout.sessions.create` com:
       - `mode="subscription"`
       - `line_items=[{price_data:{currency:"usd",unit_amount:<cents>,product_data:{name},recurring:{interval:"month"|"year"}},quantity:1}]`
       - `subscription_data={"trial_period_days":7, "metadata":{user_id,plan,billing,package_id}}`
       - `payment_method_collection="always"`
       - `client_reference_id=user_id`
       - `success_url`/`cancel_url` construídos a partir de `origin_url` (nunca hardcode)
     - **Customer**:
       - Criar/recuperar `stripe_customer_id` e persistir em `users`.
     - Criar registro em `payment_transactions` (já existe) como `initiated/pending`.
   - `GET /api/billing/status/{session_id}`
     - `stripe.checkout.sessions.retrieve(..., expand=["subscription"])`
     - Considerar **sucesso** quando subscription estiver `trialing` ou `active` (mesmo que `payment_status` não seja `paid` durante trial).
     - Aplicar upgrade idempotente do plano + persistir:
       - `stripe_subscription_id`, `trial_ends_at`, `current_period_end`.
   - `POST /api/billing/portal`
     - Criar sessão do **Billing Portal** via `stripe.billing_portal.sessions.create`.
     - Incluir `return_url` para voltar ao app.
   - `GET /api/billing/subscription` (qualidade de UX)
     - Retornar status atual (trialing/active/canceled), datas relevantes e plano.

3) **Webhook Stripe (opcional no começo, obrigatório para produção)**
   - `POST /api/webhook/stripe`
   - Se `STRIPE_WEBHOOK_SECRET` estiver configurado:
     - Verificar assinatura com `stripe.Webhook.construct_event`.
   - Eventos mínimos:
     - `checkout.session.completed`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_failed`
   - Regras:
     - `trialing/active` → garantir `users.plan` correto
     - `canceled/unpaid` → `users.plan="none"` (exceto `role=superadmin`)
   - **Idempotência**: registrar `event_id` processados (collection `stripe_events` ou campo no doc) para evitar dupla aplicação.

4) **Persistência (MongoDB)**
   - Reaproveitar `payment_transactions`.
   - Criar coleções (mínimo recomendado):
     - `billing_subscriptions` (auditoria do estado Stripe)
     - `stripe_events` (dedupe de webhook)
   - Atualizar `users`:
     - `stripe_customer_id`
     - `stripe_subscription_id` (ou último ativo)

5) **Performance/robustez**
   - Stripe SDK é síncrono: envolver chamadas em `asyncio.to_thread(...)` para não bloquear o event loop.

#### Trabalho técnico — Frontend (React)
- **Upgrade.jsx**
  - Manter criação do checkout via backend.
  - Ajustar polling:
    - hoje verifica `payment_status === 'paid'`; atualizar para aceitar `active/trialing` (ex.: `data.active === true`).
  - Mostrar feedback de “trial iniciado” e atualizar `user.plan` local.
- **Settings.jsx**
  - Adicionar botão **“Gerenciar assinatura”** → `POST /billing/portal` → redirect para `url`.

#### Critérios de aceite (G1)
- Iniciar trial de 7 dias (mensal/anual) em qualquer plano.
- `plan` do usuário muda para `starter/pro/investor` ao completar checkout (trialing) e continua em active.
- Cancelamento no portal reflete no app (plan=none) via webhook (ou fallback por verificação periódica).

---

### G2) IA Analista Virtual (LLM) — gated para Pro + Investor — ⏳
**Objetivo:** gerar um resumo interpretável (educacional) para um ativo, usando contexto do Dipzee (score + dados de mercado) e resposta localizada (pt/en/es/fr).

#### Trabalho técnico — Backend
1) **Feature flag**
   - `plans.py`: adicionar `ai_analyst` em **Pro** e **Investor**.

2) **Rotas**
- Criar `routes_ai.py`:
  - `GET /api/ai/analyst/{ticker}`
  - `Depends(require_feature('ai_analyst'))`
  - Agregar contexto via:
    - `refresh_asset(ticker)`
    - `get_company_news(ticker)` (quando útil)
  - Chamar LLM via `emergentintegrations.llm.chat`:
    - `LlmChat(api_key=EMERGENT_LLM_KEY, ...)`
    - `.with_model("openai", "gpt-5.4")`
  - Retornar JSON estruturado:
    - `summary`
    - `thesis_bullets[]`
    - `risks[]`
    - `catalysts[]`
    - `horizon`
    - `confidence` (0–100)
  - **Cache Mongo**: collection `ai_analyses` por `ticker+locale` por ~12h (e opção `?refresh=1`).
  - Rate limit extra (além do middleware) se necessário.

3) **Registro no server**
- `server.py`: incluir router `routes_ai` (sem tocar no fallback de superadmin).

#### Trabalho técnico — Frontend
- `AssetInsights.jsx`
  - Nova tab **“Analista Virtual”** gated via `<FeatureGate feature="ai_analyst">`.
  - Botão “Gerar/Atualizar” + estado de loading.
  - Render:
    - resumo
    - listas de tese/riscos/catalisadores
    - disclaimer (educacional)

#### i18n
- Adicionar chaves em `locales/{pt,en,fr,es}.json`:
  - `asset.aiAnalystTitle`, `asset.aiAnalystGenerate`, `asset.aiAnalystDisclaimer`, etc.

#### Critérios de aceite (G2)
- Pro/Investor conseguem gerar e visualizar análise.
- Starter recebe gate/upsell.
- Conteúdo localizado conforme `user.locale`.
- Cache reduz chamadas repetidas.

---

## 3) Next Actions (a partir de agora)

### Imediato (P0 — Phase G)
1) **Stripe**: injetar chaves reais no `.env` e reescrever `routes_billing.py` com SDK nativo.
2) **Frontend**: ajustar `Upgrade.jsx` (trialing/active) + adicionar Customer Portal em `Settings.jsx`.
3) **Webhook**: implementar handler com verificação opcional (ativa quando `whsec` existir).
4) **Sanity tests (manual/curl + UI)**:
   - Criar checkout, completar no Stripe test
   - Verificar `plan` alterado após status
   - Portal abre e cancelamento reflete no app
5) **IA Analista Virtual**: feature flag + endpoint + cache + UI tab + i18n.

---

## 4) Success Criteria

### Já atingidos — ✅
- UI premium (landing + app), dark mode, multi-admin.
- Mercado resiliente com cache.
- Backtest v2 e camadas de segurança.

### Para concluir a Phase G (reta final) — 🎯
- Stripe recorrente ponta a ponta com trial 7 dias em todos os planos.
- Customer Portal funcionando.
- Webhooks sincronizando plano/estado do usuário (com idempotência).
- IA Analista Virtual disponível em Pro/Investor com cache + i18n.

### Para produção (futuro) — 📌
- Termos/Privacidade + compliance.
- Emails reais (Resend) + alertas de fim de trial.
- Observabilidade (APM/metrics) + WAF.
- Opcional: provedor de dados licenciado com SLA quando houver orçamento.
