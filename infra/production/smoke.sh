#!/bin/sh
set -eu

base_url=${1:?Usage: infra/production/smoke.sh https://journey.example.com}

case "$base_url" in
  https://*) ;;
  *)
    echo "Production smoke requires an HTTPS URL" >&2
    exit 1
    ;;
esac

curl --fail --silent --show-error "$base_url/health/live"
printf '\n'
curl --fail --silent --show-error "$base_url/health/ready"
printf '\n'
curl --fail --silent --show-error --output /dev/null "$base_url/"

echo "production_smoke=PASS"
