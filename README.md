# CAFÉ — French Tourism Data Pipeline

## Project Overview

This repository contains Python scripts for collecting, processing, validating, and analyzing French tourism and geographic data as part of the CAFÉ project.

The objective is to prepare reproducible tourism indicators at three administrative levels:

- **Region** — `admin_level = 1`
- **Department** — `admin_level = 2`
- **Commune** — `admin_level = 4`

## Data Sources

The pipeline uses publicly available French datasets, including:

- **INSEE Melodi API** — Tourism overnight stays and statistical indicators.
- **INSEE Tourism Accommodation Capacity (2022)** — Hotels, campsites, and other collective tourist accommodation.
- **IGN Admin Express** — Geographic boundaries and administrative identifiers.

## Technologies

- Python
- Pandas and NumPy
- GeoPandas
- Matplotlib
- INSEE Melodi through `pynsee`
- Git and GitHub

## Processing Workflow

1. Retrieve tourism data from INSEE.
2. Download accommodation capacity data for 2022.
3. Clean and normalize geographic identifiers.
4. Join tourism data with administrative reference data.
5. Estimate commune-level overnight stays where only regional or departmental observations are available.
6. Aggregate and validate geographic results.
7. Export structured datasets for further analysis.

## Output Structure

The target dataset contains geographic identifiers and tourism indicators.

| Column | Description |
|---|---|
| `geocode` | INSEE geographic identifier |
| `admin_level` | Administrative level (1, 2, or 4) |
| `hotel_capacity` | Hotel accommodation capacity |
| `camping_capacity` | Campsite accommodation capacity |
| `other_capacity` | Other collective accommodation capacity |
| `hotel_nights_year` | Annual hotel overnight stays |
| `campings_nights_year` | Annual campsite overnight stays |
| `other_nights_year` | Annual other-accommodation overnight stays |
| `hotel_nights_january` | Hotel overnight stays in January |
| `campings_nights_january` | Campsite overnight stays in January |
| `other_nights_january` | Other-accommodation overnight stays in January |

**Current status:** The geographic and accommodation-capacity table has been generated. Overnight-stay integration and monthly indicators remain to be completed.

## Methodological Notes

Commune-level overnight stays are estimates obtained by allocating observed departmental or regional totals proportionally to local accommodation capacity.

Estimated values must be distinguished from directly observed INSEE statistics.

Camping observations covering only the high season must not be presented as full-year totals without an appropriate annual data source.

## Running the Project

Clone the repository and create a Python virtual environment.

```bash
git clone https://github.com/ansarymohammad-pixel/cafe-tourism-data-pipeline.git
cd cafe-tourism-data-pipeline

python -m venv .venv
```

Activate the environment, install the project dependencies, and run the required scripts from the project root.

```bash
python 31_tableau_final_cafe.py
```

The script requires previously prepared input datasets and geographic reference files.

## Data Management

Raw datasets, processed outputs, images, and PDF documents are excluded from Git tracking through `.gitignore`.

Source datasets should be downloaded from their official providers. Generated results can be reproduced by running the processing pipeline with the required inputs.

## Project Status

**Work in progress — November 2026**

Current work focuses on integrating 2022 accommodation capacities, harmonizing geographic identifiers, and preparing tourism indicators for the CAFÉ decision-support workflow.

## References

- [INSEE — Tourism Accommodation Capacity](https://www.insee.fr/fr/statistiques/2021703)
- [INSEE — Official Website](https://www.insee.fr/)
- [IGN — Geographic Data](https://geoservices.ign.fr/)

## License

No license has been specified for this repository. Reuse and redistribution permissions should be confirmed with the project supervisor before adding a license or publishing project-specific material.
