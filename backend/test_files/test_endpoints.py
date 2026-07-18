import os
import sys
from pathlib import Path

# Add project root to Python path for imports (MUST be before other imports)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from openai import AzureOpenAI
from core.logger import setup_logger, info, error

# ==========================
# Configuration (use environment variables for security)
# ==========================
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# ==========================
# Setup Logger
# ==========================
logger = setup_logger(
    name="azure_openai_test",
    log_level="INFO",
    log_dir="logs",
    json_logs=False,
)

# ==========================
# Create Client
# ==========================
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
)

def test_connection():
    """Test Azure OpenAI connection."""
    try:
        info(logger, "Testing Azure OpenAI connection...")
        info(logger, f"Endpoint: {AZURE_OPENAI_ENDPOINT}")
        info(logger, f"Deployment: {AZURE_OPENAI_DEPLOYMENT}")
        
        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {
                    "role": "user",
                    "content": "Reply with only: Azure OpenAI connection successful."
                }
            ],
            temperature=0,
            max_tokens=20,
        )

        print("=" * 60)
        print("✅ Connection Successful!")
        print("=" * 60)
        print(response.choices[0].message.content)
        info(logger, "Azure OpenAI connection test passed")
        return True

    except Exception as e:
        print("=" * 60)
        print("❌ Connection Failed")
        print("=" * 60)
        print(type(e).__name__)
        print(e)
        error(logger, f"Azure OpenAI connection test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)