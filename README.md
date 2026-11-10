# Al6061–SiC Mechanical Property Predictor (v5, academic prototype)

Literature-based dataset and prediction app for Al6061/SiC composites. **Estimates only – not design values.**

## Quick start
```bash
pip install -r requirements.txt
python scripts/build_dataset.py     # v4 workbook + scripts/new_records_v5.py -> data/*.xlsx, *.csv
python scripts/analyze_data.py      # plots + statistics -> reports/
python scripts/train_models.py      # leave-one-paper-out validation, saved models -> models/
streamlit run app/app.py
```
Python 3.10+. All outputs are already included, so the app runs without re-running the scripts.

## Layout
| Path | Content |
|---|---|
| `data/Al6061_SiC_Master_Dataset_v5.xlsx` | 12-sheet master workbook (START_HERE first) |
| `data/Al6061_SiC_Master_Dataset_v5.csv` | all 190 unique observations, long format, one row = one property observation |
| `data/Al6061_SiC_Core_Training_v5.csv` | Category A, Model_Set = Primary (36 rows) – the only rows used for training |
| `data/source/` | v4 workbook (input) |
| `scripts/new_records_v5.py` | every observation added in v5, with source location and status |
| `reports/` | validation table, statistics, figures |
| `models/` | saved models + `model_cards.json` (eligibility decision per target) |

## Data categories
A core binary | B supplementary binary (single-point, derived, flagged, incomplete process) | C hybrids | D process-specific (powder thixoforming, PM, compound bars) | F simulation | E excluded (see `Excluded_Papers`).
`Model_Set` says how a row may be used: `Primary`, `Sensitivity`, `Aging-only`, `No`.

## Honest status
* **Core training data:** UTS – 2 papers/9 obs; yield – 1 paper/6 obs; elongation – 2 papers/9 obs; Vickers HV – 3 papers/12 obs. Only SiC wt.% is a model feature.
* **Eligibility rule** (`scripts/train_models.py`): ≥3 papers, ≥10 observations, and leave-one-paper-out MAE below the mean baseline. Only **Vickers hardness** passes (Linear Regression, LOPO MAE 16.5 HV vs 41.7 baseline, R² 0.57). UTS, yield and elongation show the "Insufficient verified experimental data…" message.
* **Fragile result:** adding supplementary as-cast rows (diagnostic set) makes hardness R² negative. Treat the hardness model as a demonstration of the pipeline, not as validated.
* Process, heat-treatment and aging controls are intentionally **not** model inputs. Aging data exist for one paper at one composition (Rajasekaran 2012, 15 vol.%), so aging cannot be modelled.
* Rows inherited from v4 were not re-checked (original PDFs were unavailable). Rows new in v5 were read via text extraction of open-access pages and **not visually checked against PDFs**. Verification level is recorded per row.
* vol.% data (Rajasekaran, Zhang, Soliman) are stored in native units; a derived wt.% (ρAl 2.70, ρSiC 3.21 g/cm³) is provided and flagged.

## Not yet obtained (next batch)
Appendino 1995 (0–20 vol.%, 3 sizes, NA/PA/OA – highest value), Appendino 1991, Maurya 2020 tables, Mantha 2024 absolute values, Hu 2019 Figs 9–10 (UTS/elongation 0–30 wt.% by hot-pressing + T6; figure-only, needs digitising), plus a PDF check of every v5 row. Upload PDFs to the session to enable exact extraction.
