# Dipzee — Deploy & verificação

> Resumo honesto de como o dipzee sobe para produção, como **confirmar** que subiu,
> e o que fazer depois. (Isto é do dipzee — o A.REIS, na mesma VPS, é outro projeto
> com deploy manual próprio; não confundir.)

## Como o deploy funciona (automatizado)

Deploy = **push para `main`**. Não há build nem comando manual na VPS.
[`.github/workflows/deploy.yml`](.github/workflows/deploy.yml):

1. **Build backend** (imagem Docker) com o commit carimbado (`--build-arg GIT_SHA=<sha>`).
2. **Roda os testes DENTRO da imagem** (`pytest tests/`). Teste vermelho = **deploy abortado** (as imagens nem são publicadas).
3. **Push das imagens** (backend + frontend) para o **GHCR** (`ghcr.io/snipertecoficial/...`).
4. **Deploy por SSH**: a VPS só faz `pull` das imagens prontas e `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`. **A VPS não builda** (o build do CRA estourava memória no host pequeno — por isso build-once/deploy-many).
5. **Healthcheck** pós-deploy (15 tentativas até `{"status":"ok"}`).

Duração típica: **~10–20 min** (build + testes + push GHCR + pull na VPS). É lento — por isso "parece que não subiu". Não é lentidão de bug; é o pipeline.

A chave de deploy da VPS é **somente-leitura** (só faz `pull`). Correções **sempre** vêm por git — nunca editar na VPS à mão (o próximo `git reset --hard` apaga).

## Como CONFIRMAR que subiu (1 comando)

Cada imagem carrega o commit em `GET /api/health` → campo `commit`:

```bash
curl -s https://dipzee.com/api/health
# {"status":"ok","checks":{"db":true,"scheduler":true},"commit":"<sha>"}
```

Ou o verificador (espera até o commit do HEAD local estar no ar):

```bash
python scripts/verify_deploy.py            # espera o HEAD local no dipzee.com
python scripts/verify_deploy.py --timeout 1500
```

Sai `0` quando o `commit` no ar == o commit esperado **e** `status=ok`; senão avisa e sai `1`
(aí veja o run **GitHub → Actions → "Deploy to VPS"** — build/teste/push ou o passo SSH podem ter falhado).

## Depois do deploy — passos que dependem de você (VPS)

- **Londres (London Strategic Edge):** o código está no ar, mas o catálogo LSE só popula quando:
  1. `LSE_API_KEY=...` estiver no **`.env` da VPS** (nunca commitado), e
  2. rodar a importação (superadmin): `POST /api/admin/catalog/import-lse`, ou esperar o job mensal.
- **Catálogo US:** popula sozinho no startup (busca o diretório do Nasdaq Trader). Se a VPS
  bloquear a saída para `nasdaqtrader.com`, rode `POST /api/admin/catalog/import-us` (superadmin).
- **Nunca** definir `SUPERADMIN_EMAIL`/`SUPERADMIN_PASSWORD` no `.env` da VPS depois que já existe
  superadmin (o seed sobrescreve a senha no boot — já causou lockout).

## Rollback

Sem blue-green. Para reverter: `git revert <sha> && git push` (redeploya a versão anterior),
ou re-disparar o deploy de um commit bom via **Actions → Run workflow**.
