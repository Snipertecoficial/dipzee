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
4. **Preflight e backup**: completa somente as novas configurações de segurança ausentes, cria um snapshot AES-GCM, autentica o conteúdo e publica um envelope GPG por 7 dias antes de tocar nos containers.
5. **Deploy por SSH**: a VPS só faz `pull` das imagens prontas e `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`. **A VPS não builda**.
6. **Verificação externa**: confere o SHA no health do backend, no `version.json` do frontend e baixa um asset JavaScript. Falha restaura os IDs exatos das imagens anteriores.

Duração típica: **~10–20 min** (build + testes + push GHCR + pull na VPS). É lento — por isso "parece que não subiu". Não é lentidão de bug; é o pipeline.

A chave de deploy controla o checkout e os containers deste projeto na VPS; trate-a como segredo de produção. Correções **sempre** vêm por git — nunca editar na VPS à mão (o próximo `git reset --hard` apaga arquivos versionados).

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
- `SUPERADMIN_EMAIL`/`SUPERADMIN_PASSWORD` continuam obrigatórios no preflight, mas o seed atual preserva a senha armazenada de contas existentes e apenas reforça papel/plano.

## Backup temporário sem S3

O repositório é público. Por isso, o artifact não deve ser tratado como privado: ele contém somente um envelope GPG cifrado. A chave que abre esse envelope é derivada da chave SSH de deploy custodiada no ambiente `production`; o snapshot AES-GCM e sua chave ficam dentro do envelope.

Para validar e desempacotar um artifact em uma estação segura que possua a mesma chave SSH:

```bash
bash scripts/unpack_production_recovery.sh \
  dipzee-production-recovery-RUN-ATTEMPT.tar.gpg \
  /caminho/seguro/vps-deploy-key \
  /caminho/novo/recovery-output
```

O diretório resultante contém dados de produção e a `recovery-key`; mantenha modo `0700/0600`, não versione e não use para inspeção. Restaure preferencialmente em um banco vazio/isolado e valide índices e migrations antes de promover. O artifact expira em 7 dias e é apenas uma ponte até configurar S3/R2/B2.

## Rollback

O workflow mantém temporariamente os IDs exatos das imagens anteriores. Se a
ativação, o health externo ou a validação do frontend falhar, ele restaura esses
containers e remove as tags temporárias ao finalizar.

Esse rollback automático é de **aplicação**, não um rollback destrutivo do banco.
Migrations devem continuar compatíveis com a versão N-1 (expand/contract). Para
recuperar dados do artifact, desempacote-o em estação segura e restaure primeiro
em um banco vazio/isolado; valide documentos, índices e migrations antes de
qualquer promoção. O restore recusa banco não vazio por padrão.

Para uma reversão planejada de código: `git revert <sha> && git push`, ou execute
o workflow sobre um commit bom que ainda seja ancestral de `main`.
