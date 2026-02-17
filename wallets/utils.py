import requests
import os
THIRD_PARTY_URL = os.environ.get("THIRD_PARTY_URL", "http://host.docker.internal:8010/")

def request_third_party_deposit(*, amount: int, idempotency_key: str, timeout: int = 5) -> dict:
    """
    Calls the third-party service.
    - Sends Idempotency-Key header
    - Sends JSON body: {"amount": amount}
    - Raises requests exceptions for network/timeout + non-2xx
    - Returns parsed JSON as dict
    """
    headers = {"Idempotency-Key": str(idempotency_key)}

    resp = requests.post(
        THIRD_PARTY_URL,
        headers=headers,
        json={"amount": amount},
        timeout=timeout,
    )

    # Raise for non-2xx HTTP responses
    resp.raise_for_status()

    # Parse JSON safely
    try:
        data = resp.json()
    except ValueError as exc:
        raise requests.exceptions.RequestException("Third-party returned non-JSON response") from exc

    return data
