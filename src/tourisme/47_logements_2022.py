
import requests

URL = "https://api.insee.fr/melodi/data/DS_RP_LOGEMENT_PRINC"

tests = [
    {"GEO": "COM-26362", "TIME_PERIOD": "2022", "maxResult": 5},
    {"GEO": "COM-26362", "TIME_PERIOD": "2023", "maxResult": 5},
]

for params in tests:
    try:
        r = requests.get(URL, params=params, timeout=30)
        print("\nAnnée :", params["TIME_PERIOD"])
        print("URL :", r.url)
        print("HTTP :", r.status_code)
        print("Réponse :", r.text[:1500])
    except requests.RequestException as e:
        print("Erreur réseau :", e)
