import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

# --- 1. PAGE CONFIG & HIGH-END CSS ---
st.set_page_config(
    page_title="SENTINEL | Executive View",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for that "Classy/Dark" Audit look
st.markdown("""
<style>
    /* Remove default Streamlit padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Card Styling */
    .risk-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        font-family: 'Source Sans Pro', sans-serif;
    }
    .risk-score-high { color: #FF4B4B; font-weight: bold; }
    .risk-score-med { color: #FFAA00; font-weight: bold; }
    
    /* Hide Default Menus */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Scroll Indicator */
    .scroll-down {
        text-align: center;
        color: #888;
        font-size: 0.8rem;
        margin-top: 20px;
        animation: bounce 2s infinite;
    }
    
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
        40% {transform: translateY(-5px);}
        60% {transform: translateY(-3px);}
    }
</style>
""", unsafe_allow_html=True)

# --- 2. SECURE DATABASE CONNECTION ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("⚠️ SECURE CONNECTION FAILED. Please configure Secrets.")
    st.stop()

@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        return None

supabase = init_connection()

# --- 3. DATA FETCHING (Auto-Retry) ---
@st.cache_data(ttl=10)
def fetch_data():
    if not supabase: return pd.DataFrame()
    for _ in range(3):
        try:
            response = supabase.table("audit_ledger").select("*").execute()
            df = pd.DataFrame(response.data)
            return df
        except:
            time.sleep(1)
    return pd.DataFrame()

df = fetch_data()

# Refresh Logic
if st.button("↻ REFRESH INTEL", help="Fetch latest live audit data"):
    st.cache_data.clear()
    st.rerun()

st.title("🛡️ SENTINEL SYSTEM")

# --- 4. THE MAIN LAYOUT (Based on Your Sketch) ---
if not df.empty and 'risk_score' in df.columns:
    
    # CONVERT NUMBERS SAFELY
    df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce').fillna(0)
    df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce').fillna(0)
    
    # LOGIC: FIND THE "TOP 9" RISKS
    top_9_df = df.sort_values(by=['risk_score', 'total_amount'], ascending=[False, False]).head(9)
    
    # --- HERO SECTION (Graph Left, Top 9 Right) ---
    col_graph, col_list = st.columns([3, 1]) # 75% width vs 25% width
    
    with col_graph:
        st.markdown("### 📡 STRATEGIC RISK MATRIX")
        
        # THE BIG "CLASSY" GRAPH
        # Scatter Plot: X=Date/ID, Y=Amount, Color=Risk, Size=Risk
        # This isolates the "Dangerous" big money circles in Red
        fig = px.scatter(
            df, 
            x="invoice_date", 
            y="total_amount", 
            size="risk_score", 
            color="risk_score",
            hover_name="vendor_name",
            color_continuous_scale=['#00CC96', '#FFAA00', '#FF4B4B'], # Traffic Light Colors
            template="plotly_dark",
            height=500, # Matches height of the list roughly
            title="Exposure Timeline (Circle Size = Probability of Fraud)"
        )
        fig.update_layout(
            paper_bgcolor="#0E1117", 
            plot_bgcolor="#0E1117",
            font=dict(color="#E0E0E0")
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Click to scroll indicator
        st.markdown('<div class="scroll-down">▼ DETAILED LOGS BELOW ▼</div>', unsafe_allow_html=True)

    with col_list:
        st.markdown("### 🚨 TOP 9 ALERTS")
        
        # Generate the Top 9 Cards via Code
        for index, row in top_9_df.iterrows():
            vendor = row['vendor_name']
            amt = row['total_amount']
            score = row['risk_score']
            
            # Formatting CSS based on risk
            score_class = "risk-score-high" if score >= 80 else "risk-score-med"
            
            # HTML Card Injection
            st.markdown(f"""
            <div class="risk-card">
                <div style="font-size: 0.9rem; color: #888;">{row['invoice_date']}</div>
                <div style="font-weight: bold; font-size: 1.1rem;">{vendor}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 5px;">
                    <span>${amt:,.2f}</span>
                    <span class="{score_class}">RISK: {score:.0f}/100</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("---")
    
    # --- 5. DETAILED DATA BELOW (The Scroll Area) ---
    st.subheader("📂 Full Evidence Ledger")
    
    # Clean up flags for display
    def clean_flags(x):
        try: 
            return str(x)[:50] + "..." 
        except: 
            return x
            
    display_df = df.copy()
    display_df['risk_flags'] = display_df['risk_flags'].apply(clean_flags)
    
    st.dataframe(
        display_df[['invoice_date', 'vendor_name', 'total_amount', 'risk_score', 'risk_flags']],
        use_container_width=True,
        column_config={
            "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%.0f"),
            "total_amount": st.column_config.NumberColumn("Amount", format="$%.2f")
        }
    )

else:
    # --- WAITING SCREEN (If Database is empty) ---
    st.markdown("""
    <div style="text-align: center; margin-top: 100px;">
        <h1>🛡️ SYSTEM OFFLINE</h1>
        <p>No audit trail detected in Supabase ledger.</p>
        <p style="color: #666;">Waiting for neural network ingestion...</p>
    </div>
    """, unsafe_allow_html=True)
