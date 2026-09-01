#!/usr/bin/env bash
# Deploy AVENIQ Backend to Google Cloud Run

set -e

PROJECT_ID="${GCP_PROJECT_ID:-aveniq-prod}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="aveniq-backend"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "===================================================="
echo "Deploying ${SERVICE_NAME} to Cloud Run in ${REGION}"
echo "===================================================="

# Build and submit image via Cloud Build
gcloud builds submit --tag "${IMAGE_TAG}" .

# Deploy container to Cloud Run with Secret Manager mappings
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_TAG}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --port 8000 \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars ENV=production,PROJECT_NAME=AVENIQ,API_V1_STR=/api/v1 \
  --set-secrets SUPABASE_URL=SUPABASE_URL:latest,\
SUPABASE_PUBLISHABLE_KEY=SUPABASE_PUBLISHABLE_KEY:latest,\
SUPABASE_SECRET_KEY=SUPABASE_SECRET_KEY:latest,\
GEMINI_API_KEY=GEMINI_API_KEY:latest,\
RAZORPAY_KEY_ID=RAZORPAY_KEY_ID:latest,\
RAZORPAY_KEY_SECRET=RAZORPAY_KEY_SECRET:latest,\
RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET:latest

echo "[+] ${SERVICE_NAME} deployed successfully!"
