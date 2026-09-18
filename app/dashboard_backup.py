import pandas as pd
import plotly.express as px
import streamlit as st


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="ExamGuard - K-Means",
    page_icon="🛡️",
    layout="wide"
)


# ==================================================
# TITLE
# ==================================================

st.title("🛡️ ExamGuard")
st.header("🔵 Exam Session Analysis")

st.caption(
    "Exam sessions based on behaviour patterns, "
    "integrity scores and risk levels"
)


# ==================================================
# LOAD K-MEANS DATA
# ==================================================

cluster_file = "data/session_clusters.csv"

df = pd.read_csv(cluster_file)


# ==================================================
# CALCULATE FACE ABSENCE RATIO
# IMPORTANT: DO THIS BEFORE SELECTING SESSION
# ==================================================

df["Face Absence Ratio"] = (
    1 - df["face_presence_ratio"]
)


# ==================================================
# SESSION SELECTION
# ==================================================

session_ids = sorted(
    df["session_id"].unique()
)

selected_session = st.selectbox(
    "Select Exam Session",
    session_ids
)


# Get selected session data
session_data = df[
    df["session_id"] == selected_session
].iloc[0]


# ==================================================
# GET INTEGRITY SCORE
# ==================================================

integrity_score = session_data["integrity_score"]


# ==================================================
# DETERMINE RISK LEVEL
# ==================================================

if integrity_score >= 70:
    risk_level = "Low"

elif integrity_score >= 40:
    risk_level = "Medium"

else:
    risk_level = "High"


# ==================================================
# DISPLAY MAIN METRICS
# ==================================================

col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Session ID",
        int(selected_session)
    )


with col2:

    st.metric(
        "Integrity Score",
        f"{integrity_score:.2f}"
    )


with col3:

    st.metric(
        "Risk Level",
        risk_level
    )


st.divider()


# ==================================================
# K-MEANS VISUALIZATION
# ==================================================

st.subheader("🔵 K-Means Clustering Visualization")

fig = px.scatter(
    df,

    x="Face Absence Ratio",

    y="integrity_score",

    color="cluster",

    hover_data=[
        "session_id",
        "event_count"
    ],

    title="K-Means Session Clustering",

    labels={
        "integrity_score": "Integrity Score",
        "Face Absence Ratio": "Face Absence Ratio",
        "cluster": "Cluster"
    }
)


fig.update_layout(
    height=600,

    xaxis_title="Face Absence Ratio",

    yaxis_title="Integrity Score",

    legend_title="Cluster"
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# ==================================================
# SELECTED SESSION DETAILS
# ==================================================

st.subheader("📊 Selected Session Details")


details = pd.DataFrame(
    {
        "Metric": [
            "Session ID",
            "Integrity Score",
            "Risk Level",
            "Face Presence Ratio",
            "Face Absence Ratio",
            "Event Count",
            "Cluster"
        ],

        "Value": [
            int(selected_session),

            f"{integrity_score:.2f}",

            risk_level,

            f"{session_data['face_presence_ratio']:.2f}",

            f"{session_data['Face Absence Ratio']:.2f}",

            int(session_data["event_count"]),

            int(session_data["cluster"])
        ]
    }
)


st.table(details)