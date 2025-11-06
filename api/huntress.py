import base64
import requests
from typing import Dict, List

def get_agents(settings: Dict, page: int = 1, limit: int = 500) -> List[Dict]:
    """Get Huntress agents"""
    auth_string = f"{settings['HuntressAPIKey']}:{settings['huntressApiSecretKey']}"
    auth_bytes = auth_string.encode('utf-8')
    auth_encoded = base64.b64encode(auth_bytes).decode('utf-8')

    url = f"https://api.huntress.io/v1/agents?page={page}&limit={limit}"
    headers = {"Authorization": f"Basic {auth_encoded}"}
    
    response = requests.get(url, headers=headers)
    return response.json()["agents"]