import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ExamGuard Dashboard",
    page_icon="🛡️",
    layout="wide"
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE = DATA_DIR / "examguard.db"


# ============================================================
# DATABASE HELPER
# ============================================================

def read_table(table_name):

    try:

        connection = sqlite3.connect(str(DATABASE))

        df = pd.read_sql_query(
            f"SELECT * FROM {table_name}",
            connection
        )

        connection.close()

        return df

    except Exception as error:

        st.warning(
            f"Could not load {table_name}: {error}"
        )

        return pd.DataFrame()


# ============================================================
# CSV HELPER
# ============================================================

def load_csv(filename):

    path = DATA_DIR / filename

    try:

        if path.exists():

            return pd.read_csv(path)

    except Exception as error:

        st.warning(
            f"Could not load {filename}: {error}"
        )

    return pd.DataFrame()


# ============================================================
# RISK LABEL
# ============================================================

def risk_label(score):

    try:

        score = float(score)

        if score >= 70:
            return "Low"

        elif score >= 40:
            return "Medium"

        else:
            return "High"

    except Exception:

        return "Unknown"


# ============================================================
# DOWNLOAD BUTTONS
# ============================================================

def download_buttons(df, name):

    if df.empty:
        return

    csv_data = df.to_csv(index=False)

    json_data = df.to_json(
        orient="records",
        indent=2
    )

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(
            "⬇️ Download CSV",
            csv_data,
            file_name=f"{name}.csv",
            mime="text/csv",
            key=f"{name}_csv_download"
        )

    with col2:

        st.download_button(
            "⬇️ Download JSON",
            json_data,
            file_name=f"{name}.json",
            mime="application/json",
            key=f"{name}_json_download"
        )


# ============================================================
# LOAD DATABASE TABLES
# ============================================================

sessions = read_table("exam_sessions")

alerts = read_table("alerts")

evidence = read_table("evidence")

face_events = read_table("face_events")

browser_events = read_table("browser_events")

ai_reports = read_table("ai_reports")


# ============================================================
# LOAD ANALYTICS CSV FILES
# ============================================================

clusters = load_csv(
    "session_clusters.csv"
)

cohort = load_csv(
    "cohort_risk_profile.csv"
)


# ============================================================
# PREPARE SESSION DATA
# ============================================================

if not sessions.empty:

    if "integrity_score" not in sessions.columns:

        sessions["integrity_score"] = 100.0

    sessions["integrity_score"] = pd.to_numeric(
        sessions["integrity_score"],
        errors="coerce"
    ).fillna(100.0)

    if "risk_label" not in sessions.columns:

        sessions["risk_label"] = sessions[
            "integrity_score"
        ].apply(risk_label)


# ============================================================
# PREPARE CLUSTER DATA
# ============================================================

if not clusters.empty:

    if "integrity_score" in clusters.columns:

        clusters["integrity_score"] = pd.to_numeric(
            clusters["integrity_score"],
            errors="coerce"
        )

    if "risk_level" not in clusters.columns:

        if "integrity_score" in clusters.columns:

            clusters["risk_level"] = clusters[
                "integrity_score"
            ].apply(risk_label)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    "# 🛡️ ExamGuard"
)

st.markdown(
    "## Online Exam Monitoring & Integrity Analytics Dashboard"
)

st.caption(
    "Monitoring, integrity scoring, risk analysis, alerts, "
    "K-Means clustering and report export"
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("ExamGuard")

menu = st.sidebar.radio(
    "Select Section",
    [
        "Overview",
        "Session Analysis",
        "K-Means Clustering",
        "Alerts & Evidence",
        "Event Analysis",
        "AI Reports",
        "Data Export"
    ]
)


# ============================================================
# 1. OVERVIEW
# ============================================================

if menu == "Overview":

    st.header("📊 Overview")

    if sessions.empty:

        st.warning(
            "No exam session data available."
        )

    else:

        total_sessions = len(sessions)

        average_score = sessions[
            "integrity_score"
        ].mean()

        high_risk = (
            sessions["risk_label"] == "High"
        ).sum()

        medium_risk = (
            sessions["risk_label"] == "Medium"
        ).sum()

        low_risk = (
            sessions["risk_label"] == "Low"
        ).sum()

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total Sessions",
            total_sessions
        )

        col2.metric(
            "Average Integrity Score",
            f"{average_score:.2f}"
        )

        col3.metric(
            "High Risk Sessions",
            high_risk
        )

        col4.metric(
            "Low Risk Sessions",
            low_risk
        )

        st.divider()

        st.subheader(
            "Risk Distribution"
        )

        risk_df = (
            sessions["risk_label"]
            .value_counts()
            .reset_index()
        )

        risk_df.columns = [
            "Risk Level",
            "Sessions"
        ]

        fig = px.bar(
            risk_df,
            x="Risk Level",
            y="Sessions",
            title="Session Risk Distribution"
        )

        st.plotly_chart(
            fig,
            width="stretch"
        )

        st.subheader(
            "Integrity Score Distribution"
        )

        fig2 = px.histogram(
            sessions,
            x="integrity_score",
            nbins=10,
            title="Integrity Score Distribution"
        )

        st.plotly_chart(
            fig2,
            width="stretch"
        )


# ============================================================
# 2. SESSION ANALYSIS
# ============================================================

elif menu == "Session Analysis":

    st.header("🔎 Session Analysis")

    if sessions.empty:

        st.warning(
            "No session data available."
        )

    elif "id" not in sessions.columns:

        st.error(
            "Session ID column not found."
        )

    else:

        session_ids = (
            sessions["id"]
            .dropna()
            .astype(int)
            .tolist()
        )

        selected_session = st.selectbox(
            "Select Exam Session",
            session_ids
        )

        selected = sessions[
            sessions["id"] == selected_session
        ]

        if not selected.empty:

            row = selected.iloc[0]

            score = float(
                row.get(
                    "integrity_score",
                    100
                )
            )

            risk = row.get(
                "risk_label",
                risk_label(score)
            )

            st.subheader(
                f"Session {selected_session}"
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Integrity Score",
                f"{score:.2f}"
            )

            col2.metric(
                "Risk Level",
                risk
            )

            col3.metric(
                "Session Status",
                row.get(
                    "status",
                    "Unknown"
                )
            )

            st.divider()

            st.subheader(
                "Session Details"
            )

            st.dataframe(
                selected,
                width="stretch"
            )

            st.subheader(
                "Face Monitoring Events"
            )

            if (
                not face_events.empty
                and "session_id"
                in face_events.columns
            ):

                session_face = face_events[
                    face_events["session_id"]
                    == selected_session
                ]

                if session_face.empty:

                    st.info(
                        "No face events for this session."
                    )

                else:

                    st.dataframe(
                        session_face,
                        width="stretch"
                    )

            else:

                st.info(
                    "No face event data available."
                )

            st.subheader(
                "Browser Monitoring Events"
            )

            if (
                not browser_events.empty
                and "session_id"
                in browser_events.columns
            ):

                session_browser = browser_events[
                    browser_events["session_id"]
                    == selected_session
                ]

                if session_browser.empty:

                    st.info(
                        "No browser events for this session."
                    )

                else:

                    st.dataframe(
                        session_browser,
                        width="stretch"
                    )

            else:

                st.info(
                    "No browser event data available."
                )


# ============================================================
# 3. K-MEANS CLUSTERING
# ============================================================

elif menu == "K-Means Clustering":

    st.header(
        "🤖 K-Means Session Clustering"
    )

    if clusters.empty:

        st.warning(
            "session_clusters.csv is empty or not found."
        )

        st.info(
            "Run: python app\\analytics.py"
        )

    else:

        st.subheader(
            "Cluster Results"
        )

        st.dataframe(
            clusters,
            width="stretch"
        )

        st.divider()

        if (
            "integrity_score" in clusters.columns
            and "event_count" in clusters.columns
        ):

            st.subheader(
                "Integrity Score vs Event Count"
            )

            if "cluster" in clusters.columns:

                fig = px.scatter(
                    clusters,
                    x="integrity_score",
                    y="event_count",
                    color="cluster",
                    title="K-Means Session Clusters"
                )

            else:

                fig = px.scatter(
                    clusters,
                    x="integrity_score",
                    y="event_count",
                    title="Integrity Score vs Event Count"
                )

            st.plotly_chart(
                fig,
                width="stretch"
            )

        st.subheader(
            "Cohort Risk Profile"
        )

        if cohort.empty:

            st.info(
                "cohort_risk_profile.csv not found."
            )

        else:

            st.dataframe(
                cohort,
                width="stretch"
            )


# ============================================================
# 4. ALERTS & EVIDENCE
# ============================================================

elif menu == "Alerts & Evidence":

    st.header(
        "🚨 Alerts & Evidence"
    )

    # --------------------------------------------------------
    # ALERTS
    # --------------------------------------------------------

    st.subheader(
        "🚨 Alerts"
    )

    if alerts.empty:

        st.info(
            "No alerts available."
        )

    else:

        st.success(
            f"{len(alerts)} alert records found."
        )

        st.dataframe(
            alerts,
            width="stretch",
            height=400
        )

        download_buttons(
            alerts,
            "examguard_alerts"
        )

    st.divider()

    # --------------------------------------------------------
    # EVIDENCE
    # --------------------------------------------------------

    st.subheader(
        "📁 Evidence"
    )

    if evidence.empty:

        st.info(
            "No evidence records available."
        )

    else:

        st.success(
            f"{len(evidence)} evidence records found."
        )

        st.dataframe(
            evidence,
            width="stretch",
            height=400
        )

        download_buttons(
            evidence,
            "examguard_evidence"
        )


# ============================================================
# 5. EVENT ANALYSIS
# ============================================================

elif menu == "Event Analysis":

    st.header(
        "📈 Event Analysis"
    )

    event_frames = []

    # --------------------------------------------------------
    # FACE EVENTS
    # --------------------------------------------------------

    if not face_events.empty:

        face_copy = face_events.copy()

        face_copy["source"] = "Face Monitoring"

        event_frames.append(
            face_copy
        )

    # --------------------------------------------------------
    # BROWSER EVENTS
    # --------------------------------------------------------

    if not browser_events.empty:

        browser_copy = browser_events.copy()

        browser_copy["source"] = "Browser Monitoring"

        event_frames.append(
            browser_copy
        )

    if not event_frames:

        st.warning(
            "No monitoring events available."
        )

    else:

        all_events = pd.concat(
            event_frames,
            ignore_index=True,
            sort=False
        )

        st.success(
            f"{len(all_events)} monitoring event records found."
        )

        if "event_type" in all_events.columns:

            frequency = (
                all_events["event_type"]
                .value_counts()
                .reset_index()
            )

            frequency.columns = [
                "Event Type",
                "Count"
            ]

            st.subheader(
                "Event Frequency"
            )

            fig = px.bar(
                frequency,
                x="Event Type",
                y="Count",
                title="Monitoring Event Frequency"
            )

            st.plotly_chart(
                fig,
                width="stretch"
            )

        st.subheader(
            "Event Details"
        )

        st.dataframe(
            all_events,
            width="stretch",
            height=500
        )

        download_buttons(
            all_events,
            "examguard_events"
        )


# ============================================================
# 6. AI REPORTS
# ============================================================

elif menu == "AI Reports":

    st.header(
        "🧠 AI Integrity Reports"
    )

    # --------------------------------------------------------
    # REPORT COUNT
    # --------------------------------------------------------

    if ai_reports.empty:

        st.warning(
            "AI Reports table is empty."
        )

        st.info(
            "Run: python ai_report_agent.py"
        )

    else:

        st.success(
            f"{len(ai_reports)} AI reports found in database."
        )

        # ----------------------------------------------------
        # COMPLETE REPORT TABLE
        # ----------------------------------------------------

        st.subheader(
            "📋 Generated AI Reports"
        )

        st.dataframe(
            ai_reports,
            width="stretch",
            height=400
        )

        st.divider()

        # ----------------------------------------------------
        # REPORT DETAILS
        # ----------------------------------------------------

        st.subheader(
            "📄 Report Details"
        )

        # Find a useful ID column

        id_column = None

        for column in [
            "id",
            "report_id",
            "session_id"
        ]:

            if column in ai_reports.columns:

                id_column = column
                break

        if id_column:

            report_options = (
                ai_reports[id_column]
                .dropna()
                .tolist()
            )

            if report_options:

                selected_report = st.selectbox(
                    "Select Report",
                    report_options
                )

                selected_rows = ai_reports[
                    ai_reports[id_column]
                    == selected_report
                ]

            else:

                selected_rows = ai_reports

        else:

            selected_rows = ai_reports

        # ----------------------------------------------------
        # SHOW EVERY FIELD
        # ----------------------------------------------------

        if not selected_rows.empty:

            report = selected_rows.iloc[0]

            for column in selected_rows.columns:

                value = report[column]

                if pd.isna(value):

                    continue

                text = str(value)

                # Large text fields are shown clearly

                if len(text) > 150:

                    st.markdown(
                        f"### {column}"
                    )

                    st.text_area(
                        column,
                        text,
                        height=250,
                        key=f"report_{column}"
                    )

                else:

                    st.markdown(
                        f"**{column}:**"
                    )

                    st.write(
                        text
                    )

        st.divider()

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        st.subheader(
            "⬇️ Export AI Reports"
        )

        download_buttons(
            ai_reports,
            "examguard_ai_reports"
        )


# ============================================================
# 7. DATA EXPORT
# ============================================================

elif menu == "Data Export":

    st.header(
        "📦 Data Export"
    )

    # --------------------------------------------------------
    # ALL DATASETS
    # --------------------------------------------------------

    datasets = {

        "Exam Sessions": sessions,

        "Alerts": alerts,

        "Evidence": evidence,

        "Face Events": face_events,

        "Browser Events": browser_events,

        "AI Reports": ai_reports,

        "Session Clusters": clusters,

        "Cohort Risk Profile": cohort
    }

    selected_dataset = st.selectbox(
        "Select Dataset",
        list(datasets.keys())
    )

    df = datasets[
        selected_dataset
    ]

    st.subheader(
        f"📊 {selected_dataset}"
    )

    # --------------------------------------------------------
    # DATA COUNT
    # --------------------------------------------------------

    if df.empty:

        st.warning(
            f"{selected_dataset} contains no records."
        )

    else:

        st.success(
            f"{len(df)} records available."
        )

        # ----------------------------------------------------
        # DATA TABLE
        # ----------------------------------------------------

        st.dataframe(
            df,
            width="stretch",
            height=500
        )

        # ----------------------------------------------------
        # EXPORT
        # ----------------------------------------------------

        st.subheader(
            "⬇️ Export Dataset"
        )

        file_name = (
            selected_dataset
            .lower()
            .replace(" ", "_")
        )

        download_buttons(
            df,
            f"examguard_{file_name}"
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "ExamGuard | Online Exam Monitoring & Integrity Analytics Platform"
)