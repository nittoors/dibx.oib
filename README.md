# DIBX OIB Readiness

Production source package for OIB Readiness at
`https://www.dibx.ai/OIBReadiness/`.

This repository owns the OIB React application, FastAPI service, deterministic synthetic
seed/baseline data, and database jobs image. Shared AWS infrastructure is maintained in
`Nittoors/dibx.esi` to preserve one authoritative Terraform state and avoid conflicting
applies.

Production images are Linux ARM64, non-root, vulnerability-scanned, and labeled with the
GitHub source repository and revision. Base images and Python dependencies are pinned.

Local validation:

```bash
corepack enable
pnpm install --frozen-lockfile
pnpm lint && pnpm typecheck && pnpm test && pnpm build
python -m venv .venv
.venv/bin/python -m pip install --requirement apps/oib-api/requirements-dev.lock
.venv/bin/ruff check apps/oib-api
.venv/bin/mypy --config-file apps/oib-api/pyproject.toml apps/oib-api/app apps/oib-api/tests
IMAGE_TAG=local-validation SOURCE_REVISION=local-review ./scripts/build-production-images.sh
IMAGE_TAG=local-validation ./scripts/scan-production-images.sh
```

The full migration, seed-reconciliation, and test workflow requires PostgreSQL and is
exercised by `.github/workflows/validate.yml`. The security script is intentionally strict:
it fails when any high/critical finding is disclosed, including an upstream finding for
which a fixed package is not yet available.
