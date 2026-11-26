# SupplyWise — Demand, Inventory & Supply Planning

A reproducible synthetic-data planning demo built to the ORYVA AI student assignment brief. It generates linked supply-chain tables, projects stock against forecast demand, flags shortages, ranks shortage priorities, suggests supplier-based mitigation options, and exposes validation checks in a Streamlit dashboard.

> This is a decision-support prototype using synthetic data, not a production ERP or purchasing system. Recommendations are illustrative and do not create purchase orders.

## Features
- Deterministic synthetic data with configurable `starter` or `full` scale and seed.
- Master/dependent records with stable IDs and CSV exports.
- SKU-location forecast, on-hand/inbound inventory and projected balance.
- Shortage detection and criticality/cost-weighted priority.
- Supplier capacity, lead time plus transport delay filtering, and mitigation candidates.
- Separate labelled edge-case fixtures and ground-truth labels.
- Basic key/FK and non-negative validation checks.
- Dashboard tabs for overview, shortages, mitigation, data explorer and validation.

## Quick start (Windows)
1. Install Python 3.10+ and enable Add Python to PATH.
2. Open project folder in VS Code.
3. Terminal: `py -m venv .venv`
4. Activate: `.venv\\Scripts\\activate`
5. Install: `pip install -r requirements.txt`
6. Run: `streamlit run app.py`

## Generate data
`python -m src.data_generator --scale starter --seed 20261022 --output data/generated`

Full baseline scale: `python -m src.data_generator --scale full --seed 20261022 --output data/generated`

## Tests
`pytest -q`

## Dataset scale
Starter: 250 SKUs, 8 locations, 40 suppliers, 800 orders, 12 weeks, 3 active locations per SKU.
Full: 3,000 SKUs, 50 locations, 500 suppliers, 10,000 orders, 52 weeks, 5 active locations per SKU.

## Planning logic
Projected Available = On-hand + Inbound − Forecast Demand. Shortage is negative projected balance converted to positive missing units. Mitigation candidates are ranked against supplier lead time plus transport delay and capped to weekly capacity. Priority score uses shortage units × unit cost × criticality multiplier.

## Limitations
Demand is synthetic, not trained on sales history. BOM, manufacturing scheduling, transfers and approvals are only partially represented. Supplier capacity is not globally allocated across competing POs. Full mode can generate a large forecast file.
