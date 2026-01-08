import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import time
from groq import Groq

# --- 1. ENTERPRISE CONFIGURATION ---
st.set_page_config(page_title="VANTAGE CENTRAL COMMAND", layout="wide", initial_sidebar_state="collapsed")

# --- 2. DARK UI SYSTEM ---
st.markdown("""
<style>
    .stApp { background-color: #0b0c0e; color: #E0E0E0; }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    
    /* STRATEGY CARD */
    .strategy-box {
        background-color: #0f172a;
        border-left: 4px solid #00D4FF;
        padding: 20px;
        margin: 15px 0;
    }
    
    /* TABLE STYLING */
    .stDataFrame { border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

# --- 3. CONNECTIONS ---
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    try: groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except: groq_client = None
except:
    st.error("SYSTEM HALTED: CREDENTIALS MISSING")
    st.stop()

# --- 4. DATA LOADING ---
@st.cache_data(ttl=15)
def load_master_ledger():
    if not supabase: return pd.DataFrame()
    for _ in range(3):
        try:
            response = supabase.table("audit_ledger").select("*").execute()
            df = pd.DataFrame(response.data)
            if df.empty: return pd.DataFrame()
            
            # Numeric & Sanitization
            df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce').fillna(0)
            df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce').fillna(0)
            if 'department_name' not in df.columns: df['department_name'] = 'Unclassified'
            if 'invoice_id' not in df.columns: df['invoice_id'] = 'N/A'
            return df
        except: time.sleep(1)
    return pd.DataFrame()

df = load_master_ledger()

# --- 5. VICTOR VANTAGE AI ---
def get_vantage_intel(context_df):
    if not groq_client: return "AI OFFLINE."
    
    total = context_df['total_amount'].sum()
    risk = context_df[context_df['risk_score'] > 60]['total_amount'].sum()
    worst_vendor = context_df.groupby('vendor_name')['risk_score'].max().idxmax()
    
    prompt = f"""
    SYSTEM: You are the Chief Risk Architect.
    CONTEXT: Auditing specific organization vectors.
    INTEL: Total Flow ${total:,.0f}. At Risk: ${risk:,.0f}. Primary Adversary: {worst_vendor}.
    
    MISSION: Issue 3 rapid-fire directives. No intro. No filler.
    FORMAT:
    > [DIRECTIVE 1]
    > [DIRECTIVE 2]
    > [DIRECTIVE 3]
    """
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192"
        )
        return res.choices[0].message.content
    except Exception as e: return str(e)

# --- 6. DASHBOARD UI ---

if df.empty:
    st.title(" SENTINEL // WAITING FOR UPLINK")
else:
    # --- HEADER STATS (Aggregated) ---
    st.markdown("###  OPERATIONS OVERVIEW")
    
    tot_risk = df[df['risk_score']>60]['total_amount'].sum()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Spend", f"${df['total_amount'].sum():,.0f}")
    m2.metric("Critical Exposure", f"${tot_risk:,.0f}", delta="Alert" if tot_risk > 0 else "Secure", delta_color="inverse")
    m3.metric("Vendors Audited", len(df['vendor_name'].unique()))
    m4.metric("Protocol Departments", len(df['department_name'].unique()))
    
    st.markdown("---")

    # --- MAIN VIEW: THE MASTER CHART ---
    # One big chart showing everything, colored by Department
    col_chart, col_ai = st.columns([2, 1])
    
    with col_chart:
        st.subheader("📡 CROSS-SECTOR RISK MAP")
        fig = px.scatter(
            df, 
            x="invoice_date", y="total_amount",
            size="risk_score", 
            color="department_name", # This is the key: Colors separate the Depts
            hover_name="vendor_name",
            hover_data=["invoice_id", "risk_score"],
            template="plotly_dark", height=500,
            title="Entity-Wide Transaction Anomaly Detection"
        )
        fig.update_layout(paper_bgcolor="#0b0c0e", plot_bgcolor="#0b0c0e")
        st.plotly_chart(fig, use_container_width=True)

    with col_ai:
        st.subheader("🦅 VICTOR VANTAGE PROTOCOL")
        # Department Filter for AI
        dept_options = ["FULL ORGANIZATION"] + list(df['department_name'].unique())
        target_scope = st.selectbox("SELECT TARGET VECTOR:", dept_options)
        
        if st.button("INITIALIZE ANALYSIS", type="primary"):
            with st.spinner("Compiling Neural Intel..."):
                # Filter Data based on selection
                if target_scope == "FULL ORGANIZATION":
                    scope_df = df
                else:
                    scope_df = df[df['department_name'] == target_scope]
                
                intel = get_vantage_intel(scope_df)
                
                st.markdown(f"""
                <div class='strategy-box'>
                    <div style='color: #00D4FF; font-family: monospace; font-size: 0.9rem;'>
                        {intel.replace('\n', '<br>')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # --- MASTER SPREADSHEET ---
    st.subheader(" UNIFIED EVIDENCE LEDGER")
    
    # Filter Tabs
    # Allows user to see "All" or drill down without leaving the page
    tab_list = ["ALL"] + list(df['department_name'].unique())
    tabs = st.tabs(tab_list)
    
    # Render Master Table in "ALL", and specific tables in Tabs
    for i, tab in enumerate(tabs):
        with tab:
            if i == 0:
                view_df = df
            else:
                dept_name = tab_list[i]
                view_df = df[df['department_name'] == dept_name]
            
            # Search Bar simulation via text input could go here, but DataFrame has built-in search
            st.dataframe(
                view_df.sort_values(by="risk_score", ascending=False),
                column_config={
                    "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%.0f"),
                    "total_amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                    "raw_text": None, # Hide raw json
                    "risk_flags": None # Hide flag JSON
                },
                use_container_width=True,
                height=500
            )
