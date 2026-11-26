# Data dictionary (prototype)

| Table | Primary key | Important fields | Meaning / validation |
|---|---|---|---|
| SKU | sku_id | category, uom, unit_cost, substitute_group, criticality | Product master; SKU ID pattern SKU-000001; unit cost positive; criticality low/medium/high |
| Location | location_id | location_name, region | Warehouse/store master; unique ID |
| Supplier | supplier_id | reliability_score, status | Supplier master; score 0–1; active/inactive |
| SupplierCapacity | supplier_id | weekly_capacity_units, minimum_order_qty, effective dates | Weekly supply limit; quantities nonnegative; dates valid |
| LeadTime | supplier_id | lead_time_days, transport_delay_days | Nonnegative days; total is sum of both |
| Inventory | inventory_id | sku_id, location_id, on_hand_units, inbound_units, reorder_point, as_of_date | Stock snapshot; IDs link to SKU and location; quantities nonnegative |
| ForecastDemand | demand_id | sku_id, location_id, week, forecast_units, week_start | Weekly forecast; deterministic ID; nonnegative units |
| PurchaseOrder | po_id | supplier_id, sku_id, location_id, quantity_units, order_date, expected_date, status | Inbound order; status open/confirmed/in_transit/received |
| ProductionPlan | production_plan_id | sku_id, weekly_capacity_units, production_lead_time_days | Simplified production capacity record |
| Shortage | shortage_id | shortage_units, priority_score, priority, reason | Derived from projected available balance; not a random label |
| MitigationOption | mitigation_id | shortage_id, supplier_id, recommended_units, lead_time_days, estimated_cost, feasible | Candidate option; quantities capped to supplier capacity in prototype |
| GroundTruth | issue_id | issue_type, record_id, expected_detection | Separate evaluation labels |
| AnomalyFixtures | anomaly_id | issue_type and issue-specific fields | Deliberate test scenarios, kept separate from baseline |

Relationships: SKU 1:N inventory and forecast demand; Location 1:N inventory and forecast demand; Supplier 1:1 capacity and lead-time records in this prototype; Supplier 1:N purchase orders. A SKU may have multiple locations and suppliers (many-to-many relationship; a bridge table would be added for approved sourcing in a production version).
