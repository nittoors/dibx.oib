#!/usr/bin/env bash
set -euo pipefail

tag="${IMAGE_TAG:-local-validation}"
trivy_image="${TRIVY_IMAGE:-aquasec/trivy:0.74.0}"
trivy_cache_volume="${TRIVY_CACHE_VOLUME:-dibx-trivy-cache}"

for image in "dibx/oib-api:$tag" "dibx/oib-web:$tag" "dibx/oib-jobs:$tag"; do
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$trivy_cache_volume:/root/.cache/trivy" \
    "$trivy_image" image \
    --scanners vuln,secret \
    --severity HIGH,CRITICAL \
    --exit-code 1 \
    "$image"
done

echo "OIB images have no high/critical findings."
