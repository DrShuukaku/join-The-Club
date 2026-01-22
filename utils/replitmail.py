import os
import subprocess
import requests
from typing import List, Optional, Dict, Any

def get_auth_token() -> Dict[str, str]:
    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME")
    if not hostname:
        raise Exception("REPLIT_CONNECTORS_HOSTNAME not found")
    
    result = subprocess.run(
        ["replit", "identity", "create", "--audience", f"https://{hostname}"],
        capture_output=True,
        text=True,
        check=True
    )
    
    replit_token = result.stdout.strip()
    if not replit_token:
        raise Exception("Replit Identity Token not found")
        
    return {"authToken": f"Bearer {replit_token}", "hostname": hostname}

def send_email(subject: str, text: Optional[str] = None, html: Optional[str] = None, attachments: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    auth = get_auth_token()
    hostname = auth["hostname"]
    auth_token = auth["authToken"]
    
    payload = {
        "subject": subject,
        "text": text,
        "html": html,
        "attachments": attachments
    }
    
    response = requests.post(
        f"https://{hostname}/api/v2/mailer/send",
        headers={
            "Content-Type": "application/json",
            "Replit-Authentication": auth_token,
        },
        json=payload
    )
    
    if not response.ok:
        try:
            error_data = response.json()
            message = error_data.get("message", "Failed to send email")
        except:
            message = response.text
        raise Exception(message)
        
    return response.json()
