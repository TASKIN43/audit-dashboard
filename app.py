import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import time

# 1. PAGE SETUP
st.set_page_config(page_title="Audit Control", layout="wide")
st.title("System Audit Log")

# 2. SECURE CONNECTION
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Critical: Secrets missing. Go to App Settings -> Secrets to configure.")
    st.stop()

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_connection()

# 3. ROBUST DATA FETCHING (Retries on 502 Errors)
@st.cache_data(ttl=60)
def get_data_with_retry():
    if not supabase:
        return pd.DataFrame()
    
    # Try 3 times to connect
    for attempt in range(3):
        try:
            response = supabase.table("audit_ledger").select("*").execute()
            return pd.DataFrame(response.data)
        except Exception:
            time.sleep(1) # Wait 1 second and try again
    
    return pd.DataFrame() # Return empty if it fails 3 times

df = get_data_with_retry()

# 4. DASHBOARD RENDER
if df.empty:
    st.warning("System Online. Waiting for Data stream...")
    st.info("Status: Database is live but returned 0 rows or is waking up.")
else:
    # METRICS
    total_spend = pd.to_numeric(df['total_amount'], errors='coerce').sum()
    risk_rows = df[df['risk_score'] > 0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Processed", f"${total_spend:,.2f}")
    col2.metric("Invoices Scanned", len(df))
    col3.metric("Flags Detected", len(risk_rows))

    st.markdown("---")

    # CHARTS
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("Transaction Data")
        st.dataframe(df[['invoice_date', 'vendor_name', 'total_amount', 'risk_flags']], use_container_width=True)
    with c2:
        st.subheader("Vendor Overview")
        if 'vendor_name' in df.columns and 'total_amount' in df.columns:
            chart = df.groupby("vendor_name")['total_amount'].sum().reset_index()
            st.plotly_chart(px.bar(chart, x='vendor_name', y='total_amount'), use_container_width=True)
