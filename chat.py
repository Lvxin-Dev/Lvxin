import httpx
import json
import os
from typing import List, Dict, Any

class ChatAPIError(Exception):
    """Custom exception for chat API errors."""
    pass

async def generate_message(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Generates a response from the legal advice AI.

    Args:
        messages: A list of message dictionaries, e.g., [{"role": "user", "content": "..."}].

    Returns:
        The parsed JSON response from the API.
    
    Raises:
        ChatAPIError: If the API call fails or returns an error.
    """
    access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
    access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    workspace_id = os.getenv("WORKSPACE_ID")

    if not all([access_key_id, access_key_secret, workspace_id]):
        raise ChatAPIError("Missing required environment variables for Alibaba Cloud.")

    url = f"https://bailian.aliyuncs.com/v2/workspaces/{workspace_id}/farui/legalAdvice/consult"

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {access_key_secret}",
    }

    payload = {
        "appId": "farui",
        "stream": False,
        "thread": {
            "messages": messages
        },
        "assistant": {
            "id": "assitant_abc_123",
            "type": "legal_advice_consult",
            "version": "1.0.0"
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                auth=(access_key_id, access_key_secret)
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise ChatAPIError(f"API request failed with status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise ChatAPIError(f"An unexpected error occurred during the API call: {e}") 