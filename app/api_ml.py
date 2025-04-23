# app/api_ml.py
import requests, json
from datetime import datetime, timedelta

TOKEN_PATH    = "app/ml_token.json"
CLIENT_ID     = "5569606371936049"
CLIENT_SECRET = "wH7UDWXbA92DVlYa4P50cHBCLrEloMa0"
DEFAULT_IMG   = "https://via.placeholder.com/150"

def get_valid_token():
    with open(TOKEN_PATH) as f:
        data = json.load(f)
    expires_in   = int(data.get("expires_in", 0))
    created_at   = data.get("created_at")
    access_token = data.get("access_token")
    if not created_at:
        return access_token
    created_dt = datetime.fromisoformat(created_at)
    if datetime.now() > created_dt + timedelta(seconds=expires_in - 60):
        payload = {
            "grant_type":    "refresh_token",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": data["refresh_token"]
        }
        r = requests.post("https://api.mercadolibre.com/oauth/token", data=payload)
        if r.status_code == 200:
            new = r.json()
            new["created_at"] = datetime.now().isoformat()
            with open(TOKEN_PATH, "w") as wf:
                json.dump(new, wf, indent=2)
            return new["access_token"]
        return None
    return access_token

def fetch_variation_images(item_id, variation_id, headers):
    """
    Trae las picture_ids de la variante y construye sus URLs.
    """
    url = f"https://api.mercadolibre.com/items/{item_id}/variations/{variation_id}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        pic_ids = data.get("picture_ids", [])
        pics = []
        for pid in pic_ids:
            # thumbnail = “-I.jpg”, full = “-O.jpg”
            pics.append({
                "url":       f"https://http2.mlstatic.com/D_{pid}-O.jpg",
                "thumbnail": f"https://http2.mlstatic.com/D_{pid}-I.jpg"
            })
        return pics
    return []



def fetch_item_images(item_id, headers):
    """
    Si NO hay variant_id, llama a /items/{item_id} y devuelve sus fotos principales.
    """
    url = f"https://api.mercadolibre.com/items/{item_id}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        pics = r.json().get("pictures", [])
        return [
            {"url": pic.get("url"), "thumbnail": pic.get("secure_url")}
            for pic in pics
        ]
    return []


def parse_order_data(order_data: dict, headers: dict):
    salida = []
    for oi in order_data.get("order_items", []):
        prod = oi["item"]
        item_id = prod["id"]
        variation_id = prod.get("variation_id")  # puede ser None

        # 1) Nombre de variante
        attrs = prod.get("variation_attributes", [])
        variante_text = attrs[0]["value_name"] if attrs else "—"

        # 2) Imágenes: variante o item
        if variation_id:
            imgs = fetch_variation_images(item_id, variation_id, headers)
        else:
            imgs = fetch_item_images(item_id, headers)
        if not imgs:
            imgs = [{"url": DEFAULT_IMG, "thumbnail": DEFAULT_IMG}]

        # 3) SKU real
        sku = prod.get("seller_sku") or prod.get("seller_custom_field") or "Sin SKU"

        salida.append({
            "titulo":   prod.get("title", "Sin título"),
            "sku":      sku,
            "imagenes": imgs,
            "variante": variante_text,
            "cantidad": oi.get("quantity", 0)
        })

    # El return debe quedar fuera del for
    return {
        "cliente": order_data.get("buyer", {}).get("nickname", "Sin nombre"),
        "items":   salida
    }
        

def get_order_details(order_id: str):
    token = get_valid_token()
    if not token:
        return {"cliente":"Error","items":[]}
    headers = {"Authorization": f"Bearer {token}"}

    # 1) /orders/{order_id}
    r1 = requests.get(f"https://api.mercadolibre.com/orders/{order_id}", headers=headers)
    if r1.status_code == 200:
        return parse_order_data(r1.json(), headers)

    # 2) /shipments/{order_id}
    r2 = requests.get(f"https://api.mercadolibre.com/shipments/{order_id}", headers=headers)
    if r2.status_code == 200:
        real_id = r2.json().get("order_id")
        if real_id:
            r3 = requests.get(f"https://api.mercadolibre.com/orders/{real_id}", headers=headers)
            if r3.status_code == 200:
                return parse_order_data(r3.json(), headers)

    # 3) /packs/{order_id}
    r4 = requests.get(f"https://api.mercadolibre.com/packs/{order_id}", headers=headers)
    if r4.status_code == 200:
        all_items = []
        for o in r4.json().get("orders", []):
            rp = requests.get(f"https://api.mercadolibre.com/orders/{o['id']}", headers=headers)
            if rp.status_code == 200:
                all_items += parse_order_data(rp.json(), headers)["items"]
        return {"cliente":"Pedido pack","items":all_items}

    # si llegamos aquí, no hubo éxito
    return {"cliente":"Error","items":[]}
