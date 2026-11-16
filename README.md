# CAFÉ — Analyse des données touristiques 2022

## Présentation

Ce projet vise à consolider et analyser les données touristiques de l'INSEE pour l'outil CAFÉ.

Les données sont organisées selon trois niveaux géographiques :
- **COM** : communes
- **DEP** : départements
- **REG** : régions

Deux catégories de tourisme sont étudiées : marchand et non marchand.

## Livrables 2022

### Tourisme marchand

Le tableau contient les nuitées des hôtels, campings et autres hébergements touristiques, avec les colonnes annuelles et mensuelles.

**[Télécharger le tableau marchand corrigé](data/processed/tourisme/livraison_cafe_2022/CAFE_TOURISME_2022_MARCHAND_CORRIGE.xlsx)**

Cette version intègre les données supplémentaires disponibles pour les campings et les autres hébergements.

### Tourisme non marchand

Le tableau contient les estimations de nuitées :
- Chez la famille et les amis
- Dans les résidences secondaires

Les estimations utilisent des données de population et de logements INSEE comme clés de répartition géographique.

**[Consulter le classeur initial](data/processed/tourisme/livraison_cafe_2022/CAFE_TOURISME_2022_DEUX_TABLEAUX.xlsx)**

## Sources et méthodologie

Les données proviennent principalement de l'INSEE.

- Fréquentation touristique : observations disponibles pour 2022
- Capacités d'hébergement : données communales
- Population : clé de répartition des séjours chez les proches
- Résidences secondaires : clé de répartition des nuitées correspondantes

Lorsque les nuitées ne sont pas directement disponibles à l'échelle communale, leur répartition est estimée à partir des capacités d'accueil ou d'autres indicateurs adaptés.

Les données observées et les estimations doivent être distinguées.

## État d'avancement

- Tableaux structurés aux niveaux COM, DEP et REG
- Données annuelles marchandes mises à jour
- Estimations non marchandes disponibles
- Certaines données mensuelles encore manquantes
- Vérifications de cohérence géographique et temporelle en cours

Les livrables restent provisoires jusqu'à validation finale.

## Dashboard Streamlit

Le projet comprend également un tableau de bord pour explorer les données touristiques.

Installation :

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Le dashboard utilise notamment :

- `data/processed/tourisme/livraison_cafe_2022/cafe_communes_2022.csv`
- `data/processed/tourisme/capacites_metro_2022.csv`
- `data/processed/tourisme/livraison_cafe_2022/campings_haute_saison_2022.csv` (facultatif)
- `data/processed/tourisme/livraison_cafe_2022/controles_nuitees_2022.csv` (facultatif)

Si les fichiers sont ailleurs, les chemins peuvent être modifiés dans la barre latérale.

## Prochaines étapes

1. Compléter les observations mensuelles disponibles.
2. Vérifier les correspondances et les totaux COM/DEP/REG.
3. Finaliser les contrôles de qualité.
4. Intégrer les données de population travaillant et étudiant sur le territoire.

## Statut

**Projet CAFÉ — Version de travail, novembre 2026.**
