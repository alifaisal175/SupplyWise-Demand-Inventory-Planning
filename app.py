from pathlib import Path
import pandas as pd
import streamlit as st
from src.data_generator import generate, SEED_DEFAULT
from src.planning_engine import calculate_balance, calculate_weekly_balance, build_shortages, suggest_mitigations, validate_tables, detect_edge_cases

st.set_page_config(page_title='SupplyWise | Planning',page_icon='📦',layout='wide')
st.title('📦 SupplyWise')
st.caption('Demand, Inventory & Supply Planning | Synthetic, reproducible demo')
with st.sidebar:
    st.header('Demo controls')
    scale=st.selectbox('Dataset size',['Starter (fast demo)','Full assignment-scale'])
    seed=st.number_input('Random seed',value=SEED_DEFAULT,step=1)
    horizon=st.slider('Mitigation delivery window (days)',1,45,14)
    if st.button('Generate / refresh data',type='primary'):
        with st.spinner('Generating data...'):
            tables=generate('data/generated', 'full' if scale.startswith('Full') else 'starter',int(seed))
        st.session_state['tables']=tables
        st.success('Data generated. Seed and scale are recorded in this session.')
if 'tables' not in st.session_state:
    try:
        files=Path('data/generated')
        if files.exists(): st.session_state['tables']={p.stem:pd.read_csv(p) for p in files.glob('*.csv')}
    except Exception: pass
if 'tables' not in st.session_state:
    st.info('Choose a dataset size on the left and click Generate / refresh data to start. Starter mode is quickest for a live demo.')
    st.stop()
t=st.session_state['tables']
bal=calculate_balance(t['inventory'],t['forecast_demand']); shortages=build_shortages(bal,t['sku']); mitigations=suggest_mitigations(shortages,t['supplier'],t['supplier_capacity'],t['lead_time'],horizon)
checks=validate_tables(t)
weekly=calculate_weekly_balance(t['inventory'],t['forecast_demand'])
edge_results=detect_edge_cases(t['anomaly_fixtures'])
m1,m2,m3,m4=st.columns(4)
m1.metric('SKUs',f"{len(t['sku']):,}"); m2.metric('Inventory records',f"{len(t['inventory']):,}"); m3.metric('Shortage locations',f"{len(shortages):,}"); m4.metric('Total shortage units',f"{int(shortages.shortage_units.sum()):,}")
tab1,tab2,tab3,tab4,tab5=st.tabs(['Overview','Shortages','Mitigations','Data explorer','Validation & edge cases'])
with tab1:
    a,b=st.columns(2)
    with a:
        st.subheader('Inventory status')
        st.bar_chart(bal.status.value_counts())
    with b:
        st.subheader('Shortage priority')
        if not shortages.empty: st.bar_chart(shortages.priority.value_counts())
        else: st.success('No shortage in the generated sample.')
    st.subheader('Weekly stock trajectory')
    if not weekly.empty:
        selected_sku=st.selectbox('SKU for weekly view',weekly.sku_id.unique()[:100])
        selected_weekly=weekly[weekly.sku_id==selected_sku].groupby('week',as_index=False).projected_balance_units.sum()
        st.line_chart(selected_weekly.set_index('week'))
    st.subheader('Largest shortage locations')
    st.dataframe(shortages[['shortage_id','sku_id','location_id','forecast_demand_units','projected_available_units','shortage_units','priority','reason']].head(20),use_container_width=True)
with tab2:
    st.subheader('Shortage investigation')
    if shortages.empty: st.success('No shortages detected in this run.')
    else:
        p=st.selectbox('Priority filter',['All','Critical','Medium','Low'])
        view=shortages if p=='All' else shortages[shortages.priority==p]
        st.dataframe(view,use_container_width=True)
        st.download_button('Download shortage report CSV',view.to_csv(index=False),'shortages.csv','text/csv')
with tab3:
    st.subheader('Supplier mitigation options')
    st.caption(f'Options are limited to active suppliers whose combined supplier + transport lead time is within {horizon} days. Quantities respect weekly capacity.')
    if mitigations.empty: st.warning('No feasible supplier options found within selected horizon.')
    else:
        st.dataframe(mitigations.sort_values(['shortage_id','estimated_cost']),use_container_width=True)
        st.download_button('Download mitigation options CSV',mitigations.to_csv(index=False),'mitigation_options.csv','text/csv')
with tab4:
    name=st.selectbox('Dataset',list(t.keys()))
    st.dataframe(t[name].head(500),use_container_width=True)
    st.caption(f'{len(t[name]):,} rows × {len(t[name].columns)} columns (showing up to 500 rows)')
    st.download_button('Download selected data CSV',t[name].to_csv(index=False),f'{name}.csv','text/csv')
with tab5:
    st.subheader('Automated validation')
    result=pd.DataFrame(checks); st.dataframe(result,use_container_width=True)
    st.metric('Checks passed',f"{int(result.passed.sum())}/{len(result)}")
    st.subheader('Injected edge-case fixtures (labelled)')
    st.dataframe(t['anomaly_fixtures'],use_container_width=True)
    st.warning('Edge-case fixtures describe known issues for test/demo evaluation. They are kept separate from clean baseline tables.')
    st.subheader('Edge-case detector results')
    st.dataframe(edge_results,use_container_width=True)
    st.metric('Edge cases detected',f"{int(edge_results.detected.sum())}/{len(edge_results)}")
    st.subheader('Ground truth labels')
    st.dataframe(t['ground_truth'],use_container_width=True)
