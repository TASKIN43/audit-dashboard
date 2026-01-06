import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import time

# 1. PAGE SETUP
st.set_page_config(page_title="Audit Control", layout="wide")
st.title("System Audit Log")

# 2. SECURE CONNECTION
# Checks for secrets. If not found, handles gracefully.
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except FileNotFoundError:
    st.error("Critical: Secrets file not found on Streamlit Cloud.")
    st.stop()
except KeyError:
    st.error("Critical: 'SUPABASE_URL' or 'SUPABASE_KEY' missing from Secrets.")
    st.stop()

# Initialize Client
@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Failed to initialize Supabase client: {e}")
        return None

supabase = init_connection()

# 3. ROBUST DATA FETCHING (The Fix)
@st.cache_data(ttl=60)
def get_data_with_retry():
    if not supabase:
        return pd.DataFrame()
    
    # Try 3 times to connect (fixes 502 Gateway issues)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = supabase.table("audit_ledger").select("*").execute()
            # If successful, break loop
            return pd.DataFrame(response.data)
        except Exception as e:
            time.sleep(1) # Wait 1 second before retry
            if attempt == max_retries - 1:
                st.warning(f"Database connection unstable. Error details: {e}")
                return pd.DataFrame() # Return empty on final fail

df = get_data_with_retry()

# 4. DASHBOARD RENDER
if df.empty:
    st.warning("No data retrieved. Possible reasons: Database empty, Connection error, or System paused.")
    st.info("Check: Does the 'audit_ledger' table exist in Supabase?")
else:
    # Key Metrics
    total_spend = pd.to_numeric(df['total_amount'], errors='coerce').sum()
    risk_rows = df[df['risk_score'] > 0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Processed", f"${total_spend:,.2f}")
    col2.metric("Invoices Scanned", len(df))
    col3.metric("Flags Detected", len(risk_rows))

    st.markdown("---")

    # Layout
    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader("Transaction Data")
        # Ensure we only show columns that exist
        cols_to_show = ['invoice_date', 'vendor_name', 'total_amount', 'risk_flags']
        valid_cols = [c for c in cols_to_show if c in df.columns]
        st.dataframe(df[valid_cols], use_container_width=True)

    with c2:
        st.subheader("Vendor Overview")
        if 'vendor_name' in df.columns and 'total_amount' in df.columns:
            # Simple aggregation
            chart_data = df.groupby("vendor_name")['total_amount'].sum().reset_index()
            fig = px.bar(chart_data, x='vendor_name', y='total_amount')
            st.plotly_chart(fig, use_container_width=True)
