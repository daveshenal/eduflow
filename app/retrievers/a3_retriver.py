import logging
import requests
from config.settings import settings

def retrieve_action_plan(ccn: str) -> str:
    url = f"{settings.A3_API_ENDPOINT}/{ccn}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logging.warning(f"A3 Retriver Failed: {e}")
        return None

    if not data:
        return None

    # Get latest record
    latest_record = sorted(data, key=lambda x: x['createdAt'], reverse=True)[0]

    # Build prompt
    prompt_parts = ["Consider following issues and solutions:"]
    for i, action_item in enumerate(latest_record['planData']['actionItems'], start=1):
        root_cause = action_item.get('rootCause', 'Root Cause not provided')
        action_description = action_item.get('actionDescription', 'Action Description not provided')
        if action_description == '':
            action_description = 'Not provided'
        prompt_parts.append(f"\nIssue {i}:\nRoot Cause: {root_cause}\nRecommended Action: {action_description}")

    return "\n".join(prompt_parts)