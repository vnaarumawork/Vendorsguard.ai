#!/usr/bin/env bash
# Deploy VendorGuard AI to Google Cloud Run.
# Prereqs: gcloud CLI authenticated, a GCP project, and a GOOGLE_API_KEY
# (AI Studio) stored in Secret Manager as 'google-api-key' for live mode.
set -euo pipefail

PROJECT_ID="${1:?Usage: ./deploy.sh <gcp-project-id> [region]}"
REGION="${2:-us-central1}"
SERVICE="vendorguard-ai"

gcloud config set project "$PROJECT_ID"

# Build and deploy straight from source (Cloud Build uses the Dockerfile)
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-secrets "GOOGLE_API_KEY=google-api-key:latest" \
  --set-env-vars "VENDORGUARD_MODE=auto"

echo "✅ Deployed. Public URL:"
gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)'
