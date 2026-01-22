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
    
    /* INTEL CARD */
    .intel-card {
        background-color: #0F0F0F;
        border-left: 3px solid #D32F2F;
        border-bottom: 1px solid #222;
        padding: 15px;
        margin-bottom: 12px;
    }
    .intel-header { color: #D32F2F; font-weight: bold; font-size: 1.0em; letter-spacing: 1px; }
    .intel-body { color: #EEE; font-size: 0.95em; margin-top: 5px; }
    
    /* BUTTONS */
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
        padding: 20px;
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

# --- 3. AGENT 3: THE GLOBAL PATTERN HUNTER ---
def execute_agent_3(full_df):
    if not groq_client: return ["// ERROR: AI OFFLINE"]
    
    # 1. AGGREGATE STATS (Global View)
    stats = full_df.groupby('vendor_name').agg(
        total_spend=('total_amount', 'sum'),
        txn_count=('invoice_id', 'count')
    ).reset_index()

    # 2. SELECT DATA FOR AI (Top 25 Vectors - High Spend OR High Frequency)
    # We send MORE data now to let the AI find subtle patterns
    targets = stats.sort_values(['total_spend', 'txn_count'], ascending=False).head(25)
    
    # 3. PREPARE EVIDENCE BLOCK
    evidence_lines = []
    for _, row in targets.iterrows():
        avg_ticket = row['total_spend'] / row['txn_count'] if row['txn_count'] > 0 else 0
        evidence_lines.append(
            f"VENDOR: {row['vendor_name']} | TOTAL: ${row['total_spend']:,.0f} | COUNT: {row['txn_count']} | AVG: ${avg_ticket:,.0f}"
        )

    # 4. THE "OMNISCIENT" PROMPT
    prompt = f"""
    SYSTEM: You are an Advanced Pattern Recognition Algorithm.
    TASK: Scan the vendor data below. Detect ANY mathematical or behavioral anomaly.
    
    PATTERNS TO ANALYZE:
    1. STRUCTURING: Is the 'AVG' ticket suspiciously close to $5,000 or $10,000? (e.g. $4950).
    2. VELOCITY: High 'COUNT' with Low/Med 'TOTAL' (Death by a thousand cuts).
    3. DOMINANCE: Does one vendor hold > 30% of the total cash?
    4. ROUND NUMBERS: Is the AVG exactly $500, $1000, $2000? (Human fabrication).
    5. LOW VALUE SPAM: High count of very small payments.
    
    INPUT DATA:
    {evidence_lines}
    
    OUTPUT FORMAT (Strict):
    [VENDOR] :: [PATTERN DETECTED] (Reason: [Math explanation])
    
    Example:
    TITANIUM CONSULTING :: STRUCTURING DETECTED (Reason: Avg $4,950 is 1% below $5k limit)
    """
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return res.choices[0].message.content.split('\n')
    except: return ["// ERROR: COMPUTATION FAILED"]

# --- 4. RENDER GLOBAL DASHBOARD ---
st.markdown("<h1>VANTAGE PROTOCOL // GLOBAL OVERSIGHT</h1>")

if not df.empty:
    # Cleanup
    df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce').fillna(0)
    df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce').fillna(0)

    # Meta Extraction
    def get_meta(x, key):
        try:
            import json
            if isinstance(x, dict): return x.get(key, '-')
            return json.loads(x).get(key, '-')
        except: return '-'
    df['approver'] = df['risk_flags'].apply(lambda x: get_meta(x, 'approver'))
    df['description'] = df['risk_flags'].apply(lambda x: get_meta(x, 'description'))

    # LAYOUT: 50/50
    c1, c2 = st.columns(2)
    
    # --- LEFT: THE PIE CHART (Capital Distribution) ---
    with c1:
        st.markdown("#### TOTAL CAPITAL DISTRIBUTION")
        
        # Prepare Data for Pie
        # Group small vendors into "Others" to keep chart clean
        pie_data = df.groupby('vendor_name')['total_amount'].sum().reset_index()
        pie_data = pie_data.sort_values('total_amount', ascending=False)
        
        # Color Scale: Dark Red theme
        fig = px.pie(
            pie_data, 
            values='total_amount', 
            names='vendor_name',
            hole=0.5, # Donut Chart
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        
        fig.update_layout(
            paper_bgcolor="#000", 
            plot_bgcolor="#000", 
            font=dict(color="#DDD", family="Courier New"),
            showlegend=False,
            annotations=[dict(text='CASH<br>FLOW', x=0.5, y=0.5, font_size=20, showarrow=False, font_color='white')]
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)

    # --- RIGHT: AGENT 3 INTELLIGENCE ---
    with c2:
        st.markdown("#### FORENSIC PATTERN ANALYSIS")
        
        if st.button("INITIALIZE DEEP SCAN (GLOBAL)", key="global_scan"):
            with st.spinner("SCANNING ALL VECTORS..."):
                findings = execute_agent_3(df)
                
                # Check if AI returned nothing useful
                valid_findings = False
                for find in findings:
                    if len(find) > 5 and "::" in find:
                        valid_findings = True
                        parts = find.split('::')
                        title = parts[0]
                        body = parts[1]
                        st.markdown(f"""
                        <div class="intel-card">
                            <div class="intel-header">{title}</div>
                            <div class="intel-body">{body}</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                if not valid_findings:
                    st.info("// ANALYSIS COMPLETE. NO HIGH-PROBABILITY PATTERNS FOUND.")
                    
        else:
            st.markdown("<div style='border:1px dashed #333; padding:60px; text-align:center; color:#555;'>AWAITING TRIGGER</div>", unsafe_allow_html=True)

    # --- BOTTOM: FULL LEDGER ---
    st.markdown("---")
    st.markdown("#### GLOBAL EVIDENCE LEDGER")
    cols_to_display = ['invoice_id', 'invoice_date', 'description', 'vendor_name', 'total_amount', 'approver', 'risk_score']
    
    st.dataframe(
        df[cols_to_display].sort_values('risk_score', ascending=False),
        use_container_width=True,
        column_config={
            "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%.0f"),
            "total_amount": st.column_config.NumberColumn("Amount", format="$%.2f")
        },
        hide_index=True
    )

    st.markdown("<br><center style='color:#444'>[ END OF TRANSMISSION ]</center>", unsafe_allow_html=True)

else:
    st.markdown("### SYSTEM STANDBY... CHECK UPLINK")
