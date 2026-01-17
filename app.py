import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import time
from groq import Groq

# --- 1. CONFIG ---
st.set_page_config(page_title="VANTAGE PROTOCOL", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #CCCCCC; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #FFFFFF; letter-spacing: -1px; text-transform: uppercase; font-weight: 800; }
    
    .intel-card {
        background-color: #0F0F0F;
        border-left: 3px solid #D32F2F;
        border-bottom: 1px solid #222;
        padding: 12px;
        margin-bottom: 10px;
    }
    .intel-header { color: #D32F2F; font-weight: bold; font-size: 0.9em; letter-spacing: 1px; }
    .intel-body { color: #EEE; font-size: 0.95em; margin-top: 4px; }
    
    div.stButton > button {
        background-color: #000;
        border: 1px solid #D32F2F;
        color: #D32F2F;
        width: 100%;
        font-family: monospace;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: bold;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #D32F2F;
        color: #000;
    }
    hr { border-color: #222; margin: 40px 0; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONNECTIONS ---
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    try: groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except: groq_client = None
except: st.stop()

@st.cache_data(ttl=10)
def load_data():
    try:
        r = supabase.table("audit_ledger").select("*").execute()
        return pd.DataFrame(r.data)
    except: return pd.DataFrame()

df = load_data()

# --- 3. AGENT 3: THE STATISTICIAN (GRAPH READER) ---
def execute_agent_3(sector_df):
    if not groq_client: return ["// ERROR: AI OFFLINE"]
    
    # STEP 1: CALCULATE THE GRAPH DATA (Aggregates)
    # We group by Vendor to see who got the money and how often.
    # This detects "Structuring" (High Count, Low Avg) and "Velocity" (High Count).
    stats = sector_df.groupby('vendor_name').agg(
        total_spend=('total_amount', 'sum'),
        txn_count=('invoice_id', 'count')
    ).reset_index()

    # STEP 2: FILTER TARGETS (Lowered Thresholds for Sensitivity)
    # Target anything with >$3,000 spend OR >2 transactions
    targets = stats[
        (stats['total_spend'] > 3000) | 
        (stats['txn_count'] >= 2)
    ].sort_values('total_spend', ascending=False).head(8)
    
    if targets.empty: 
        return ["// STATUS: LOW VOLUME. NO STATISTICAL ANOMALIES DETECTED."]

    # STEP 3: PREPARE EVIDENCE
    evidence_lines = []
    for _, row in targets.iterrows():
        avg_txn = row['total_spend'] / row['txn_count']
        evidence_lines.append(
            f"VENDOR: {row['vendor_name']} | TOTAL: ${row['total_spend']:,.0f} | COUNT: {row['txn_count']} | AVG_TICKET: ${avg_txn:,.0f}"
        )

    # STEP 4: THE STATISTICIAN PROMPT
    prompt = f"""
    SYSTEM: You are a Forensic Statistician. You analyze Graphs and Data Aggregates.
    TASK: Look at the Vendor Spend Summary below. Detect anomalies in the distribution.
    
    PATTERNS TO CATCH:
    1. STRUCTURING: High Count + Low/Medium Average Ticket (Splitting payments).
    2. VELOCITY: High Count (Frequency abuse).
    3. CONCENTRATION: Disproportionate Total Spend on one vendor.
    4. basically any kind of pattern you recognize.
    
    INPUT DATA (Vendor Aggregates):
    {evidence_lines}
    
    OUTPUT FORMAT (STRICT):
    [VENDOR] :: [STATISTICAL OBSERVATION] (Value: $X)
    
    Example:
    TITANIUM CONSULTING :: HIGH FREQUENCY / LOW AVG (Structuring Risk) (Value: $14k)
    """
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
            temperature=0.1
        )
        return res.choices[0].message.content.split('\n')
    except: return ["// ERROR: COMPUTATION FAILED"]

# --- 4. DASHBOARD RENDER ---
st.markdown("<h1>VANTAGE PROTOCOL // OVERSIGHT TERMINAL</h1>")

if not df.empty:
    df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce').fillna(0)
    df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce').fillna(0)
    if 'department_name' not in df.columns: df['department_name'] = 'GENERAL'

    def get_meta(x, key):
        try:
            import json
            if isinstance(x, dict): return x.get(key, '-')
            return json.loads(x).get(key, '-')
        except: return '-'
    df['approver'] = df['risk_flags'].apply(lambda x: get_meta(x, 'approver'))
    df['description'] = df['risk_flags'].apply(lambda x: get_meta(x, 'description'))

    sectors = df['department_name'].unique()
    
    for sector in sectors:
        st.markdown(f"## SECTOR: {sector.upper()}")
        sector_df = df[df['department_name'] == sector]
        
        c1, c2 = st.columns(2)
        
        # --- LEFT: MONEY GRAPH (Visualizing the Stats) ---
        with c1:
            st.markdown("#### CAPITAL FLOW")
            chart_data = sector_df.groupby('vendor_name')['total_amount'].sum().reset_index()
            fig = px.bar(
                chart_data, x='vendor_name', y='total_amount',
                color='total_amount', color_continuous_scale=['#1a1a1a', '#D32F2F'],
                height=400
            )
            # Clean layout, removed use_container_width arg to stop logs
            fig.update_layout(paper_bgcolor="#000", plot_bgcolor="#000", font=dict(color="#888", family="Courier New"))
            st.plotly_chart(fig) 

        # --- RIGHT: AGENT 3 INTEL ---
        with c2:
            st.markdown("#### PATTERN RECOGNITION")
            btn_key = f"scan_{sector}"
            
            if st.button("INITIALIZE FORENSIC SCAN", key=btn_key):
                with st.spinner("ANALYZING AGGREGATES..."):
                    findings = execute_agent_3(sector_df)
                    for find in findings:
                        if len(find) > 5 and "::" in find:
                            parts = find.split('::')
                            title = parts[0]
                            body = parts[1]
                            st.markdown(f"""
                            <div class="intel-card">
                                <div class="intel-header">{title}</div>
                                <div class="intel-body">{body}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        elif "STATUS:" in find:
                             st.info(find)
            else:
                st.markdown("<div style='border:1px dashed #333; padding:40px; text-align:center; color:#555;'>AWAITING TRIGGER</div>", unsafe_allow_html=True)

        # --- BOTTOM: EVIDENCE TABLE ---
        st.markdown("#### RAW EVIDENCE LEDGER")
        cols_to_display = ['invoice_id', 'invoice_date', 'description', 'vendor_name', 'total_amount', 'approver', 'risk_score']
        
        # Removed use_container_width to stop logs
        st.dataframe(
            sector_df[cols_to_display].sort_values('risk_score', ascending=False),
            column_config={
                "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%.0f"),
                "total_amount": st.column_config.NumberColumn("Amount", format="$%.2f")
            },
            hide_index=True
        )

        st.markdown("---")
        
    st.markdown("<center style='color:#444'>[ END OF TRANSMISSION ]</center>", unsafe_allow_html=True)

else:
    st.markdown("### SYSTEM STANDBY... CHECK UPLINK")
   
