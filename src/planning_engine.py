"""Inventory planning calculations, shortages, mitigation options and validations."""
import pandas as pd

def calculate_balance(inventory: pd.DataFrame, demand: pd.DataFrame) -> pd.DataFrame:
    d=demand.groupby(['sku_id','location_id'],as_index=False).forecast_units.sum().rename(columns={'forecast_units':'forecast_demand_units'})
    x=inventory.merge(d,on=['sku_id','location_id'],how='left').fillna({'forecast_demand_units':0})
    x['projected_available_units']=x.on_hand_units+x.inbound_units-x.forecast_demand_units
    x['shortage_units']=(-x.projected_available_units).clip(lower=0)
    x['surplus_units']=x.projected_available_units.clip(lower=0)
    x['status']=x.shortage_units.map(lambda n:'SHORTAGE' if n>0 else 'OK')
    return x

def build_shortages(balance: pd.DataFrame, sku: pd.DataFrame) -> pd.DataFrame:
    s=balance[balance.shortage_units>0].copy().merge(sku[['sku_id','criticality','unit_cost']],on='sku_id',how='left')
    s['shortage_id']=[f'SHORT-2026-{i:06d}' for i in range(1,len(s)+1)]
    s['priority_score']=s.shortage_units*s.unit_cost*s.criticality.map({'low':1,'medium':1.5,'high':2}).fillna(1)
    s['priority']=pd.cut(s.priority_score,[-1,1000,10000,float('inf')],labels=['Low','Medium','Critical']).astype(str)
    s['reason']='Forecast demand exceeds on-hand plus inbound inventory'
    return s.sort_values('priority_score',ascending=False)

def suggest_mitigations(shortages: pd.DataFrame, suppliers: pd.DataFrame, capacity: pd.DataFrame, lead: pd.DataFrame, horizon_days: int=14) -> pd.DataFrame:
    pool=suppliers.merge(capacity,on='supplier_id').merge(lead,on='supplier_id')
    pool=pool[pool.status=='active'].copy()
    pool['total_lead_days']=pool.lead_time_days+pool.transport_delay_days
    pool=pool[pool.total_lead_days<=horizon_days]
    rows=[]
    for _,s in shortages.iterrows():
        candidates=pool.sort_values(['total_lead_days','reliability_score'],ascending=[True,False]).head(3)
        for j,sp in enumerate(candidates.itertuples(),1):
            qty=min(int(s.shortage_units),int(sp.weekly_capacity_units))
            rows.append({'mitigation_id':f'MIT-{s.shortage_id}-{j:02d}','shortage_id':s.shortage_id,'sku_id':s.sku_id,'location_id':s.location_id,'supplier_id':sp.supplier_id,'recommended_units':qty,'lead_time_days':int(sp.total_lead_days),'estimated_cost':round(qty*float(s.unit_cost),2),'reliability_score':sp.reliability_score,'tradeoff':f'{qty} units; {int(sp.total_lead_days)} days lead time; reliability {sp.reliability_score:.0%}','feasible':qty>0 and qty<=sp.weekly_capacity_units})
    return pd.DataFrame(rows)

def validate_tables(tables: dict[str,pd.DataFrame]) -> list[dict]:
    checks=[]
    def add(name,ok,detail): checks.append({'check':name,'passed':bool(ok),'details':detail})
    primary_keys={'sku':'sku_id','location':'location_id','supplier':'supplier_id','supplier_capacity':'supplier_id','lead_time':'supplier_id','inventory':'inventory_id','forecast_demand':'demand_id','purchase_order':'po_id','production_plan':'production_plan_id'}
    for name,key in primary_keys.items():
        df=tables[name]
        add(f'{name}.{key} unique',df[key].is_unique,f'{df[key].duplicated().sum()} duplicate values')
    inv=tables['inventory']; sku=tables['sku']; loc=tables['location']; sup=tables['supplier']
    add('Inventory SKU foreign keys',inv.sku_id.isin(sku.sku_id).all(),'Inventory SKU references exist')
    add('Inventory location foreign keys',inv.location_id.isin(loc.location_id).all(),'Inventory location references exist')
    add('Purchase order supplier foreign keys',tables['purchase_order'].supplier_id.isin(sup.supplier_id).all(),'PO supplier references exist')
    add('Purchase order SKU foreign keys',tables['purchase_order'].sku_id.isin(sku.sku_id).all(),'PO SKU references exist')
    add('Demand units non-negative',(tables['forecast_demand'].forecast_units>=0).all(),'Demand must be >= 0')
    add('Inventory units non-negative',((inv.on_hand_units>=0)&(inv.inbound_units>=0)).all(),'Inventory values must be >= 0')
    add('IDs follow SKU pattern',sku.sku_id.str.match(r'^SKU-\d{6}$').all(),'SKU IDs are zero-padded')
    return checks

def col_is_key(col): return col in {'sku_id','location_id','supplier_id','inventory_id','demand_id','po_id','production_plan_id'}

def calculate_weekly_balance(inventory: pd.DataFrame, demand: pd.DataFrame) -> pd.DataFrame:
    """Time-phased projected balance using snapshot stock and inbound at week 1."""
    d=demand.sort_values('week').copy()
    d['cumulative_demand']=d.groupby(['sku_id','location_id']).forecast_units.cumsum()
    x=d.merge(inventory[['sku_id','location_id','on_hand_units','inbound_units']],on=['sku_id','location_id'],how='left')
    x['projected_balance_units']=x.on_hand_units+x.inbound_units-x.cumulative_demand
    x['shortage_units']=(-x.projected_balance_units).clip(lower=0)
    return x

def detect_edge_cases(fixtures: pd.DataFrame) -> pd.DataFrame:
    """Rule checks over explicit labelled fixture rows; returns explainable detections."""
    out=[]
    for row in fixtures.to_dict('records'):
        kind=row.get('issue_type'); detected=False; explanation='No rule matched'
        if kind=='duplicate_inventory_count':
            detected=bool(row.get('duplicate_units',0)>0); explanation='Duplicate source/count units are present in the fixture'
        elif kind=='unapproved_substitute':
            detected=not bool(row.get('approved',False)); explanation='Substitute approval flag is false; recommendation should be blocked'
        elif kind=='supplier_capacity_exceeded':
            detected=int(row.get('requested_units',0))>int(row.get('capacity_units',0)); explanation='Requested quantity is greater than weekly supplier capacity'
        elif kind=='lead_time_ignored':
            detected=int(row.get('lead_time_days',0))>0; explanation='The scenario contains nonzero lead time; check delivery against required date'
        elif kind=='uom_mismatch':
            detected=pd.isna(row.get('conversion_factor')); explanation='Demand and supplier units differ and no conversion factor is supplied'
        out.append({'anomaly_id':row.get('anomaly_id'),'issue_type':kind,'detected':detected,'explanation':explanation})
    return pd.DataFrame(out)
