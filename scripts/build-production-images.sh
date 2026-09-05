#!/usr/bin/env bash
set -euo pipefail

platform="${CONTAINER_PLATFORM:-linux/arm64}"
tag="${IMAGE_TAG:-local-validation}"
source_revision="${SOURCE_REVISION:-uncommitted-local}"
source_repository="https://github.com/Nittoors/dibx.oib"

docker build --pull --platform "$platform" --build-arg SOURCE_REPOSITORY="$source_repository" --build-arg SOURCE_REVISION="$source_revision" -f apps/oib-api/Dockerfile.production -t "dibx/oib-api:$tag" apps/oib-api
docker build --pull --platform "$platform" --build-arg SOURCE_REPOSITORY="$source_repository" --build-arg SOURCE_REVISION="$source_revision" -f apps/oib-web/Dockerfile.production -t "dibx/oib-web:$tag" .
docker build --pull --platform "$platform" --build-arg SOURCE_REPOSITORY="$source_repository" --build-arg SOURCE_REVISION="$source_revision" -f apps/oib-api/Dockerfile.jobs -t "dibx/oib-jobs:$tag" .

echo "Built three OIB production images for $platform. No registry push was performed."
