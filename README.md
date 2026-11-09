# CAFÉ · Dashboard Tourisme 2022

Copier `app.py` à la racine du projet `cafe`, à côté des scripts Python. Installer :

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Le tableau de bord lit :
- `data/processed/tourisme/livraison_cafe_2022/cafe_communes_2022.csv`
- `data/processed/tourisme/capacites_metro_2022.csv`
- `data/processed/tourisme/livraison_cafe_2022/campings_haute_saison_2022.csv` (facultatif)
- `data/processed/tourisme/livraison_cafe_2022/controles_nuitees_2022.csv` (facultatif)

Si les fichiers sont ailleurs, modifier le chemin dans la barre latérale.
