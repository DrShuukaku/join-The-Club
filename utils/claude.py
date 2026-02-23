import os
from anthropic import Anthropic

def get_claude_client():
    """
    Returns an Anthropic client configured with Replit AI Integrations.
    """
    api_key = os.environ.get("AI_Integrations_Anthropic_API_Key")
    base_url = os.environ.get("AI_Integrations_Anthropic_Base_Url")
    
    if not api_key:
        raise ValueError("Anthropic API Key not found in environment. Please ensure the integration is properly set up.")
        
    return Anthropic(
        api_key=api_key,
        base_url=base_url
    )

def ask_claude(prompt, model="claude-3-5-sonnet-20240620", max_tokens=1024):
    """
    Simple wrapper to send a message to Claude and get a response.
    """
    client = get_claude_client()
    
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.content[0].text
