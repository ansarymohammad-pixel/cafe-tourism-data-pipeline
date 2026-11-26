CAFÉ — Pipeline de données touristiques INSEE (2022–2025)
Pipeline Python pour préparer, répartir et consolider des données touristiques françaises, aux trois niveaux commune (COM), département (DEP) et région (REG).
Statut — novembre 2026 : pipeline fonctionnel sur 2022–2025 ; sorties marchandes estimées, avec des lacunes de couverture pour certains campings ; sorties non marchandes exploratoires, et non des statistiques de destination métropolitaine validées.

1. Résultats livrés
Pour chaque année 2022, 2023, 2024 et 2025, le script d'assemblage produit :
data/final/tourisme/
├── CAFE_TOURISME_2022.xlsx
├── CAFE_TOURISME_2023.xlsx
├── CAFE_TOURISME_2024.xlsx
├── CAFE_TOURISME_2025.xlsx
├── 2022/
│   ├── CAFE_TOURISME_2022_MARCHAND_V2.csv
│   └── CAFE_TOURISME_2022_NON_MARCHAND_V2.csv
└── ... (même structure pour 2023–2025)
Chaque classeur Excel contient exactement deux onglets :
- MARCHAND : hôtels, campings, autres hébergements, annuels et mensuels ;
- NON_MARCHAND : famille/amis et résidences secondaires, scénario exploratoire annuel et mensuel.
Les CSV conservent les colonnes geocode et admin_level et utilisent les codes géographiques comme identifiants textuels (ex. 01001, 2A...). Les fichiers bruts et intermédiaires sont conservés à part.
2. Organisation des fichiers
cafe/
├── src/
│   └── tourisme/
│       ├── run_all.py                         # orchestration
│       ├── 54_assembler_cafe_2022_2025.py    # CSV et Excel finaux
│       ├── download/
│       │   ├── 09_tourisme_extraction.py
│       │   ├── 10_recuperer_capacites_historiques.py
│       │   └── 13_nuitees_2022_2025.py
│       ├── distribution_com/
│       │   ├── 18_capacites_communales.py
│       │   ├── 20_estimation_nuitees_communales.py
│       │   ├── 46_nonmarche.py
│       │   ├── 47_logements_2022.py
│       │   ├── 49_integration_non_marchand.py
│       │   ├── 50_non_marchand_com_dep_reg.py
│       │   ├── 51_tourisme_marchand_2022.py
│       │   ├── 52_scenario_non_marchand_2022_2025.py
│       │   └── 53_ventilation_mensuelle_2022.py
│       └── analysis/                         # diagnostics et analyses
├── data/
│   ├── raw/tourisme/                         # sources INSEE non versionnées
│   ├── processed/tourisme/{année}/           # résultats intermédiaires
│   └── final/tourisme/                       # livrables finaux
└── README.md
Les anciennes copies de scripts ont été déplacées dans une archive locale ; les traitements actifs sont dans les répertoires ci-dessus. Ne pas confondre les dossiers data/ à la racine avec d'anciens src/data/.
3. Mise en route — Windows / PowerShell
Depuis le dossier racine cafe, avec un environnement virtuel Python déjà créé :
.\.venv\Scripts\Activate.ps1
python -m pip install pandas numpy XlsxWriter
Les grandes données sources (ex. frequentation_brut.csv, tourisme_national_brut.csv) doivent déjà se trouver dans data/raw/tourisme/. Elles ne sont pas automatiquement téléchargées par run_all.py.

Pour reprendre uniquement la finalisation, lorsque les résultats intermédiaires sont déjà présents :
python src\tourisme\run_all.py --finalize
Pour exécuter tout le pipeline :
python src\tourisme\run_all.py
Pour contrôler la présence des sorties sans les recalculer :
python src\tourisme\run_all.py --verify-only
Pour afficher toutes les étapes lors de la finalisation (version récente de l'orchestrateur) :
python src\tourisme\run_all.py --finalize --verbose
Ces options --finalize et --verbose nécessitent la version mise à jour de run_all.py ; l'ancienne version du dépôt peut ne pas les proposer. Vérifier avec python src\tourisme\run_all.py --help.

Pour ouvrir directement les livrables :
explorer data\final\tourisme
4. Chaîne de traitement
Sources INSEE — DS_TOUR_FREQ / DS_TOUR_CAP / DS_SUIVI_DDE_TOUR
    |
    +--> 09 : extraction (si nécessaire, opération distincte)
    |
    +--> 13 : nuitées observées par zone et type d'hébergement
    +--> 18 : capacités communales
    |      |
    |      +--> 20 : estimation des nuitées communales
    |                  |
    |                  +--> 51 : consolidation COM / DEP / REG
    |                              |
    |                              +--> 53 : profils mensuels marchands
    |
    +--> 46 : nuitées nationales non marchandes (toutes destinations)
           |
           +--> 47 : logements (RP2023 comme proxy si nécessaire)
           +--> 49 : poids population / logements
                      |
                      +--> 50 : clés COM / DEP / REG
                                 |
                                 +--> 52 : scénario non marchand
                                            |
                                            +--> 54 : 4 Excel + 8 CSV finaux
Tourisme marchand
Les nuitées observées à une maille géographique supérieure sont estimées au niveau communal grâce aux capacités d'hébergement. Les communes sont ensuite additionnées pour former les départements et régions.
- Hôtels : totaux annuels et profils mensuels INSEE départementaux.
- Autres hébergements : totaux annuels et profils mensuels INSEE régionaux.
- Campings : source couvrant la haute saison (avril–septembre), profil mensuel régional. La colonne historique camping_nights_year correspond en réalité au total de haute saison, pas à un total annuel complet.
Les mois hors période camping peuvent être exportés comme zéros d'allocation dans le tableur : ce ne sont pas des zéros observés. Certains totaux de camping restent inconnus, et les cases correspondantes doivent rester manquantes.
Tourisme non marchand : scénario B
Le script 46 extrait les nuitées annuelles « famille/amis » et « résidences secondaires » du jeu INSEE DS_SUIVI_DDE_TOUR, avec TRAVEL_DEST=_T : toutes destinations.

La solution B applique à chacune des deux catégories le rapport, pour chaque année :
coefficient = (nuitées France + outre-mer, tous hébergements)
              / (nuitées toutes destinations, tous hébergements)
Les totaux ajustés sont ensuite répartis entre communes, selon :
- population municipale pour famille/amis ;
- résidences secondaires + logements occasionnels pour la seconde catégorie.
Les données communales de population et de logements 2023 sont utilisées comme proxy pour les années sans mesure annuelle exploitable. Les départements et régions sont obtenus par addition des communes. Les nuitées non marchandes mensuelles sont réparties uniformément sur 12 mois (1/12).

Limites impératives :
1. France + outre-mer n'est pas France métropolitaine seule ;
2. le coefficient global tous hébergements est appliqué aux catégories non marchandes par hypothèse ;
3. la mensualisation 1/12 est une convention non observée ;
4. ces totaux proviennent de l'enquête auprès des résidents métropolitains et ne mesurent pas toutes les nuitées non marchandes réalisées en métropole ;
5. les logements RP2023 utilisés pour d'autres années sont des proxies, pas des observations de ces années.
Les tableaux non marchands finaux sont donc des scénarios exploratoires non validés, pas des statistiques officielles de nuitées dans chaque commune.
5. Contrôles intégrés
Les scripts de calcul conservent les contrôles essentiels. Leurs résultats ne nécessitent pas un second programme de test :
- Conservation géographique : somme COM = somme DEP = somme REG, à périmètre équivalent ;
- Conservation mensuelle : somme des 12 mois = total annuel pour les séries annuelles complètes ;
- Camping : somme avril–septembre = total de la haute saison, lorsque le total est disponible ;
- Scénario B : somme des communes = total corrigé par le coefficient annuel.
Ces contrôles garantissent la cohérence arithmétique, pas la validité des hypothèses, ni une couverture statistique exhaustive.
Couverture camping constatée
Année	Communes avec nuitées camping	Communes sans total camping
2022	34 727	144
2023	34 616	245
2024	34 042	764
2025	33 982	760


Les lignes manquantes ne doivent pas être transformées artificiellement en nuitées observées égales à zéro.
6. Sources principales
- INSEE — site officiel
- INSEE — enquête de suivi de la demande touristique (SDT)
- Jeux extraits du pipeline : DS_TOUR_FREQ, DS_TOUR_CAP, DS_SUIVI_DDE_TOUR.
- Références de logements : recensement INSEE, DS_RP_LOGEMENT_PRINC (RP2023) et éventuelles bases historiques.
7. Git et suivi du projet
Les fichiers de données brutes et les livrables massifs ne doivent pas être ajoutés automatiquement à Git. Privilégier les scripts, la documentation et les fichiers de configuration.
git status
git add README.md
git commit -m "docs: update CAFE tourism pipeline README 2022-2025"
git push origin <nom-de-ta-branche>
Remplacer <nom-de-ta-branche> par la branche affichée via git branch --show-current. Fusionner ensuite dans main via Pull Request, puis synchroniser la branche locale main.
CAFÉ — Documentation de travail, mise à jour en novembre 2026. Toute publication de résultats doit distinguer observations INSEE, estimations communales et scénario exploratoire non marchand.