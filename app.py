import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import time
from groq import Groq

# --- 1. ENTERPRISE CONFIGURATION ---
st.set_page_config(
    page_title="VANTAGE SYSTEM",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. PROFESSIONAL STYLING (CSS) ---
st.markdown("""
<style>
    /* GLOBAL THEME OVERRIDE */
    .stApp { background-color: #0b0c0e; color: #E0E0E0; }
    
    /* REMOVE DEFAULT PADDING */
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }

    /* CARD SYSTEM: DATA ENTRY */
    .data-card {
        background-color: #16191f;
        border: 1px solid #2d3035;
        border-radius: 2px;
        padding: 16px;
        margin-bottom: 8px;
        font-family: 'IBM Plex Mono', monospace;
    }
    
    /* CARD SYSTEM: CRITICAL ALERT (Red Stripe) */
    .card-critical {
        border-left: 4px solid #FF3B30;
    }
    
    /* CARD SYSTEM: STANDARD (Grey Stripe) */
    .card-std {
        border-left: 4px solid #4A4A4A;
    }

    /* VANTAGE CARD: STRATEGY (Cyan Stripe) */
    .strategy-card {
        background-color: #0f172a;
        border-left: 4px solid #00D4FF;
        border-right: 1px solid #1e293b;
        border-top: 1px solid #1e293b;
        border-bottom: 1px solid #1e293b;
        padding: 20px;
        margin-top: 15px;
        border-radius: 2px;
    }

    /* TYPOGRAPHY */
    h1, h2, h3 { letter-spacing: -0.5px; font-weight: 600; }
    .header-tag { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1.5px; }
    .big-stat { font-size: 1.2rem; font-weight: 700; color: #FFF; }
    .risk-tag-high { color: #FF3B30; font-weight: 700; float: right; }
    .risk-tag-med { color: #FFD60A; font-weight: 700; float: right; }
    
    /* SEPARATOR */
    hr { border-color: #2d3035; margin: 40px 0; }
    
</style>
""", unsafe_allow_html=True)

# --- 3. INFRASTRUCTURE CONNECTION ---
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    # Graceful degradation if Groq missing
    try:
        groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except:
        groq_client = None
except:
    st.error("SYSTEM HALTED: CREDENTIALS MISSING")
    st.stop()

# --- 4. DATA PIPELINE ---
@st.cache_data(ttl=15)
def load_ledger():
    if not supabase: return pd.DataFrame()
    for _ in range(3):
        try:
            response = supabase.table("audit_ledger").select("*").execute()
            df = pd.DataFrame(response.data)
            if df.empty: return pd.DataFrame()
            
            # Numeric Sanitization
            df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce').fillna(0)
            df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce').fillna(0)
            if 'department_name' not in df.columns: df['department_name'] = 'General Operations'
            if 'invoice_id' not in df.columns: df['invoice_id'] = 'N/A'
            return df
        except:
            time.sleep(1)
    return pd.DataFrame()

df_master = load_ledger()

# --- HEADER SECTION ---
st.markdown("<div class='header-tag'>FORENSIC OVERSIGHT PLATFORM</div>", unsafe_allow_html=True)
st.markdown("<h1>VANTAGE PROTOCOL v1.0</h1>", unsafe_allow_html=True)

# --- 5. INTELLIGENCE AGENT (The Strategist) ---
def execute_protocol(dept_df, dept_name):
    if not groq_client: return "DIRECTIVE: ANALYSIS ENGINE OFFLINE."
    
    # Financial Intel
    total = dept_df['total_amount'].sum()
    risk = dept_df[dept_df['risk_score'] >= 60]['total_amount'].sum()
    
    if risk == 0: return "STATUS: OPTIMAL.\nNo intervention required."
    
    # Pattern Recognition
    worst_vendor = dept_df.groupby('vendor_name')['risk_score'].max().idxmax()
    
    prompt = f"""
    SYSTEM: You are a Corporate Turnaround Architect.
    CONTEXT: Auditing Department '{dept_name}'.
    DATA: Exposure ${risk:,.0f} out of ${total:,.0f}. Primary Source: {worst_vendor}.
    
    TASK: Issue 2 strategic directives to remediation.
    STYLE: Strict. No prose. Military-grade instructions.
    FORMAT:
    DIRECTIVE A: [Instruction]
    DIRECTIVE B: [Instruction]
    """
    
    try:
        res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192"
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"ERR: {e}"

# --- 6. VISUALIZATION ENGINE (Per Department) ---
if df_master.empty:
    st.code("WAITING FOR DATA UPLINK...", language="text")
else:
    unique_sectors = df_master['department_name'].unique()
    
    for sector in unique_sectors:
        # Isolate Data
        sector_df = df_master[df_master['department_name'] == sector]
        
        # Header for Section
        st.markdown(f"### SECTOR: {sector.upper()}")
        
        # Key Metrics Row (Mini Dashboard)
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Throughput", f"${sector_df['total_amount'].sum():,.2f}")
        with m2:
            st.metric("Risk Exposure", f"${sector_df[sector_df['risk_score']>60]['total_amount'].sum():,.2f}")
        with m3:
            st.metric("Transaction Volume", f"{len(sector_df)}")
            
        st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
        
        # Main Layout: 70% Matrix / 30% Feed
        col_main, col_feed = st.columns([2.5, 1])
        
        with col_main:
            # MATRIX GRAPH
            # Simplified "Dark" Aesthetics
            fig = px.scatter(
                sector_df, 
                x="invoice_date", y="total_amount", 
                size="risk_score", color="risk_score",
                color_continuous_scale=['#1C1C1C', '#00D4FF', '#FF3B30'], # Black->Blue->Red
                hover_name="vendor_name",
                hover_data=["invoice_id"],
                template="plotly_dark", height=400,
                title="RISK PROBABILITY MATRIX"
            )
            # Remove chart grid noise for cleaner look
            fig.update_layout(
                paper_bgcolor="#0E1117",
                plot_bgcolor="#0E1117",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#222'),
                margin=dict(l=0, r=0, t=40, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_feed:
            st.markdown("##### PRIORITY ALERTS")
            
            # Extract Top 4
            alerts = sector_df.sort_values(["risk_score", "total_amount"], ascending=False).head(4)
            
            for _, row in alerts.iterrows():
                # Risk Logic
                risk_val = row['risk_score']
                is_crit = risk_val >= 80
                css_class = "card-critical" if is_crit else "card-std"
                risk_tag_class = "risk-tag-high" if is_crit else "risk-tag-med"
                
                st.markdown(f"""
                <div class="data-card {css_class}">
                    <div style="font-size: 0.7rem; color: #666; letter-spacing: 1px;">ID: {row.get('invoice_id', 'N/A')}</div>
                    <div style="font-weight: 600; margin-top: 4px;">{row['vendor_name']}</div>
                    <div style="margin-top: 8px;">
                        <span style="color: #CCC;">${row['total_amount']:,.2f}</span>
                        <span class="{risk_tag_class}">R: {risk_val:.0f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        # --- THE VANTAGE BLOCK ---
        st.markdown(f"<div class='header-tag' style='margin-top: 20px;'>STRATEGIC INTERVENTION: {sector.upper()}</div>", unsafe_allow_html=True)
        
        btn_key = f"vantage_{sector.replace(' ', '_')}"
        if st.button("EXECUTE ANALYSIS PROTOCOL", key=btn_key):
            with st.spinner("Processing Logic Gate..."):
                intel = execute_protocol(sector_df, sector)
                
                # Split output
                lines = intel.split('\n')
                for line in lines:
                    if "DIRECTIVE" in line or "STATUS" in line:
                         st.markdown(f"""
                         <div class="strategy-card">
                            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 0.9rem; color: #00D4FF;">
                                {line}
                            </div>
                         </div>
                         """, unsafe_allow_html=True)
        
        st.markdown("---")
