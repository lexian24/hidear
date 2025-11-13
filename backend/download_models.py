#!/usr/bin/env python3
"""
Download and cache HuggingFace models for offline use.

This script should be run once after deploying the application to the server.
It downloads all required models to the HuggingFace cache directory, so they
don't need to be downloaded at runtime.

Usage:
    # Run in the backend container
    podman run --rm -it \
      -e HF_HOME=/app/models \
      -e HF_TOKEN=$HF_TOKEN \
      -v hidear_celery_models:/app/models \
      hidear-celery-worker python download_models.py

Or locally for testing:
    python backend/download_models.py
"""

import os
import logging
from pathlib import Path
from typing import Optional

# Patch torchaudio compatibility issue with pyannote
# Newer torchaudio removed list_audio_backends() which pyannote still tries to use
try:
    import torchaudio
    if not hasattr(torchaudio, 'list_audio_backends'):
        # Provide a stub function that returns empty list
        torchaudio.list_audio_backends = lambda: []
        logging.info("Patched torchaudio.list_audio_backends() for compatibility")
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_pyannote_models(hf_token: Optional[str] = None) -> bool:
    """
    Download pyannote.audio speaker diarization models using git-lfs.

    This downloads the community version for offline use, which doesn't require
    accepting gated model agreements.

    Args:
        hf_token: HuggingFace API token (from HF_TOKEN env var)

    Returns:
        True if successful, False otherwise
    """
    import subprocess

    try:
        # Check if git-lfs is installed
        try:
            subprocess.run(["git", "lfs", "version"], capture_output=True, check=True)
            logger.info("✅ git-lfs is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error(f"❌ git-lfs is not installed")
            logger.error(f"   Please install git-lfs from https://git-lfs.com")
            logger.error(f"   Then run: git lfs install")
            return False

        logger.info("=" * 60)
        logger.info("Downloading pyannote speaker diarization models...")
        logger.info("=" * 60)

        # Get token from environment or parameter
        token = hf_token or os.getenv("HF_TOKEN")

        if not token:
            logger.warning(f"⚠️  HF_TOKEN not provided")
            logger.warning(f"   The community model is gated and requires authentication")
            logger.warning(f"   Please set HF_TOKEN environment variable with your HuggingFace access token")
            logger.warning(f"   Get a token from: https://huggingface.co/settings/tokens")
            logger.warning(f"   Then run: export HF_TOKEN=your_token_here")
            logger.warning(f"   And try again: python backend/download_models.py")
            return False

        # Use community version for offline use
        model_id = "pyannote/speaker-diarization-community-1"
        model_path = Path(os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))) / "hub" / "models--pyannote--speaker-diarization-community-1"

        logger.info(f"📥 Downloading {model_id}...")
        logger.info(f"   Destination: {model_path}")
        logger.info(f"   Using HuggingFace token for authentication...")

        # Create parent directory if it doesn't exist
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # Clone the model using git lfs with token authentication
        try:
            # Use token in URL to authenticate with HuggingFace
            # This avoids interactive password prompts
            clone_url = f"https://{token}@hf.co/{model_id}"

            cmd = ["git", "clone", clone_url, str(model_path)]

            logger.info(f"   Running: git clone https://<token>@hf.co/{model_id} {model_path}")
            logger.info(f"   This may take 5-15 minutes (model is ~1GB with git-lfs)...")
            logger.info(f"")

            # Set environment to avoid interactive prompts
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"  # Disable password/passphrase prompt

            result = subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
            logger.info(f"✅ Successfully downloaded {model_id}")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to download {model_id}")
            logger.error(f"   git clone failed with exit code: {e.returncode}")
            if e.stderr:
                stderr_output = e.stderr.strip()
                logger.error(f"   Error: {stderr_output}")
            logger.error(f"")
            logger.error(f"   Troubleshooting:")
            logger.error(f"   1. Check git-lfs is installed: git lfs --version")
            logger.error(f"   2. Verify HF_TOKEN is valid and has 'repo' read permissions")
            logger.error(f"      Token: https://huggingface.co/settings/tokens")
            logger.error(f"   3. Verify you accepted the model access agreement:")
            logger.error(f"      https://huggingface.co/pyannote/speaker-diarization-community-1")
            logger.error(f"   4. Check internet connectivity: curl -I https://hf.co")
            logger.error(f"")
            logger.error(f"   If token is invalid, generate a new one:")
            logger.error(f"   - Visit: https://huggingface.co/settings/tokens")
            logger.error(f"   - Create 'New token' with 'repo' read permissions")
            logger.error(f"   - Run: export HF_TOKEN=your_new_token")
            logger.error(f"   - Try again: python backend/download_models.py")
            return False

        # Verify by loading the pipeline
        logger.info(f"✅ Verifying pipeline can load from disk...")
        try:
            from pyannote.audio import Pipeline
            pipeline = Pipeline.from_pretrained(str(model_path))
            logger.info(f"✅ Pipeline verification successful")

            # Move to GPU if available for validation
            try:
                import torch
                if torch.cuda.is_available():
                    pipeline = pipeline.to(torch.device("cuda"))
                    logger.info("✅ Model moved to GPU successfully")
            except Exception as e:
                logger.info(f"ℹ️  Could not move to GPU: {e} (OK for CPU-only systems)")
        except Exception as e:
            logger.error(f"❌ Failed to verify pipeline: {e}")
            return False

        return True

    except ImportError as e:
        logger.error(f"❌ pyannote.audio not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


def download_transformers_models(hf_token: Optional[str] = None) -> bool:
    """
    Download any transformers models needed by the application.

    Args:
        hf_token: HuggingFace API token

    Returns:
        True if successful, False otherwise
    """
    try:
        from transformers import AutoTokenizer

        logger.info("=" * 60)
        logger.info("Downloading transformers models...")
        logger.info("=" * 60)

        # Get token from environment or parameter
        token = hf_token or os.getenv("HF_TOKEN")

        # Add any specific transformer models you use here
        # Example:
        # models = ["microsoft/phi-2", "openai/whisper-base", ...]

        logger.info("ℹ️  No specific transformer models configured for download")
        logger.info("   (Add model IDs to this script if needed)")

        return True

    except ImportError:
        logger.info("ℹ️  transformers not installed (OK, may not be needed)")
        return True
    except Exception as e:
        logger.error(f"❌ Error downloading transformer models: {e}")
        return False


def verify_cache() -> bool:
    """
    Verify that models are cached.

    Returns:
        True if cache directory exists and has content
    """
    try:
        hf_home = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
        cache_dir = Path(hf_home) / "hub"

        logger.info("=" * 60)
        logger.info("Cache Status")
        logger.info("=" * 60)
        logger.info(f"HF_HOME: {hf_home}")
        logger.info(f"Cache directory: {cache_dir}")

        if cache_dir.exists():
            cached_files = list(cache_dir.glob("**/*"))
            logger.info(f"✅ Cache directory exists with {len(cached_files)} items")

            # List some cached models
            if cached_files:
                logger.info("\nCached model directories:")
                models_dir = cache_dir / "models--pyannote--speaker-diarization-3.1"
                if models_dir.exists():
                    logger.info(f"  ✅ pyannote/speaker-diarization-3.1")

                models_dir = cache_dir / "models--pyannote--speaker-diarization"
                if models_dir.exists():
                    logger.info(f"  ✅ pyannote/speaker-diarization")
        else:
            logger.warning(f"⚠️  Cache directory does not exist: {cache_dir}")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ Error verifying cache: {e}")
        return False


def main():
    """Main entry point."""
    logger.info("\n" + "=" * 60)
    logger.info("HuggingFace Model Download Utility")
    logger.info("=" * 60 + "\n")

    # Get token from environment
    hf_token = os.getenv("HF_TOKEN")
    if hf_token:
        logger.info(f"✅ HF_TOKEN found in environment")
    else:
        logger.warning("⚠️  HF_TOKEN not found in environment")
        logger.info("   Public models will be downloaded without authentication")

    # Download models
    success = True
    success = download_pyannote_models(hf_token) and success
    success = download_transformers_models(hf_token) and success

    # Verify cache
    verify_cache()

    logger.info("\n" + "=" * 60)
    if success:
        logger.info("✅ All models downloaded successfully!")
        logger.info("=" * 60 + "\n")
        return 0
    else:
        logger.error("❌ Some models failed to download")
        logger.info("=" * 60 + "\n")
        return 1


if __name__ == "__main__":
    exit(main())
