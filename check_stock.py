"""ASOS voorraadmelder: controleert een product en stuurt een ntfy-pushmelding.

Omgevingsvariabelen:
  NTFY_TOPIC    verplicht: jouw geheime ntfy-topic (bv. asos-jan-x8k2q9)
  PRODUCT_ID    optioneel, standaard 210335519
  STORE         optioneel, standaard BE
  LOOP_SECONDS  optioneel: hoelang binnen één run blijven controleren (standaard 0 = één keer)
  INTERVAL      optioneel: seconden tussen controles (standaard 30)
  DEBUG         optioneel: "1" print het ruwe antwoord van ASOS (handig om te testen)
"""
import os
import sys
import time

import requests

PRODUCT_ID = os.environ.get("PRODUCT_ID", "210335519")
STORE = os.environ.get("STORE", "BE")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
LOOP_SECONDS = int(os.environ.get("LOOP_SECONDS", "0"))
INTERVAL = int(os.environ.get("INTERVAL", "30"))
DEBUG = os.environ.get("DEBUG") == "1"

PRODUCT_URL = f"https://www.asos.com/nl/prd/{PRODUCT_ID}"
API_URL = "https://www.asos.com/api/product/catalogue/v3/stockprice"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
}


def check_in_stock():
    """Geeft True/False, of None als de status niet bepaald kon worden."""
    params = {
        "productIds": PRODUCT_ID,
        "store": STORE,
        "currency": "EUR",
        "country": STORE,
    }
    r = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
    if DEBUG:
        print(r.status_code, r.text[:1500])
    if r.status_code != 200:
        print(f"Onverwachte statuscode {r.status_code} (mogelijk geblokkeerd)")
        return None
    data = r.json()
    if not isinstance(data, list) or not data:
        print("Leeg of onverwacht antwoord")
        return None
    variants = data[0].get("variants", [])
    if not variants:
        print("Geen varianten in antwoord")
        return None
    return any(v.get("isInStock") or v.get("isAvailable") for v in variants)


def notify(title, message, priority="urgent"):
    if not NTFY_TOPIC:
        print("NTFY_TOPIC ontbreekt, geen melding verstuurd")
        return
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": priority,
            "Click": PRODUCT_URL,
            "Tags": "gift,rotating_light",
        },
        timeout=20,
    )


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        notify("Test ASOS-melder", "De melding werkt!", priority="default")
        print("Testmelding verstuurd")
        return

    end = time.time() + LOOP_SECONDS
    while True:
        try:
            status = check_in_stock()
        except Exception as e:  # netwerkfout, JSON-fout, ...
            print("Fout bij controle:", e)
            status = None

        print(time.strftime("%H:%M:%S"), "in voorraad:", status)
        if status:
            notify("ASOS adventskalender BESCHIKBAAR", f"Snel bestellen: {PRODUCT_URL}")
            return
        if time.time() + INTERVAL >= end:
            return
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
