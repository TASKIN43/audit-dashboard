import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import time
from groq import Groq

# --- 1. PRESTIGE CONFIG ---
st.set_page_config(page_title="SENTINEL | OVERWATCH", page_icon="🦅", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* TITANIUM DARK THEME */
    .stApp { background-color: #0E1117; }
    
    /* VANTAGE CARD STYLING */
    .vantage-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border-left: 5px solid #00D2EA; /* Cyber Blue */
        padding: 20px;
        margin-top: 15px;
        border-radius: 0 10px 10px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .directive-title { color: #00D2EA; font-weight: bold; letter-spacing: 1px; font-size: 1.1em;}
    .directive-body { color: #E5E7EB; margin-top: 5px; font-size: 0.95em;}
    
    /* Risk Card Styling */
    .risk-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 8px;
    }
    
    /* Divider */
    hr { border-color: #333; margin: 60px 0; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONNECTIONS (DB + AI) ---
try:
    # We look for all keys. If Groq is missing, the AI button just won't work, but charts will.
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    try:
        groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except:
        groq_client = None
except:
    st.error("🔒 SYSTEM LOCK: Credentials missing in Streamlit Secrets.")
    st.stop()

# --- 3. DATA FETCHING ---
@st.cache_data(ttl=10)
def fetch_and_cluster_data():
    if not supabase: return pd.DataFrame()
    for _ in range(3): # Retry logic
        try:
            response = supabase.table("audit_ledger").select("*").execute()
            df = pd.DataFrame(response.data)
            if df.empty: return pd.DataFrame()
            
            # Numeric cleanup
            df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce').fillna(0)
            df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce').fillna(0)
            if 'department_name' not in df.columns: df['department_name'] = 'General_Ops'
            return df
        except:
            time.sleep(1)
    return pd.DataFrame()

df_master = fetch_and_cluster_data()

st.title("🦅 VICTOR VANTAGE | PROTOCOL")

# --- 4. THE STRATEGIST LOGIC (AGENT 3) ---
def consult_victor_vantage(dept_df, dept_name):
    if not groq_client: return "DIRECTIVE: AI_OFFLINE. Please add Groq Key."
    
    total_spend = dept_df['total_amount'].sum()
    risk_spend = dept_df[dept_df['risk_score'] >= 60]['total_amount'].sum()
    if risk_spend == 0: return "DIRECTIVE ALPHA: SECTOR CLEAN\nMaintain current protocols."

    # Identify the specific problem patterns
    bad_vendors = dept_df[dept_df['risk_score'] >= 80]['vendor_name'].value_counts().head(2).index.tolist()
    
    prompt = f"""
    SYSTEM: You are 'Victor Vantage'. Strategic Consultant.
    CONTEXT: Auditing Sector '{dept_name}'.
    DATA: Total Spend ${total_spend}. At-Risk: ${risk_spend}.
    FLAGGED VENDORS: {", ".join(bad_vendors)}.
    
    TASK: Write 2 "Directives" to fix this. Not generic advice. Specific to these risks.
    FORMAT:
    DIRECTIVE ALPHA: [Command]
    DIRECTIVE BRAVO: [Command]
    """
    
    try:
        completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"DIRECTIVE: ERROR CALCULATING. {e}"

# --- 5. THE SCROLL LOOP (The "Chaos" Handler) ---
if df_master.empty:
    st.info("...Satellite Uplink Established. Waiting for Data...")
else:
    # 1. Get List of every 'Part 1', 'Part 2', 'Chemical', 'Mech' found in the CSV
    unique_sectors = df_master['department_name'].unique()
    
    # 2. Iterate and Create a Dashboard for EACH one
    for sector in unique_sectors:
        sector_df = df_master[df_master['department_name'] == sector]
        
        # --- SECTOR HEADER ---
        st.header(f"📍 SECTOR: {sector.upper()}")
        
        col_left, col_right = st.columns([2, 1])
        
        # --- LEFT: THE RADAR GRAPH ---
        with col_left:
            fig = px.scatter(
                sector_df, 
                x="invoice_date", y="total_amount", 
                size="risk_score", color="risk_score",
                hover_name="vendor_name", hover_data=["invoice_id"],
                color_continuous_scale=['#00CC96', '#FF4B4B'],
                template="plotly_dark", height=450,
                title=f"{sector} // Risk Distribution"
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        # --- RIGHT: TOP 5 TARGETS ---
        with col_right:
            st.subheader("🚨 PRIORITY TARGETS")
            targets = sector_df.sort_values(['risk_score', 'total_amount'], ascending=[False, False]).head(5)
            
            for _, row in targets.iterrows():
                st.markdown(f"""
                <div class="risk-card">
                    <div style="font-size:0.8em; color:#888">{row.get('invoice_id','N/A')}</div>
                    <div style="font-weight:bold; font-size:1.1em">{row['vendor_name']}</div>
                    <div style="display:flex; justify-content:space-between; margin-top:5px;">
                         <span style="color:#EEE">${row['total_amount']:,.0f}</span>
                         <span style="color:#FF4B4B">RISK: {row['risk_score']:.0f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        # --- BOTTOM: THE VANTAGE BUTTON ---
        # The ID key ensures clicking one doesn't trigger all of them
        btn_key = f"vantage_{sector.replace(' ','_')}"
        
        if st.button(f"⚡ INITIALIZE VANTAGE PROTOCOL ({sector})", key=btn_key):
            with st.spinner("Decryption in progress..."):
                # Call Agent 3
                intel = consult_victor_vantage(sector_df, sector)
                
                # Render Results
                lines = intel.split('\n')
                for line in lines:
                    if "DIRECTIVE" in line:
                        parts = line.split(':')
                        title = parts[0]
                        body = parts[1] if len(parts) > 1 else ""
                        st.markdown(f"""
                        <div class="vantage-card">
                            <div class="directive-title">{title}</div>
                            <div class="directive-body">{body}</div>
                        </div>
                        """, unsafe_allow_html=True)
        
        # Divider between Sector Reports
        st.markdown("---")
