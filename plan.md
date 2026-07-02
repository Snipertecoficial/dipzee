# Dipzee — plan.md (Planos + Paywall + Mercado resiliente + App Premium) — ATUALIZADO (Fase: F — Robustez sem Chaves + Backtest + Segurança + i18n Depoimentos)

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

### Qualidade de Código + Refatoração Admin — ✅ CONCLUÍDA
- Backend sem warnings relevantes de `pyflakes` nos módulos de runtime.
- Frontend sem `key={index}` em listas dinâmicas (chaves estáveis).
- `Admin.jsx` dividido em subcomponentes e verificado (screenshots e sanity checks).

### Integração GitHub + Features Admin/Monetização + Landing Premium — ✅ CONCLUÍDA (após pull)
- Pull do GitHub aplicado por fast-forward (commit `78e0755`).
- Novas tabs e arquitetura admin:
  - **AdminAnnouncementsTab** (CRUD de comunicados globais)
  - **AdminAdsTab** (CRUD de anúncios de parceiros)
  - **AdminHealthTab** (status do sistema + integridade de chaves + scheduler)
- Landing premium com **framer-motion**, **carrossel de depoimentos** e reforço de copy.

### Hotfixes pós-pull (stabilização do preview) — ✅ CONCLUÍDOS
- **Landing.jsx**: corrigido import quebrado do `lucide-react` que causava “Failed to compile”.
- **/api/admin/health**: corrigido erro 500 (import inexistente `scheduler`) via helper `is_scheduler_running()`.

---

## 2) Implementation Steps

### Phase 0 — Auditoria/Inventário (curto, antes de mexer) — ✅ CONCLUÍDA
- Auditoria de limites, intraday, alert types, UI do Upgrade.
- Tabela interna “Plano → features → status”.
- Ajuste de copy/i18n para evitar overpromising.

---

### Phase A — Fundação (Capacidades por plano + Perfil + Dark Mode) — ✅ CONCLUÍDA
- Catálogo de planos/capabilities e gating backend/frontend.
- Perfil editável com avatar Base64.
- Dark mode com persistência.

---

### Phase B — Mercados + Ativos/Notícias — ✅ CONCLUÍDA
- `/app/markets` com abas.
- Asset Detail com insights (charts/fundamentals/options/backtest), com gating.

---

### Phase C — Investidor (Portfolio P&L + Backtest + Canais) — ✅ CONCLUÍDA
- Portfolio com P&L e export.
- Backtest (MVP) entregue.
- Alertas (in-app + mocked email + webhook + telegram pronto).

---

### Phase D — Gating, Upsell, Qualidade e “Lista 100%” — ✅ CONCLUÍDA (MVP) / ⏳ PENDÊNCIAS (produção)
**Entregue (MVP)**
- Gating consistente backend/frontend.

**Pendências (fora do escopo imediato)**
- Stripe subscriptions/portal (depende de chaves).
- Resend e-mails reais (depende de chave).
- Telegram token.

---

### Phase E — Qualidade de Código + Refatoração Admin — ✅ CONCLUÍDA
- Correções de hooks/keys/pyflakes e extração de Admin em subcomponentes.

---

## Phase F — Robustez sem chaves + i18n Depoimentos + Backtest v2 + Segurança (fase atual) — ⏳ EM ANDAMENTO

### Contexto e decisão técnica
O usuário **não possui chaves de API** para FMP/Polygon/AlphaVantage/TwelveData/Marketstack. Para manter **estabilidade e cobertura ampla** (todos ativos disponíveis), a estratégia será:
- **Primário:** `yfinance` (sem chave, maior cobertura) + cache agressivo + fallback stale MongoDB.
- **Secundário:** Finnhub (já configurado no ambiente) para quote rápido quando disponível.
- **Terciário (último recurso):** Investing (endpoints internos) **apenas como fallback** e com hardening (timeouts, rate limit, cache), por ser instável e com risco de bloqueio.

> Nota: endpoints internos do Investing são não oficiais; serão tratados como “best effort” e nunca como única fonte.

### F1) Depoimentos localizados por idioma (Landing) — ⏳
**Requisito:** 5 depoimentos por idioma (PT/EN/ES/FR), exibidos conforme idioma selecionado.

**Plano:**
- Criar um dataset de depoimentos por locale (ex.: `frontend/src/constants/testimonials.js`).
- Selecionar a lista via `i18n.language` (slice 0,2 → `pt/en/es/fr`).
- Garantir fallback elegante (se locale não existir → EN).
- Preservar o componente `TestimonialsCarousel` e apenas trocar a fonte de dados.

**Critérios de aceite:**
- Ao trocar idioma pelo seletor, o carrossel troca os depoimentos (texto/nome/cargo) corretamente.

### F2) Camada de dados “multi-oráculo” resiliente sem chaves — ⏳
**Objetivo:** Cobrir *todos os ativos* com máxima estabilidade e antirate-limit.

**Trabalhos planejados:**
1) **Cascata defensiva real por operação** (não apenas provider único global)
   - Hoje `get_provider()` escolhe 1 provider global.
   - Ajustar para uma estratégia por operação:
     - `quote`: tentar Finnhub → yfinance → Investing → cache stale
     - `history`: yfinance → Investing → cache stale
     - `search`: yfinance search → Investing search → cache stale
   - Implementar isso em uma camada `provider_router` (ou dentro de `market_service`/`asset_service`) sem acoplar nas rotas.

2) **Cache agressivo + deduplicação de chamadas**
   - Reforçar TTLs e “single-flight” (se 10 requests pedirem o mesmo ticker, 1 busca externa, 9 aguardam cache).
   - Persistir respostas normalizadas em MongoDB (já existe padrão `market_cache`).

3) **Hardening anti-quebra para Investing**
   - Timeouts baixos (ex.: 6–10s) e circuit breaker simples (se falhar N vezes em 10 min, desativa temporariamente).
   - Sanitização de inputs (ticker/query) e limites (máximo de símbolos por batch).

**Critérios de aceite:**
- A aplicação não cai quando uma fonte externa rate-limita.
- Quote/histórico/search retornam algo útil (ou stale) em vez de 500.

### F3) Backtest v2 (didático + configurável + visual) — ⏳
**Requisito:** explicar “para que serve”, tooltips, gráfico visual, período/estratégia configuráveis.

**Plano:**
- UI (frontend `AssetInsights`/tab Backtest):
  - Seção “O que é Backtest?” com explicação curta e objetiva + aviso educacional.
  - Tooltips nos parâmetros e métricas (win rate, retorno médio, trades, etc.).
  - Controles:
    - período (ex.: 6m/1y/2y/5y)
    - estratégia (ex.: Buy & Hold vs Buy the Dip; e preparar arquitetura para expansão)
    - parâmetros básicos (hold_days, dip_threshold, etc.)
  - **Gráfico**: curva do capital da estratégia vs buy&hold (Recharts).

- Backend (`routes_backtest.py`):
  - Expandir resposta para incluir série temporal (equity curve) e parâmetros usados.
  - Validações e limites (período máximo e número de pontos) para performance.

**Critérios de aceite:**
- Usuário entende o que está rodando (copy + tooltips).
- Backtest gera um gráfico comparativo consistente.

### F4) Segurança em camadas (anti-hackers + anti-falhas) — ⏳
**Requisito:** rate limiting, anti brute force, security headers, validação/sanitização, cascata resiliente.

**Plano:**
1) **Rate limiting** (sem dependências pesadas)
   - Rate limit por IP em rotas críticas: login/register/reset, e endpoints de mercado.
   - Implementar in-memory (TTL) e, quando possível, fallback Mongo para consistência.

2) **Anti brute force no login**
   - Lockout progressivo por email+IP (ex.: 5 tentativas → bloqueio 10 min; 10 tentativas → 60 min).
   - Registrar auditoria mínima (sem armazenar senha, apenas contagem e timestamps).

3) **Security headers (CSP/HSTS/etc.)**
   - Configurar no backend (Starlette middleware) e/ou no Nginx (quando aplicável):
     - Strict-Transport-Security (produção)
     - X-Content-Type-Options, X-Frame-Options, Referrer-Policy
     - CSP mínima compatível com React (evitar quebrar assets).

4) **Validação e sanitização de inputs**
   - Normalizar tickers e queries (`A-Z0-9.^-`), limite de tamanho.
   - Validar payloads de admin (ads/announcements) e profile (já existe parte).

**Critérios de aceite:**
- Login protegido contra brute force.
- Endpoints críticos com rate limit.
- Headers básicos ativos.

### F5) Checklist de produção (superadmins e estabilidade) — ⏳
- Garantir que o seed de superadmins continue idempotente e funcionando em produção.
- Documentar claramente: preview vs produção → precisa redeploy para refletir.

---

## 3) Next Actions (a partir de agora)

### Imediato (Phase F)
1. Implementar depoimentos por idioma (5 por locale) e validar no seletor de idioma.
2. Backtest v2: UI/UX + parâmetros + gráfico + tooltips.
3. Segurança: rate limiting + anti brute force + headers + validações.
4. Robustez de mercado sem chaves:
   - reestruturar fallback por operação (quote/history/search)
   - reforçar cache/anti-rate-limit
   - Investing somente como último recurso com circuit breaker.
5. Sanity checks (preview): compile + curl endpoints + smoke UI (Landing/Admin/Asset Detail/Backtest).

### Próximo (quando houver chaves)
- Ativar provedores oficiais (FMP/Polygon/Alpha/Twelve/Marketstack) e escolher um primário com SLA.

---

## 4) Success Criteria

### Já atingidos (baseline + MVP)
- 3 planos pagos em USD + paywall trial 7 dias.
- UI premium (landing/auth + app shell) e gating consistente.
- Dados de mercado resilientes com cache e fallback.
- Perfil + avatar base64 + dark mode.
- Mercados + Asset Detail Pro+ + Portfolio/Backtest Investor.
- Admin com tabs de monetização/comunicados/health e landing premium.

### Para concluir a Phase F
- Depoimentos trocam corretamente por idioma (PT/EN/ES/FR) com 5 itens cada.
- Backtest v2 com explicação, tooltips, parâmetros e gráfico.
- Rate limiting + anti brute force + security headers + validações aplicadas.
- Camada de dados robusta sem chaves: yfinance primário, Finnhub secundário, Investing último recurso, sempre com fallback stale.

### Para considerar “100% produção” (futuro)
- Stripe subscriptions + portal.
- Resend e-mails reais.
- Telegram token.
- Provider licenciado + compliance (termos/privacidade) + observabilidade (metrics/logs).
