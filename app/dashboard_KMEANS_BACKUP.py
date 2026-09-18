import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


# ==========================================
# ExamGuard - K-Means Dashboard
# ==========================================

st.set_page_config(
    page_title="ExamGuard | K-Means Clustering",
    page_icon="🛡️",
    layout="wide"
)


# ==========================================
# Custom CSS
# ==========================================

st.markdown("""
<style>

    /* Main background */
    .stApp {
        background-color: #f5f7fb;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #102a43;
    }

    section[data-testid="stSidebar"] * {
        color: white;
    }

    /* Main title */
    .main-title {
        font-size: 32px;
        font-weight: 700;
        color: #102a43;
        margin-bottom: 5px;
    }

    .subtitle {
        color: #627d98;
        font-size: 15px;
        margin-bottom: 25px;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0px 2px 10px rgba(0,0,0,0.06);
        border: 1px solid #e6e9ef;
    }

    .metric-title {
        color: #627d98;
        font-size: 14px;
    }

    .metric-value {
        color: #102a43;
        font-size: 28px;
        font-weight: 700;
        margin-top: 5px;
    }

    /* Section headings */
    .section-title {
        font-size: 21px;
        font-weight: 650;
        color: #102a43;
        margin-top: 25px;
        margin-bottom: 12px;
    }

</style>
""", unsafe_allow_html=True)


# ==========================================
# Load Dataset
# ==========================================

DATA_FILE = Path("data/session_clusters.csv")

if not DATA_FILE.exists():

    st.error(
        "session_clusters.csv not found. "
        "Please run: python -m app.analytics"
    )

    st.stop()


df = pd.read_csv(DATA_FILE)


# ==========================================
# Prepare Data
# ==========================================

df["face_absence_ratio"] = (
    1 - df["face_presence_ratio"]
)

df["face_absence_ratio"] = (
    df["face_absence_ratio"].clip(lower=0)
)

# Risk classification based on integrity score
def get_risk(score):

    if score >= 70:
        return "Low"

    elif score >= 40:
        return "Medium"

    return "High"


df["risk_label"] = df["integrity_score"].apply(get_risk)


# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.markdown(
        """
        <h1 style="margin-bottom:0;">🛡️ ExamGuard</h1>
        <p style="margin-top:0;color:#bcccdc;">
        AI-Powered Exam Integrity
        </p>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    st.markdown("### 📊 Dashboard")

    st.write("Overview")
    st.write("Integrity Scores")
    st.write("Event Analysis")

    st.markdown(
        """
        <div style="
            background:#243b53;
            padding:10px;
            border-radius:8px;
            margin:5px 0;
        ">
        🔵 <b>K-Means Clustering</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("Cohort Risk Profile")
    st.write("AI Reports")
    st.write("Alerts & Evidence")

    st.markdown("---")

    st.caption("Milestone 3")
    st.caption("Data Science & Analytics")


# ==========================================
# HEADER
# ==========================================

st.markdown(
    '<div class="main-title">K-Means Session Clustering</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'ExamGuard session behaviour analysis using K-Means clustering'
    '</div>',
    unsafe_allow_html=True
)


# ==========================================
# TOP METRICS
# ==========================================

total_sessions = len(df)

total_clusters = df["cluster"].nunique()

avg_score = df["integrity_score"].mean()

avg_face_presence = df["face_presence_ratio"].mean()


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Sessions</div>
            <div class="metric-value">{total_sessions}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with col2:

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">K-Means Clusters</div>
            <div class="metric-value">{total_clusters}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with col3:

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Average Integrity Score</div>
            <div class="metric-value">{avg_score:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with col4:

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Face Presence</div>
            <div class="metric-value">{avg_face_presence:.2%}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================
# K-MEANS SCATTER PLOT
# ==========================================

st.markdown(
    '<div class="section-title">Session Cluster Visualization</div>',
    unsafe_allow_html=True
)

fig = px.scatter(
    df,
    x="face_absence_ratio",
    y="integrity_score",
    color="cluster",
    hover_data=[
        "session_id",
        "integrity_score",
        "face_presence_ratio",
        "event_count",
        "risk_label"
    ],
    labels={
        "face_absence_ratio": "Face Absence Ratio",
        "integrity_score": "Integrity Score",
        "cluster": "Cluster"
    },
    title="K-Means Session Behaviour Clustering"
)


fig.update_layout(
    height=500,
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(
        showgrid=True,
        tickformat=".0%"
    ),
    yaxis=dict(
        showgrid=True,
        range=[0, 105]
    ),
    legend_title="K-Means Cluster"
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# ==========================================
# CLUSTER SUMMARY
# ==========================================

st.markdown(
    '<div class="section-title">Cluster Summary</div>',
    unsafe_allow_html=True
)


cluster_summary = (
    df.groupby("cluster")
    .agg(
        Sessions=("session_id", "count"),
        Avg_Integrity=("integrity_score", "mean"),
        Avg_Face_Presence=("face_presence_ratio", "mean"),
        Avg_Events=("event_count", "mean")
    )
    .reset_index()
)


cluster_summary["Avg_Integrity"] = (
    cluster_summary["Avg_Integrity"].round(2)
)

cluster_summary["Avg_Face_Presence"] = (
    cluster_summary["Avg_Face_Presence"]
    .map(lambda x: f"{x:.2%}")
)

cluster_summary["Avg_Events"] = (
    cluster_summary["Avg_Events"].round(2)
)


st.dataframe(
    cluster_summary,
    use_container_width=True,
    hide_index=True
)


# ==========================================
# SESSION DETAILS
# ==========================================

st.markdown(
    '<div class="section-title">Session Cluster Details</div>',
    unsafe_allow_html=True
)


display_df = df[
    [
        "session_id",
        "integrity_score",
        "risk_label",
        "face_presence_ratio",
        "face_absence_ratio",
        "event_count",
        "cluster"
    ]
].copy()


display_df["integrity_score"] = (
    display_df["integrity_score"].round(2)
)

display_df["face_presence_ratio"] = (
    display_df["face_presence_ratio"]
    .map(lambda x: f"{x:.2%}")
)

display_df["face_absence_ratio"] = (
    display_df["face_absence_ratio"]
    .map(lambda x: f"{x:.2%}")
)


display_df = display_df.rename(
    columns={
        "session_id": "Session ID",
        "integrity_score": "Integrity Score",
        "risk_label": "Risk Level",
        "face_presence_ratio": "Face Presence",
        "face_absence_ratio": "Face Absence",
        "event_count": "Event Count",
        "cluster": "Cluster"
    }
)


st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# ==========================================
# RISK DISTRIBUTION
# ==========================================

st.markdown(
    '<div class="section-title">Risk Distribution</div>',
    unsafe_allow_html=True
)


risk_counts = (
    df["risk_label"]
    .value_counts()
    .reindex(
        ["Low", "Medium", "High"],
        fill_value=0
    )
    .reset_index()
)

risk_counts.columns = [
    "Risk Level",
    "Session Count"
]


col1, col2 = st.columns(2)


with col1:

    risk_fig = px.bar(
        risk_counts,
        x="Risk Level",
        y="Session Count",
        title="Session Risk Distribution",
        text="Session Count"
    )

    risk_fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white"
    )

    st.plotly_chart(
        risk_fig,
        use_container_width=True
    )


with col2:

    cluster_counts = (
        df["cluster"]
        .value_counts()
        .sort_index()
        .reset_index()
    )

    cluster_counts.columns = [
        "Cluster",
        "Session Count"
    ]

    cluster_fig = px.pie(
        cluster_counts,
        names="Cluster",
        values="Session Count",
        title="K-Means Cluster Distribution"
    )

    st.plotly_chart(
        cluster_fig,
        use_container_width=True
    )


# ==========================================
# FOOTER
# ==========================================

st.markdown("---")

st.caption(
    "ExamGuard | Milestone 3 | "
    "Integrity Scoring • K-Means Clustering • Risk Analytics"
)