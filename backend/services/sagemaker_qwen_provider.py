"""
AWS SageMaker Qwen Provider for Text Summarization
Based on llm_sagemaker.py pattern
"""
import os
import json
import logging
from typing import Dict, Any, Optional

import boto3

logger = logging.getLogger(__name__)


class SageMakerQwenProvider:
    """
    Client for AWS SageMaker Qwen endpoint.
    Used for text summarization (intention, conclusion, POV analysis).

    Based on llm_sagemaker.py pattern:
    - Uses boto3 SageMaker runtime client
    - Requires AWS credentials from environment
    - Chat completions format for prompt/response
    """

    def __init__(self, endpoint_name: Optional[str] = None):
        """
        Initialize SageMaker Qwen provider.

        Args:
            endpoint_name: SageMaker endpoint name (from config or environment)
                          If None, tries to read from QWEN_SAGEMAKER_ENDPOINT env var
        """
        logger.info("Initializing SageMaker Qwen Provider...")

        # Get endpoint name from argument or environment
        if endpoint_name is None:
            endpoint_name = os.getenv("QWEN_SAGEMAKER_ENDPOINT")

        # Endpoint name is optional - will be determined at runtime if not provided
        self.endpoint_name = endpoint_name

        if self.endpoint_name:
            logger.info(f"Using SageMaker endpoint: {self.endpoint_name}")
        else:
            logger.info("No SageMaker endpoint specified - will need to be provided at invocation time")

        # Initialize boto3 SageMaker client with AWS credentials
        try:
            aws_access_key = os.environ.get('QWENVL_AWS_ACCESS_KEY_ID')
            aws_secret_key = os.environ.get('QWENVL_AWS_SECRET_ACCESS_KEY')
            region = os.environ.get('AWS_DEFAULT_REGION', 'ap-southeast-1')

            # Log what we're getting (without exposing full credentials)
            logger.info(f"AWS credentials check:")
            if aws_access_key:
                logger.info(f"  QWENVL_AWS_ACCESS_KEY_ID: {aws_access_key[:4]}...{aws_access_key[-4:]} (length: {len(aws_access_key)})")
            else:
                logger.info(f"  QWENVL_AWS_ACCESS_KEY_ID: NOT SET")

            if aws_secret_key:
                logger.info(f"  QWENVL_AWS_SECRET_ACCESS_KEY: {aws_secret_key[:4]}...{aws_secret_key[-4:]} (length: {len(aws_secret_key)})")
            else:
                logger.info(f"  QWENVL_AWS_SECRET_ACCESS_KEY: NOT SET")

            logger.info(f"  AWS_DEFAULT_REGION: {region}")

            if not aws_access_key or not aws_secret_key:
                logger.error(
                    "❌ AWS credentials not found! Expected environment variables: "
                    "QWENVL_AWS_ACCESS_KEY_ID, QWENVL_AWS_SECRET_ACCESS_KEY"
                )
                raise ValueError("AWS credentials required for SageMaker access")

            session = boto3.Session(
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=region
            )
            self.runtime_client = session.client('sagemaker-runtime')

            logger.info(f"✅ SageMaker Qwen Provider initialized")
            logger.info(f"   Endpoint: {self.endpoint_name}")
            logger.info(f"   Region: {region}")

        except Exception as e:
            logger.error(f"Failed to initialize SageMaker client: {e}")
            raise

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.1,
        top_p: float = 0.8,
        top_k: int = 20,
        endpoint_name: Optional[str] = None,
    ) -> str:
        """
        Generate text using remote Qwen via AWS SageMaker.

        Args:
            prompt: Text prompt for generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            endpoint_name: Optional SageMaker endpoint name (overrides init value)

        Returns:
            Generated text
        """
        try:
            logger.info(f"Calling SageMaker Qwen for text generation...")

            # Use provided endpoint or fall back to initialized one
            target_endpoint = endpoint_name or self.endpoint_name
            if not target_endpoint:
                raise ValueError("SageMaker endpoint name not specified")

            # Build payload following llm_sagemaker.py pattern
            payload = {
                'messages': [{"role": "user", "content": prompt}],
                'temperature': temperature,
                'top_p': top_p,
                'top_k': top_k,
                'max_tokens': max_tokens,
                "chat_template_kwargs": {"enable_thinking": False},
            }

            # Invoke SageMaker endpoint
            response = self.runtime_client.invoke_endpoint(
                EndpointName=target_endpoint,
                ContentType="application/json",
                Body=json.dumps(payload)
            )

            # Parse response
            response_dict = json.loads(response['Body'].read().decode("utf-8"))
            generated_text = response_dict['choices'][0]['message']['content'].strip()

            logger.info(f"✅ Generation complete: {generated_text[:80]}...")
            return generated_text

        except Exception as e:
            logger.error(f"❌ SageMaker text generation failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return "[generation failed]"

    def summarize_intention(self, transcription: str) -> str:
        """
        Generate conversation intention using Qwen.

        Args:
            transcription: Full conversation text

        Returns:
            Intention summary
        """
        prompt = (
            f"Analyze this conversation:\n\n"
            f"Conversation:\n{transcription}\n\n"
            f"In 1-2 sentences, what is the main purpose/intention of this conversation?"
        )
        return self.generate_text(prompt, max_tokens=256, temperature=0.1)

    def summarize_conclusion(self, transcription: str) -> str:
        """
        Generate conversation conclusion using Qwen.

        Args:
            transcription: Full conversation text with speaker context

        Returns:
            Conclusion summary
        """
        prompt = (
            f"Analyze this conversation:\n\n"
            f"Conversation:\n{transcription}\n\n"
            f"In 2-3 sentences, what is the key conclusion or outcome, considering each speaker's perspective and emotional state?"
        )
        return self.generate_text(prompt, max_tokens=512, temperature=0.1)

    def summarize_speaker_pov(self, transcription: str, speaker_name: str) -> str:
        """
        Generate speaker's point of view using Qwen.

        Args:
            transcription: Full conversation text with speaker context
            speaker_name: Name of the speaker

        Returns:
            Speaker's POV summary
        """
        prompt = (
            f"Analyze this conversation:\n\n"
            f"Conversation:\n{transcription}\n\n"
            f"In 1-2 sentences, what is the point of view and main idea from {speaker_name}'s perspective?"
        )
        return self.generate_text(prompt, max_tokens=256, temperature=0.1)
