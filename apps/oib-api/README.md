# OIB Readiness API

This service was vendored from the rebuilt Depot Readiness application at git revision
`d3476cf53cf31a388d5ecc99409e8415c44ac7bd`. It retains the source FastAPI contracts,
PostgreSQL migrations, deterministic seed process, reconciliation checks, and Cognito
authorization model. The production Dockerfiles in this directory adapt it to the shared
DIBX ECS/RDS platform; the source application's standalone CDK stack is intentionally not used.
