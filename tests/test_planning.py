import pandas as pd
from src.planning_engine import calculate_balance, build_shortages

def test_projected_balance():
    inv=pd.DataFrame([{'sku_id':'SKU-000001','location_id':'LOC-001','on_hand_units':100,'inbound_units':20,'reorder_point':10}])
    dem=pd.DataFrame([{'sku_id':'SKU-000001','location_id':'LOC-001','forecast_units':130}])
    result=calculate_balance(inv,dem).iloc[0]
    assert result.projected_available_units==-10
    assert result.shortage_units==10

def test_no_shortage():
    inv=pd.DataFrame([{'sku_id':'SKU-000001','location_id':'LOC-001','on_hand_units':100,'inbound_units':20,'reorder_point':10}])
    dem=pd.DataFrame([{'sku_id':'SKU-000001','location_id':'LOC-001','forecast_units':50}])
    assert calculate_balance(inv,dem).iloc[0].shortage_units==0

def test_edge_case_detection():
    from src.planning_engine import detect_edge_cases
    fixtures=pd.DataFrame([
      {'anomaly_id':'1','issue_type':'duplicate_inventory_count','duplicate_units':5},
      {'anomaly_id':'2','issue_type':'unapproved_substitute','approved':False},
      {'anomaly_id':'3','issue_type':'supplier_capacity_exceeded','requested_units':20,'capacity_units':10},
      {'anomaly_id':'4','issue_type':'lead_time_ignored','lead_time_days':5},
      {'anomaly_id':'5','issue_type':'uom_mismatch','conversion_factor':None}])
    assert detect_edge_cases(fixtures).detected.all()
