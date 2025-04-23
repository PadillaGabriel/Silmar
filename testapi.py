import requests, json
from datetime import datetime, timedelta

# Ajusta la ruta si hace falta
TOKEN_PATH = "app/ml_token.json"
CLIENT_ID = "5569606371936049"
CLIENT_SECRET = "wH7UDWXbA92DVlYa4P50cHBCLrEloMa0"

def get_valid_token():
    with open(TOKEN_PATH) as f:
        data = json.load(f)
    token = data["access_token"]
    exp   = int(data.get("expires_in",0))
    created = data.get("created_at")
    if created:
        from datetime import datetime, timedelta
        if datetime.now() > datetime.fromisoformat(created) + timedelta(seconds=exp-60):
            # renovar...
            payload = {
                "grant_type":"refresh_token",
                "client_id":CLIENT_ID,
                "client_secret":CLIENT_SECRET,
                "refresh_token":data["refresh_token"]
            }
            r = requests.post("https://api.mercadolibre.com/oauth/token", data=payload)
            r.raise_for_status()
            new = r.json()
            new["created_at"] = datetime.now().isoformat()
            with open(TOKEN_PATH,"w") as fw:
                json.dump(new, fw, indent=2)
            token = new["access_token"]
    return token

if __name__ == "__main__":
    item_id = input("Item ID (MLA...): ").strip()
    var_id  = input("Variation ID: ").strip()
    token   = get_valid_token()
    headers = {"Authorization": f"Bearer {token}"}
    url     = f"https://api.mercadolibre.com/items/{item_id}/variations/{var_id}"
    r = requests.get(url, headers=headers)
    print("Status:", r.status_code)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
