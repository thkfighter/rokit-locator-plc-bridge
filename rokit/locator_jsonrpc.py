import requests


def clientLocalizationSetSeed(url, id, sessionId: str, x: float, y: float, a: float, enforceSeed: bool = False, uncertainSeed: bool = False):
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }

    payload = {
        "id": id,
        "jsonrpc": "2.0",
        "method": "clientLocalizationSetSeed",
        "params": {
            "query": {
                "sessionId": sessionId,
                "enforceSeed": enforceSeed,
                "uncertainSeed": uncertainSeed,
                "seedPose": {
                    "x": x,
                    "y": y,
                    "a": a
                }
            }
        }
    }

    print(f"x={x}, y={y}, a={a}")
    response = requests.post(url=url, json=payload, headers=headers)
    # print(response.json())


def sessionLogin(url, id, user_name, password) -> str:
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }
    payload = {
        "id": id,
        "jsonrpc": "2.0",
        "method": "sessionLogin",
        "params": {
            "query": {
                "timeout": { # timeout, not timestamp
                    "valid": True,
                    "time": 60, # Integer64
                    "resolution": 1 # real_time = time / resolution
                },
                "userName": user_name,
                "password": password
            }
        }
    }
    # print(payload)

    response = requests.post(url=url, json=payload, headers=headers)
    # print(response.json())
    sessionId = response.json()['result']['response']['sessionId']

    return sessionId


def sessionLogout(url, id, sessionId: str = None):
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
    }

    payload = {
        "id": id,
        "jsonrpc": "2.0",
        "method": "sessionLogout",
        "params": {
            "query": {
                "sessionId": sessionId
            }
        }
    }

    response = requests.post(url=url, json=payload, headers=headers)
    # print(response.json())