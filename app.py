import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import time
from groq import Groq

# --- 1. CONFIG: PITCH BLACK / NO EMOJI ---
st.set_page_config(page_title="VANTAGE PROTOCOL", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* GLOBAL BLACK THEME */
    .stApp { background-color: #000000; color: #E0E0E0; font-family: 'Courier New', monospace; }
    
    /* TYPOGRAPHY */
    h1, h2, h3 { color: #FFF; letter-spacing: -1px; text-transform: uppercase; font-weight: 800; }
    div[data-testid="stMarkdownContainer"] p { font-size: 0.95rem; }

    /* LEFT: GRAPH CONTAINER */
    .graph-box { border-right: 1px solid #333; padding-right: 20px; }
    
    /* RIGHT: INTELLIGENCE CARD */
    .kill-list-card {
        background-color: #0a0a0a;
        border-left: 4px solid #FF3333;
        border-bottom: 1px solid #222;
        padding: 15px;
        margin-bottom: 12px;
        font-family: 'Courier New', monospace;
    }
    .kill-title { color: #FF3333; font-weight: bold; font-size: 1.0em; margin-bottom: 5px;}
    .kill-body { color: #DDD; font-size: 0.9em; }

    /* SEPARATOR */
    hr { border-color: #222; margin: 60px 0; }
    
    /* BUTTON STYLING (The Trigger) */
    div.stButton > button {
        background-color: #000;
        border: 1px solid #00D4FF;
        color: #00D4FF;
        border-radius: 0px;
        width: 100%;
        padding: 15px;
        font-family: monospace;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: bold;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #00D4FF;
        color: #000;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SECURE CONNECTIONS ---
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

# --- 3. AGENT 3 LOGIC (The Consultant) ---
def execute_agent_3(sector_df):
    if not groq_client: return ["// ERROR: AI OFFLINE"]
    
    # 1. Filter: Only look at Risk > 50 (The noise is ignored)
    targets = sector_df[sector_df['risk_score'] > 50].sort_values('risk_score', ascending=False).head(9)
    
    if targets.empty: return ["// STATUS: NOMINAL. NO LEAKAGE DETECTED."]

    # 2. Extract Evidence for the Prompt
    evidence_lines = []
    for _, row in targets.iterrows():
        # Unpack JSON flags safely
        issue = "ANOMALY"
        approver = "SYSTEM"
        try:
            import json
            flags = row['risk_flags']
            if isinstance(flags, str): flags = json.loads(flags)
            issue = flags.get('issue', 'ANOMALY').upper()
            approver = flags.get('approver', 'UNKNOWN').upper()
        except: pass
        
        evidence_lines.append(f"VENDOR: {row['vendor_name']} | AMT: ${row['total_amount']} | ISSUE: {issue} | AUTH: {approver}")

    # 3. The "McKinsey" Prompt
    prompt = f"""
    SYSTEM: You are a Senior Forensic Partner.
    CONTEXT: Analyzing Client AP Ledger for Leakage.
    INPUT DATA:
    {evidence_lines}
    
    MISSION:
    Convert raw data into a "Strategic Kill List".
    Use cold, corporate financial jargon (e.g., "Variance", "Structuring", "Compliance Gap").
    Focus on the MONEY and the PERSON (Approver).
    
    OUTPUT FORMAT (Strict List):
    [VENDOR NAME] :: [JARGON DESCRIPTION] (Auth: [NAME]) -> [DIRECTIVE]
    
    Example:
    TITANIUM INC :: STRUCTURED LIMIT EVASION (Auth: SARAH J) -> AUDIT PO.
    """
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192"
        )
        return res.choices[0].message.content.split('\n')
    except: return ["// ERROR: COMPUTATION FAILED"]

# --- 4. RENDER DASHBOARD ---
st.markdown("<h1>VANTAGE PROTOCOL // OVERSIGHT TERMINAL</h1>")

if not df.empty:
    # Numeric Cleanup
    df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce').fillna(0)
    df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce').fillna(0)
    if 'department_name' not in df.columns: df['department_name'] = 'GENERAL_LEDGER'

    # Get Sectors
    sectors = df['department_name'].unique()
    
    for sector in sectors:
        st.markdown(f"## SECTOR: {sector.upper()}")
        
        sector_df = df[df['department_name'] == sector]
        
        # LAYOUT: 50% Graph | 50% Intel
        c1, c2 = st.columns(2)
        
        # --- LEFT: MONEY FLOW GRAPH ---
        with c1:
            st.markdown("#### CAPITAL OUTFLOW (VENDOR VOLUME)")
            # Group by Vendor to show total cash stack
            chart_data = sector_df.groupby('vendor_name').agg({
                'total_amount': 'sum',
                'risk_score': 'max' # Use worst score for color
            }).reset_index()
            
            fig = px.bar(
                chart_data, 
                x='vendor_name', y='total_amount',
                color='total_amount', # The more money, the brighter the bar
                color_continuous_scale=['#222', '#FF3333'], # Dark to Red
                height=450
            )
            
            fig.update_layout(
                paper_bgcolor="#000", 
                plot_bgcolor="#000", 
                font=dict(color="#888", family="Courier New"),
                xaxis_title=None, yaxis_title="USD VOLUME"
            )
            st.plotly_chart(fig, use_container_width=True)

        # --- RIGHT: AGENT 3 INTERFACE ---
        with c2:
            st.markdown("#### FORENSIC FINDINGS")
            
            # The Trigger
            btn_key = f"btn_{sector}"
            if st.button("INITIALIZE DIAGNOSTIC SCAN", key=btn_key):
                with st.spinner("AGENT 3: ANALYZING VECTORS..."):
                    
                    # CALL AGENT 3
                    kill_list = execute_agent_3(sector_df)
                    
                    # RENDER CARDS
                    for item in kill_list:
                        if len(item) > 5: # Filter empty lines
                            # Formatting the string for display
                            parts = item.split('::')
                            title = parts[0] if len(parts) > 0 else "ALERT"
                            body = parts[1] if len(parts) > 1 else item
                            
                            st.markdown(f"""
                            <div class="kill-list-card">
                                <div class="kill-title">{title}</div>
                                <div class="kill-body">{body}</div>
                            </div>
                            """, unsafe_allow_html=True)
            else:
                # Placeholder State
                st.markdown("""
                <div style="border:1px dashed #333; padding:50px; text-align:center; color:#444;">
                    AWAITING MANUAL TRIGGER
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        
    st.markdown("<center style='color:#444'>[ END OF TRANSMISSION ]</center>", unsafe_allow_html=True)

else:
    st.markdown("### SYSTEM STANDBY... WAITING FOR UPLINK")
