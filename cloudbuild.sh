#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Starting Cloud Run Deployment ---"

# --- Configuration ---
# These MUST be set in your Cloud Build trigger configuration (substitutions/secrets)
# or environment variables in your CI/CD system. Avoid hardcoding sensitive values.

# Required:
PROJECT_ID="${PROJECT_ID:-school-kg}" # Your Google Cloud Project ID
SERVICE_NAME="sandbox-backend" # Your Cloud Run service name
REGION="${REGION:-us-central1}" # The region for your Cloud Run service

# Required from your .env (Set these in CI/CD):
API_KEY="${API_KEY}"
GEMINI_API_KEY="${GEMINI_API_KEY}"
SMTP_HOST="${SMTP_HOST}"
SMTP_PORT="${SMTP_PORT}"
SMTP_USERNAME="${SMTP_USERNAME}"
SMTP_PASSWORD="${SMTP_PASSWORD}" # Sensitive!
OPENAI_API_KEY="${OPENAI_API_KEY}" # Sensitive!
DB_USER="${DB_USER}"
DB_PASSWORD="${DB_PASSWORD}" # Sensitive!
DB_NAME="${DB_NAME}"


INSTANCE_CONNECTION_NAME="${INSTANCE_CONNECTION_NAME}" # Can have default
# GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS}" # See note above about usage in Cloud Run
GCS_BUCKET_NAME="sandbox-pdf_bucket"

# Optional: Specify service account for Cloud Run (Highly Recommended for production)
# SERVICE_ACCOUNT="your-service-account@${PROJECT_ID}.iam.gserviceaccount.com"

# Calculated:
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest" # Use Artifact Registry (e.g., REGION-docker.pkg.dev/...) for newer projects.

# --- Validate Configuration ---
echo "[INFO] Validating required environment variables..."
missing_vars=()
[ -z "$API_KEY" ] && missing_vars+=("API_KEY")
[ -z "$GEMINI_API_KEY" ] && missing_vars+=("GEMINI_API_KEY")
[ -z "$SMTP_HOST" ] && missing_vars+=("SMTP_HOST")
[ -z "$SMTP_PORT" ] && missing_vars+=("SMTP_PORT")
[ -z "$SMTP_USERNAME" ] && missing_vars+=("SMTP_USERNAME")
[ -z "$SMTP_PASSWORD" ] && missing_vars+=("SMTP_PASSWORD")
[ -z "$OPENAI_API_KEY" ] && missing_vars+=("OPENAI_API_KEY")
[ -z "$DB_USER" ] && missing_vars+=("DB_USER")
[ -z "$DB_PASSWORD" ] && missing_vars+=("DB_PASSWORD")
[ -z "$DB_NAME" ] && missing_vars+=("DB_NAME")
[ -z "$INSTANCE_CONNECTION_NAME" ] && missing_vars+=("INSTANCE_CONNECTION_NAME")
# [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ] && missing_vars+=("GOOGLE_APPLICATION_CREDENTIALS") # Optional depending on usage
[ -z "$GCS_BUCKET_NAME" ] && missing_vars+=("GCS_BUCKET_NAME")

if [ ${#missing_vars[@]} -ne 0 ]; then
  echo "[ERROR] The following required environment variables are not set: ${missing_vars[*]}"
  exit 1
fi
echo "[INFO] All required environment variables appear to be set."

# --- Log Configuration (excluding sensitive values) ---
echo "[INFO] Project ID: ${PROJECT_ID}"
echo "[INFO] Service Name: ${SERVICE_NAME}"
echo "[INFO] Region: ${REGION}"
echo "[INFO] Image Name: ${IMAGE_NAME}"
echo "[INFO] Instance Connection Name: ${INSTANCE_CONNECTION_NAME}"
echo "[INFO] DB User: ${DB_USER}"
echo "[INFO] DB Name: ${DB_NAME}"
echo "[INFO] GCS Bucket Name: ${GCS_BUCKET_NAME}"
echo "[INFO] SMTP Host: ${SMTP_HOST}"
echo "[INFO] SMTP Port: ${SMTP_PORT}"
echo "[INFO] SMTP Username: ${SMTP_USERNAME}"
echo "[INFO] Sensitive Keys (API_KEY, GEMINI_API_KEY, SMTP_PASSWORD, OPENAI_API_KEY, DB_PASSWORD): [SET]"
# echo "[INFO] Google App Credentials Path: ${GOOGLE_APPLICATION_CREDENTIALS:-[NOT SET]}" # Uncomment if needed

# --- Build Step ---
echo "[INFO] Building Docker image: ${IMAGE_NAME}"
docker build -t "${IMAGE_NAME}" .
echo "[INFO] Docker image built successfully."

# --- Push Step ---
# Ensure docker is authenticated to push (gcloud auth configure-docker)
echo "[INFO] Pushing Docker image to Google Container Registry: ${IMAGE_NAME}"
docker push "${IMAGE_NAME}"
echo "[INFO] Docker image pushed successfully."

# --- Deploy Step ---
echo "[INFO] Deploying service '${SERVICE_NAME}' to Cloud Run in region '${REGION}'..."

# Construct environment variables string
# Start with potentially non-existent ones to avoid leading comma issues if they are empty
ENV_VARS=""
[ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && ENV_VARS="GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS}"

# Append other variables, adding comma prefix if ENV_VARS is not empty
[ -n "$ENV_VARS" ] && ENV_VARS+="," || : ; ENV_VARS+="API_KEY=${API_KEY}"
ENV_VARS+=",GEMINI_API_KEY=${GEMINI_API_KEY}"
ENV_VARS+=",SMTP_HOST=${SMTP_HOST}"
ENV_VARS+=",SMTP_PORT=${SMTP_PORT}"
ENV_VARS+=",SMTP_USERNAME=${SMTP_USERNAME}"
ENV_VARS+=",SMTP_PASSWORD=${SMTP_PASSWORD}"
ENV_VARS+=",OPENAI_API_KEY=${OPENAI_API_KEY}"
ENV_VARS+=",DB_USER=${DB_USER}"
ENV_VARS+=",DB_PASSWORD=${DB_PASSWORD}"
ENV_VARS+=",DB_NAME=${DB_NAME}"
ENV_VARS+=",INSTANCE_CONNECTION_NAME=${INSTANCE_CONNECTION_NAME}"
ENV_VARS+=",GCS_BUCKET_NAME=${GCS_BUCKET_NAME}"
# Add any other variables here:
# ENV_VARS+=",ANOTHER_VAR=value"

# Base deploy command
DEPLOY_CMD=(gcloud run deploy "${SERVICE_NAME}"
  --image "${IMAGE_NAME}"
  --platform managed
  --region "${REGION}"
  --project "${PROJECT_ID}"
  # --- Connectivity ---
  --add-cloudsql-instances "${INSTANCE_CONNECTION_NAME}"
  # --- Environment Variables ---
  --set-env-vars "${ENV_VARS}" # Pass all env vars defined above
  # --- Access Control ---
  # Choose one:
  --allow-unauthenticated # For public access
)

# Optional: Add service account if defined and uncommented
# if [ -n "$SERVICE_ACCOUNT" ]; then
#  DEPLOY_CMD+=(--service-account "${SERVICE_ACCOUNT}")
# fi

# Execute the deployment command
echo "[COMMAND] gcloud run deploy ${SERVICE_NAME} --image ... --set-env-vars [VARIABLES HIDDEN] ..." # Log command without showing vars
"${DEPLOY_CMD[@]}"

echo "[INFO] Deployment of '${SERVICE_NAME}' initiated successfully."
echo "--- Cloud Build Finished ---"