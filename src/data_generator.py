"""Deterministic synthetic supply-chain data generator for SupplyWise."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

SEED_DEFAULT = 20261022

def generate(output_dir: str | Path, scale: str = 'starter', seed: int = SEED_DEFAULT) -> dict[str, pd.DataFrame]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    if scale == 'starter':
        n_sku, n_loc, n_sup, n_orders, weeks, loc_per_sku = 250, 8, 40, 800, 12, 3
    elif scale == 'full':
        n_sku, n_loc, n_sup, n_orders, weeks, loc_per_sku = 3000, 50, 500, 10000, 52, 5
    else: raise ValueError("scale must be starter or full")
    skus = pd.DataFrame({'sku_id':[f'SKU-{i:06d}' for i in range(1,n_sku+1)],
        'sku_name':[f'Product {i:05d}' for i in range(1,n_sku+1)],
        'category':rng.choice(['Electronics','Home','Apparel','Food','Industrial'],n_sku),
        'uom':'each','unit_cost':np.round(rng.uniform(2,250,n_sku),2),
        'substitute_group':[f'SUB-{i//4:04d}' for i in range(n_sku)],
        'criticality':rng.choice(['low','medium','high'],n_sku,p=[.5,.35,.15])})
    locations = pd.DataFrame({'location_id':[f'LOC-{i:03d}' for i in range(1,n_loc+1)],
        'location_name':[f'Warehouse {i:02d}' for i in range(1,n_loc+1)],
        'region':rng.choice(['North','South','East','West','Central'],n_loc)})
    suppliers = pd.DataFrame({'supplier_id':[f'SUP-{i:04d}' for i in range(1,n_sup+1)],
        'supplier_name':[f'Supplier {i:04d}' for i in range(1,n_sup+1)],
        'reliability_score':np.round(rng.uniform(.65,.99,n_sup),2),'status':'active'})
    supplier_capacity = pd.DataFrame({'supplier_id':suppliers.supplier_id,
        'weekly_capacity_units':rng.integers(300,5000,n_sup),
        'minimum_order_qty':rng.choice([10,25,50,100],n_sup),
        'effective_from':'2026-01-01','effective_to':'2027-12-31'})
    lead_times = pd.DataFrame({'supplier_id':suppliers.supplier_id,
        'lead_time_days':rng.integers(3,35,n_sup),'transport_delay_days':rng.choice([0,0,0,2,5,10],n_sup)})
    inventory_rows=[]; demand_rows=[]
    for s in range(n_sku):
        selected_locs=rng.choice(n_loc,size=min(loc_per_sku,n_loc),replace=False)
        for li in selected_locs:
            sku=skus.iloc[s]; loc=locations.iloc[li]
            onhand=int(rng.integers(0,300)); inbound=int(rng.integers(0,160)); reorder=int(rng.integers(30,150))
            inventory_rows.append({'inventory_id':f'INV-{len(inventory_rows)+1:08d}','sku_id':sku.sku_id,'location_id':loc.location_id,'on_hand_units':onhand,'inbound_units':inbound,'reorder_point':reorder,'as_of_date':'2026-11-25'})
            base=int(rng.integers(5,80)); spike_week=int(rng.integers(1,weeks+1))
            for w in range(1,weeks+1):
                d=max(0,int(rng.normal(base, max(2,base*.18))))
                if w==spike_week: d=int(d*2.4)
                demand_rows.append({'demand_id':f'DEM-{sku.sku_id}-{loc.location_id}-2026W{w:02d}','sku_id':sku.sku_id,'location_id':loc.location_id,'week':w,'forecast_units':d,'week_start':f'2026-W{w:02d}'})
    inventory=pd.DataFrame(inventory_rows); demand=pd.DataFrame(demand_rows)
    order_sup=rng.integers(0,n_sup,n_orders); order_sku=rng.integers(0,n_sku,n_orders); order_loc=rng.integers(0,n_loc,n_orders)
    orders=pd.DataFrame({'po_id':[f'PO-2026-{i:06d}' for i in range(1,n_orders+1)],
        'supplier_id':suppliers.supplier_id.iloc[order_sup].to_numpy(),'sku_id':skus.sku_id.iloc[order_sku].to_numpy(),
        'location_id':locations.location_id.iloc[order_loc].to_numpy(),'quantity_units':rng.integers(10,400,n_orders),
        'order_date':'2026-11-01','expected_date':pd.to_datetime('2026-11-01')+pd.to_timedelta(rng.integers(3,35,n_orders),unit='D'),
        'status':rng.choice(['open','confirmed','in_transit','received'],n_orders,p=[.2,.3,.3,.2])})
    orders['expected_date']=orders.expected_date.dt.strftime('%Y-%m-%d')
    production=pd.DataFrame({'production_plan_id':[f'PROD-{i:06d}' for i in range(1,min(n_sku,500)+1)],
        'sku_id':skus.sku_id.iloc[:min(n_sku,500)],'weekly_capacity_units':rng.integers(0,500,min(n_sku,500)),
        'production_lead_time_days':rng.integers(2,21,min(n_sku,500))})
    gt=pd.DataFrame([
        {'issue_id':'ISSUE-001','issue_type':'duplicate_inventory_count','record_id':inventory.inventory_id.iloc[0],'expected_detection':'duplicate inventory source/count should be flagged'},
        {'issue_id':'ISSUE-002','issue_type':'unapproved_substitute','record_id':skus.sku_id.iloc[1],'expected_detection':'substitute is not approved; block recommendation'},
        {'issue_id':'ISSUE-003','issue_type':'supplier_capacity_exceeded','record_id':suppliers.supplier_id.iloc[0],'expected_detection':'allocated quantity exceeds weekly supplier capacity'},
        {'issue_id':'ISSUE-004','issue_type':'lead_time_ignored','record_id':orders.po_id.iloc[0],'expected_detection':'expected receipt after demand week cannot cover shortage'},
        {'issue_id':'ISSUE-005','issue_type':'uom_mismatch','record_id':skus.sku_id.iloc[2],'expected_detection':'case/each conversion is missing or inconsistent'}])
    anomalies=pd.DataFrame([
        {'anomaly_id':'ANOM-001','issue_type':'duplicate_inventory_count','inventory_id':inventory.inventory_id.iloc[0],'sku_id':inventory.sku_id.iloc[0],'location_id':inventory.location_id.iloc[0],'duplicate_units':inventory.on_hand_units.iloc[0]},
        {'anomaly_id':'ANOM-002','issue_type':'unapproved_substitute','sku_id':skus.sku_id.iloc[1],'substitute_sku_id':skus.sku_id.iloc[2],'approved':False},
        {'anomaly_id':'ANOM-003','issue_type':'supplier_capacity_exceeded','supplier_id':suppliers.supplier_id.iloc[0],'requested_units':int(supplier_capacity.weekly_capacity_units.iloc[0]+100),'capacity_units':int(supplier_capacity.weekly_capacity_units.iloc[0])},
        {'anomaly_id':'ANOM-004','issue_type':'lead_time_ignored','po_id':orders.po_id.iloc[0],'lead_time_days':int(lead_times.lead_time_days.iloc[order_sup[0]]+lead_times.transport_delay_days.iloc[order_sup[0]]),'required_by':'2026-11-28'},
        {'anomaly_id':'ANOM-005','issue_type':'uom_mismatch','sku_id':skus.sku_id.iloc[2],'demand_uom':'each','supplier_uom':'case','conversion_factor':None}])
    tables={'sku':skus,'location':locations,'supplier':suppliers,'supplier_capacity':supplier_capacity,'lead_time':lead_times,'inventory':inventory,'forecast_demand':demand,'purchase_order':orders,'production_plan':production,'ground_truth':gt,'anomaly_fixtures':anomalies}
    for name,df in tables.items(): df.to_csv(out/f'{name}.csv',index=False)
    return tables

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--scale',choices=['starter','full'],default='starter'); p.add_argument('--seed',type=int,default=SEED_DEFAULT); p.add_argument('--output',default='data')
    a=p.parse_args(); data=generate(a.output,a.scale,a.seed); print('Generated:',{k:len(v) for k,v in data.items()})
