# Deploy AVENIQ Backend to Google Cloud Run (PowerShell)

$ErrorActionPreference = "Stop"

$PROJECT_ID = if ($env:GCP_PROJECT_ID) { $env:GCP_PROJECT_ID } else { "aveniq-prod" }
$REGION = if ($env:GCP_REGION) { $env:GCP_REGION } else { "us-central1" }
$SERVICE_NAME = "aveniq-backend"
$IMAGE_TAG = "gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "Deploying ${SERVICE_NAME} to Cloud Run in ${REGION}" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# Submit image build
gcloud builds submit --tag "${IMAGE_TAG}" .

# Deploy container to Cloud Run
gcloud run deploy "${SERVICE_NAME}" `
  --image "${IMAGE_TAG}" `
  --platform managed `
  --region "${REGION}" `
  --allow-unauthenticated `
  --port 8000 `
  --cpu 1 `
  --memory 512Mi `
  --min-instances 1 `
  --max-instances 10 `
  --set-env-vars "ENV=production,PROJECT_NAME=AVENIQ,API_V1_STR=/api/v1" `
  --set-secrets "SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_PUBLISHABLE_KEY=SUPABASE_PUBLISHABLE_KEY:latest,SUPABASE_SECRET_KEY=SUPABASE_SECRET_KEY:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,RAZORPAY_KEY_ID=RAZORPAY_KEY_ID:latest,RAZORPAY_KEY_SECRET=RAZORPAY_KEY_SECRET:latest,RAZORPAY_WEBHOOK_SECRET=RAZORPAY_WEBHOOK_SECRET:latest"

Write-Host "[+] ${SERVICE_NAME} deployed successfully to Cloud Run!" -ForegroundColor Green
