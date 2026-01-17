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
    .intel-reason { color: #888; font-size: 0.85em; margin-top: 4px; font-style: italic;}
    
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

# --- 3. AGENT 3: THE QUANTITATIVE ANALYST ---
def execute_agent_3(sector_df):
    if not groq_client: return ["// ERROR: AI OFFLINE"]
    
    # 1. CALCULATE AGGREGATES
    stats = sector_df.groupby('vendor_name').agg(
        total_spend=('total_amount', 'sum'),
        txn_count=('invoice_id', 'count')
    ).reset_index()

    # 2. FILTER: Focus on Frequency OR High Value
    targets = stats[
        (stats['total_spend'] > 3000) | 
        (stats['txn_count'] >= 2)
    ].sort_values('total_spend', ascending=False).head(10)
    
    if targets.empty: return ["// STATUS: NOMINAL. DATA VOLUME TOO LOW FOR PATTERN ANALYSIS."]

    # 3. EVIDENCE PREP (Calculate Average Ticket for the AI)
    evidence_lines = []
    for _, row in targets.iterrows():
        avg_ticket = row['total_spend'] / row['txn_count']
        evidence_lines.append(
            f"VENDOR: {row['vendor_name']} | TOTAL: ${row['total_spend']:,.0f} | COUNT: {row['txn_count']} | AVG_TICKET: ${avg_ticket:,.0f}"
        )

    # 4. THE "REASONING" PROMPT
    prompt = f"""
    SYSTEM: You are a Forensic Auditor (Quantitative Specialist).
    TASK: Analyze the Vendor Aggregates below. Identify the 3-4 most critical anomalies.
    
    CRITICAL INSTRUCTION: You must explain WHY a pattern is suspicious using numbers.
    - If "Global Assets" has $45k (1 invoice), that is "Single Point Risk".
    - If "Titanium" has $15k (3 invoices of $5k), that is "Structuring/Limit Evasion".
    
    INPUT DATA:
    {evidence_lines}
    
    OUTPUT FORMAT (Strict):
    [VENDOR] :: [PATTERN NAME] | [EXACT REASONING]
    
    Examples:
    TITANIUM CONSULTING :: STRUCTURING RISK | Suspicious: 3 txns averaging $4,950 (Just below $5k limit).
    GLOBAL ASSETS :: CONCENTRATION RISK | Single vendor holds 60% of sector spend ($45k).
    SHELL FLEET :: VELOCITY ANOMALY | High frequency (15 txns) indicates potential card sharing.
    """
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return res.choices[0].message.content.split('\n')
    except: return ["// ERROR: COMPUTATION FAILED"]

# --- 4. RENDER ---
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
        
        # LEFT: GRAPH
        with c1:
            st.markdown("#### CAPITAL FLOW")
            chart_data = sector_df.groupby('vendor_name')['total_amount'].sum().reset_index()
            fig = px.bar(
                chart_data, x='vendor_name', y='total_amount',
                color='total_amount', color_continuous_scale=['#1a1a1a', '#D32F2F'],
                height=400
            )
            fig.update_layout(paper_bgcolor="#000", plot_bgcolor="#000", font=dict(color="#888", family="Courier New"))
            st.plotly_chart(fig)

        # RIGHT: INTEL
        with c2:
            st.markdown("#### PATTERN RECOGNITION")
            if st.button("INITIALIZE FORENSIC SCAN", key=f"btn_{sector}"):
                with st.spinner("ANALYZING AGGREGATES..."):
                    findings = execute_agent_3(sector_df)
                    for find in findings:
                        if len(find) > 5 and "::" in find:
                            # Parse the new format
                            parts = find.split('::')
                            vendor_name = parts[0]
                            rest = parts[1].split('|')
                            pattern = rest[0]
                            reason = rest[1] if len(rest) > 1 else "Anomaly detected."
                            
                            st.markdown(f"""
                            <div class="intel-card">
                                <div class="intel-header">{vendor_name} // {pattern}</div>
                                <div class="intel-body">{reason}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        elif "STATUS:" in find:
                             st.info(find)
            else:
                st.markdown("<div style='border:1px dashed #333; padding:40px; text-align:center; color:#555;'>AWAITING TRIGGER</div>", unsafe_allow_html=True)

        # BOTTOM: TABLE
        st.markdown("#### RAW EVIDENCE LEDGER")
        cols = ['invoice_id', 'invoice_date', 'description', 'vendor_name', 'total_amount', 'approver', 'risk_score']
        
        st.dataframe(
            sector_df[cols].sort_values('risk_score', ascending=False),
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
