#!/bin/sh
set -eu

: "${OIB_WEB_API_BASE_URL:=/OIBReadiness/api/v1}"
: "${OIB_WEB_AUTH_MODE:=cognito}"
: "${OIB_WEB_COGNITO_DOMAIN:?OIB_WEB_COGNITO_DOMAIN is required}"
: "${OIB_WEB_COGNITO_CLIENT_ID:?OIB_WEB_COGNITO_CLIENT_ID is required}"
: "${OIB_WEB_COGNITO_REDIRECT_URI:=https://www.dibx.ai/OIBReadiness/}"
: "${OIB_WEB_COGNITO_LOGOUT_URI:=https://www.dibx.ai/OIBReadiness/}"
: "${OIB_WEB_COGNITO_SCOPES:=openid email profile oib-api/read}"

export OIB_WEB_API_BASE_URL OIB_WEB_AUTH_MODE OIB_WEB_COGNITO_DOMAIN
export OIB_WEB_COGNITO_CLIENT_ID OIB_WEB_COGNITO_REDIRECT_URI OIB_WEB_COGNITO_LOGOUT_URI
export OIB_WEB_COGNITO_SCOPES

envsubst \
  '${OIB_WEB_API_BASE_URL} ${OIB_WEB_AUTH_MODE} ${OIB_WEB_COGNITO_DOMAIN} ${OIB_WEB_COGNITO_CLIENT_ID} ${OIB_WEB_COGNITO_REDIRECT_URI} ${OIB_WEB_COGNITO_LOGOUT_URI} ${OIB_WEB_COGNITO_SCOPES}' \
  < /opt/oib/runtime-config.template.js \
  > /usr/share/nginx/html/OIBReadiness/config.js
