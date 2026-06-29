# Dipzee — plan.md

## 1) Objectives
- Provar e estabilizar o **core**: obter dados via **yfinance/Yahoo** (TSX/US) + normalizar dividend yield + calcular **Opportunity Score** com classificação/flags.
- Construir o SaaS web **multilíngue (EN/FR/PT/ES)** com **React (CRA) + FastAPI + MongoDB**, UI seguindo a marca Dipzee.
- Entregar fluxo completo: **buscar ativo → ver score/detalhes → watchlist → alertas → notificações (email + inbox) → assinaturas Stripe** com feature-gating por plano.
- Deixar **Resend + Stripe prontos** (chaves depois) e orientar **conexão GitHub via UI do Emergent**.

## 2) Implementation Steps

### Phase 1 — POC do Core (dados Yahoo/yfinance + score) [não avançar sem passar]
**User stories**
1. Como usuário, quero consultar um ticker (US/TSX) e receber preço/52w low/high/target/div yield confiáveis.
2. Como usuário, quero que dividend yield seja consistente (decimal) para não distorcer o score.
3. Como usuário, quero que o Opportunity Score bata com exemplos (TELUS/NVDA) para confiar na lógica.
4. Como dev, quero uma interface DataProvider trocável para migrar depois para provider licenciado.
5. Como dev, quero tratamento de erro (campo ausente/rate limit) sem quebrar a API.

**Steps**
- Websearch rápido: melhores práticas/pegadinhas do **yfinance** (campos, rate limit, TSX “.TO”, dividendYield inconsistências).
- Criar script Python isolado: 
  - fetch yfinance para 2 tickers (1 US, 1 TSX), imprimir campos brutos.
  - normalizar `dividendYield` (percent vs decimal vs None).
  - rodar função pura `compute_opportunity_score()`.
  - validar unit tests (2 casos fornecidos) e logar discrepâncias.
- Definir `DataProvider` + `YFinanceProvider` (contrato de saída padronizado).
- Critérios de “go”: ambos testes passam e ao menos 1 ticker TSX + 1 US retornam dados suficientes.

### Phase 2 — V1 App (sem Stripe/Resend ativos; sem scheduler avançado)
**User stories**
1. Como visitante, quero ver uma landing page em EN/FR/PT/ES explicando Dipzee e começar grátis.
2. Como usuário, quero me cadastrar/logar e acessar um dashboard protegido.
3. Como usuário, quero buscar um ticker e abrir a página do ativo com score, badge e explicação.
4. Como usuário, quero adicionar/remover ativos da minha watchlist e ver cards ordenados por score.
5. Como usuário, quero alternar idioma e moeda (CAD/USD/BRL) e ver formatação correta.

**Backend (FastAPI + MongoDB)**
- Estrutura modular: `routers/`, `services/`, `providers/`, `models/`.
- Modelos + índices:
  - `users` (locale/currency/plan), `assets` (upsert por ticker), `watchlist_items`.
- Endpoints:
  - `GET /api/score/{ticker}` (retorna score + breakdown + flags + explicação).
  - `POST /api/assets/refresh/{ticker}` (usa provider + upsert asset).
  - Watchlist CRUD: list/create/delete.
- Auth email/senha (sessions/JWT do template) + rotas protegidas.
- Feature-gating básico por plano: Free (10 watchlist, 1 idioma, EOD flag) já preparado.

**Frontend (React CRA)**
- Setup: `react-router`, `react-i18next`, tema (Indigo/Mint/neutros), fontes Sora/Inter.
- Componentes:
  - Language switcher, currency switcher.
  - Search (ticker/nome) → chama refresh → navega para Asset Detail.
  - Asset Detail: dial circular score (cores semânticas), gauge 52w, stats, botões watchlist/alert.
  - Dashboard “Oportunidades hoje”: cards watchlist ordenados por score + filtros (Buy zone / Income>=4%).
  - Settings (persistir locale/currency no perfil).
- Traduções completas (EN/FR/PT/ES) para todas as telas V1.

**Teste ao fim da fase**
- Rodar 1 ciclo E2E: cadastrar → buscar ticker → ver score → adicionar watchlist → filtros → trocar idioma/moeda.

### Phase 3 — Alertas end-to-end (com Resend “ready”, chave depois)
**User stories**
1. Como usuário, quero criar alertas (buy zone/sell zone/target/price/score/dividend/daily drop).
2. Como usuário, quero receber eventos no inbox in-app quando um alerta dispara.
3. Como usuário, quero receber email localizado quando um alerta dispara (quando a chave existir).
4. Como usuário Free, quero limite de 3 alertas ativos e mensagens claras ao exceder.
5. Como usuário, quero editar/desativar alertas sem perder histórico.

**Steps**
- Modelos `alerts` + `alert_events` + índices.
- Endpoints: CRUD de alerts, list inbox, marcar como lido.
- Motor de avaliação:
  - “edge-trigger” (não disparar repetido) via `last_triggered_at` + estado anterior relevante no payload.
  - Execução no refresh do ativo.
- Integração Resend: serviço encapsulado; se sem chave, log + apenas inbox.
- UI: modal “Create alert”, lista de alertas por ticker, inbox notificações.
- Teste E2E: criar alerta de `price_above` baixo (forçando) → gerar evento.

### Phase 4 — Scheduler e refresh intraday (APScheduler)
**User stories**
1. Como usuário, quero que meus tickers acompanhados atualizem automaticamente.
2. Como usuário Investor, quero refresh intraday (15 min horário de mercado).
3. Como usuário Free/Pro, quero refresh diário (pós-fechamento) confiável.
4. Como usuário, quero que erros de provider não quebrem o app.
5. Como dev, quero observar logs/metrics simples do scheduler.

**Steps**
- APScheduler:
  - job diário (after close NA) para tickers em watchlist/alert.
  - job intraday (15 min, market hours) condicionado a existir usuário Investor relevante.
- Rate-limit/backoff simples no provider.
- Teste: simular execução manual do job e verificar atualização de `assets.updated_at`.

### Phase 5 — Assinaturas Stripe + feature gating completo (chaves depois)
**User stories**
1. Como usuário, quero fazer upgrade para Pro/Investor via Stripe Checkout.
2. Como usuário, quero gerenciar/cancelar assinatura no Customer Portal.
3. Como sistema, quero atualizar `users.plan` via webhooks.
4. Como usuário Free, quero ver paywall claro ao exceder limites (watchlist/alertas/idiomas).
5. Como usuário, quero alternar mensal/anual com desconto.

**Steps**
- Estruturar produtos/preços (CAD base; preparar multi-moeda).
- Checkout + Portal endpoints (com placeholders até chave).
- Webhook handler (verificação assinatura) → atualizar plano.
- Middleware de gating: watchlist limit, alert limit, idiomas, intraday.
- UI Upgrade page + Pricing table.
- Teste em modo Stripe test quando chaves forem fornecidas.

### Phase 6 — Screener + digest (opcional) + polimento final
**User stories**
1. Como usuário Pro/Investor, quero ver um screener com top oportunidades por score.
2. Como usuário, quero filtrar por setor/dividend/min upside/range position.
3. Como usuário, quero “Top oportunidades do dia” em email (quando habilitado).
4. Como usuário, quero UX consistente com a marca e responsivo.
5. Como usuário, quero disclaimers visíveis (não é recomendação personalizada).

**Steps**
- Screener backend (batch diário) + endpoint paginado.
- UI screener.
- (Opcional) Digest por idioma (Resend).
- Revisão i18n (zero strings hardcoded).
- Hardening: cache simples, retries, validações.

## 3) Next Actions
- DONE: POC, V1 (auth/i18n/landing/dashboard/asset/watchlist/settings), alerts+notifications, scheduler, Stripe (test mode), screener.
- Pending (user-driven / later): provide real Stripe + Resend keys; connect GitHub via Emergent UI; deploy + custom domain via Emergent UI; replace yfinance with a licensed provider (FMP/Finnhub) before charging; optional AI daily digest email.

## 4) Success Criteria
- POC: yfinance retorna campos essenciais (ou fallback) e os 2 unit tests do score passam.
- V1: fluxo completo (login → search → asset detail → watchlist → dashboard → i18n/currency) funcionando e traduzido.
- Alertas: cria/avalia/dispara com inbox; email pronto (ativar quando chave Resend chegar).
- Stripe: checkout/portal/webhooks implementados e prontos para chaves; gating por plano efetivo.
- Deploy: app estável no Emergent; instruções para **Save/Connect to GitHub** via UI entregues.