# Dipzee — plan.md (Correção de Planos + Redesign Áreas Logadas) — ATUALIZADO

## 1) Objectives
- **Objetivo principal (concluído):** corrigir a **estrutura de preços** e o **billing server-side** para suportar **3 planos pagos** em USD:
  - **Iniciante (`starter`) — US$ 4,97/mês**
  - **Pro (`pro`) — US$ 12,97/mês**
  - **Investidor (`investor`) — US$ 24,99/mês (mantém)**
  - Mantendo **trial de 7 dias** (com cartão) e evitando manipulação de preço no client.
- **Objetivo principal (concluído):** executar o **redesign completo das áreas logadas** (App Shell + navegação) conforme `/app/design_guidelines.md`, mantendo identidade Dipzee e reutilizando componentes existentes.
- **Objetivo de qualidade (concluído):** garantir consistência de i18n (EN/FR/PT/ES), estados e UX, e validar com **teste E2E**.

> Status geral desta fase: **CONCLUÍDO** (validado por `testing_agent_v3` — iteration_4, sucesso 100%).

---

## 2) Implementation Steps

### Phase 1 — POC (Isolado) do Core de Billing/Planos (Stripe + Packages)
**User stories**
1. Como usuário, quero ver 3 planos claros e coerentes (Iniciante/Pro/Investidor) com preços corretos.
2. Como usuário, quero iniciar checkout do plano escolhido sem risco de manipulação de preço no client.
3. Como sistema, quero mapear `package_id → plan` corretamente e atualizar `users.plan` ao pagamento.
4. Como sistema, quero manter compatibilidade com trial de 7 dias com cartão (quando habilitado).
5. Como superadmin/dev, quero validar rapidamente os pacotes do backend e o retorno de `/billing/config`.

**Steps (implementado)**
- Atualizado backend para expor pacotes **server-side** em `GET /api/billing/config`.
- Validação de `package_id` implementada em `POST /api/billing/checkout` (inválidos retornam 400).

**Entregáveis / arquivos alterados**
- `/app/backend/routes_billing.py` — `PACKAGES` com:
  - `starter_monthly (4.97)`, `starter_annual (47.71)`
  - `pro_monthly (12.97)`, `pro_annual (124.51)`
  - `investor_monthly (24.99)`, `investor_annual (239.90)`
  - `CURRENCY='usd'`

**Critério de “go” (atingido)**
- `/billing/config` e validação de packages funcionando.

---

### Phase 2 — V1 App Development (Planos + App Shell com Sidebar)
**User stories**
1. Como usuário logado, quero navegar com facilidade por um **menu lateral persistente** (desktop) e um menu mobile (Sheet).
2. Como usuário, quero um **topbar** consistente com busca global e quick actions.
3. Como usuário, quero ver os preços e nomes corretos dos planos no Upgrade e no gating.
4. Como usuário, quero que todas as páginas logadas tenham layout consistente com a marca.
5. Como usuário multilíngue, quero que a UI continue natural e responsiva mesmo com textos longos.

**Backend (planos + gating) — implementado**
- Atualizado `plans.py` para incluir o plano `starter`.
- Atualizado `routes_admin.py` para aceitar `starter` em `VALID_PLANS`.

**Frontend (Upgrade + App Shell) — implementado**
- `Upgrade.jsx` redesenhado para **3 cards pagos** (Iniciante/Pro/Investidor), com **Pro destacado** e toggle Mensal/Anual.
- Novo **AppShell** refeito em `/components/TopBar.jsx` com:
  - Sidebar persistente colapsável no desktop
  - Sheet no mobile
  - Seções: Principal / Conta / Admin
  - Rodapé: plano atual + CTA upgrade (quando aplicável)
  - Topbar: título da página, busca global, idioma/moeda, notificações, menu usuário

**i18n — implementado**
- Adicionadas chaves do plano `starter` e labels de sidebar/topbar em EN/FR/PT/ES.

**Checkpoint (atingido)**
- Validação visual em Dashboard/Screener/News/Settings/Alerts/Admin dentro do novo shell.

---

### Phase 3 — Redesign das Páginas Logadas (Layouts + Estados)
**User stories**
1. Como usuário, quero um Dashboard mais “SaaS” e consistente com o novo shell.
2. Como usuário, quero navegação rápida e padronizada nas páginas internas.

**Steps (parcialmente aplicado / verificação concluída)**
- O redesenho **estrutural** das áreas logadas (shell + navegação) foi aplicado.
- As páginas internas existentes foram **validadas visualmente** dentro do novo shell (sem regressões e com consistência).

> Observação: o blueprint de redesign page-by-page em `/app/design_guidelines.md` permanece como referência para evoluções futuras (ex.: watchlist em modo tabela desktop, two-panel screener completo, asset detail com tabs mais densas), caso o produto queira elevar ainda mais a densidade/organização por página.

---

### Phase 4 — Polish, Consistência, Acessibilidade
**User stories**
1. Como usuário, quero micro-interações suaves e navegação consistente.
2. Como usuário, quero consistência visual e boa legibilidade.

**Steps (atingido nesta fase)**
- Sidebar colapsável com tooltips no modo ícone.
- Sem regressões visuais detectadas nas principais rotas.

---

### Phase 5 — Testes (Backend + Frontend) e Regressão
**User stories**
1. Como usuário, quero conseguir fazer upgrade sem erros de package_id.
2. Como usuário, quero navegar em todas as páginas logadas sem layout quebrado.
3. Como superadmin, quero acessar /admin sem erros e ver dados carregando.

**Steps (concluído)**
- Rodado `testing_agent_v3` (iteration_4) cobrindo:
  - Backend: `/billing/config`, `/billing/checkout` (válidos e inválidos), regressões (`/watchlist`, `/alerts`, `/news/market`, `/admin/stats`)
  - Frontend: login, navegação em todas as rotas principais, sidebar toggle, upgrade page (preços + toggle mensal/anual)

**Resultado**
- **100% aprovado** (backend e frontend), sem bugs críticos.
- Relatório: `/app/test_reports/iteration_4.json`

---

## 3) Next Actions
### Próximas entregas (pendências do produto — não iniciadas nesta fase)
1. **P1 — Integrar chaves reais do Resend** (hoje envio de e-mail está mockado/log).
2. **P1 — Integrar chaves reais do Stripe (produção)** (hoje usa ambiente de teste).
3. **P2 — Digest diário (AI Agent)**: e-mail com Top Oportunidades no idioma do usuário.
4. **P2 — Integração FMP** (exige chave e decisão de provider/limites/rate-limit).

### Recomendações técnicas
- Revisar limites do plano `starter` (watchlist/alerts/locales) conforme estratégia comercial.
- Se a intenção for remover o plano `free`, definir migração `free → starter` e ajustar gating/UI.

---

## 4) Success Criteria
**Atingidos nesta fase**
- Preços corretos e coerentes em **backend + frontend + i18n**:
  - Iniciante (starter) **US$ 4,97**
  - Pro **US$ 12,97**
  - Investidor **US$ 24,99**
- `package_id`/checkout funcionando e impossível de manipular preço via client (server-side).
- App Shell com sidebar responsiva implementado sem quebrar rotas/logged-in UX.
- `testing_agent_v3` passa sem erros críticos e sem regressões visuais/funcionais.

**Próximos critérios (futuros)**
- Resend e Stripe em modo produção com chaves reais + fluxo completo de cobrança/portal.
- Implementação do digest diário (AI) e/ou FMP conforme decisão de roadmap.