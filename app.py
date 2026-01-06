import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import json

# 1. PAGE SETUP
st.set_page_config(page_title="Forensic Audit Control Center", layout="wide")
st.title("🛡️ Sentinel: Autonomous Forensic Audit System")

# 2. DATABASE CONNECTION (The Credentials)
# REPLACE THE TEXT INSIDE THE QUOTES BELOW
# 2. DATABASE CONNECTION (SECURE MODE)
# Instead of pasting keys here, we look for them in the "Secrets" vault
try:
    SUPABASE_URL = st.secrets["https://yiyhascgocesdumzyxro.supabase.co"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("Secrets not found! Did you add them to the Streamlit Dashboard settings?")
    st.stop()

# Initialize Connection
@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        return None

supabase = init_connection()

# 3. GET DATA FROM SUPABASE
def get_data():
    if not supabase:
        return pd.DataFrame()
    response = supabase.table("audit_ledger").select("*").execute()
    return pd.DataFrame(response.data)

df = get_data()

# 4. SHOW THE DASHBOARD
if df.empty:
    st.warning("Connected! No data found in database yet. Run the n8n workflow!")
else:
    # Top Stats
    st.success("System Online - Connection Secure")
    
    col1, col2, col3 = st.columns(3)
    
    total = df['total_amount'].sum()
    count = len(df)
    risky = df[df['risk_flags'].astype(str).str.contains("Struct|Fraud|Round", case=False, na=False)]
    
    col1.metric("Total Volume Processed", f"${total:,.2f}")
    col2.metric("Total Invoices", count)
    col3.metric("Flags Detected", len(risky))

    st.markdown("---")
    
    # The Visuals
    c1, c2 = st.columns([2,1])
    
    with c1:
        st.subheader("Live Transaction Feed")
        st.dataframe(df[['invoice_date', 'vendor_name', 'total_amount', 'risk_flags']], use_container_width=True)
        
    with c2:
        st.subheader("Vendor Analysis")
        chart_data = df.groupby("vendor_name")['total_amount'].sum().reset_index()
        fig = px.bar(chart_data, x='vendor_name', y='total_amount', title="Spend by Vendor")
        st.plotly_chart(fig, use_container_width=True)
