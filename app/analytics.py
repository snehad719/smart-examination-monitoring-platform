
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from integrity_scoring import calculate_integrity_score


DATABASE = "data/examguard.db"


# ============================================================
# 1. GENERATE INTEGRITY SCORES FOR ALL VALID SESSIONS
# ============================================================

def generate_integrity_scores():

    connection = sqlite3.connect(DATABASE)

    sessions = pd.read_sql_query(
        """
        SELECT id
        FROM exam_sessions
        WHERE start_time IS NOT NULL
          AND end_time IS NOT NULL
        ORDER BY id
        """,
        connection
    )

    connection.close()

    results = []

    for session_id in sessions["id"]:

        try:
            result = calculate_integrity_score(
                int(session_id)
            )

            results.append(result)

        except ValueError:
            continue

    return pd.DataFrame(results)


# ============================================================
# 2. INTEGRITY SCORE DISTRIBUTION
# ============================================================

def show_score_distribution(df):

    print("\n======================================")
    print("ExamGuard Integrity Score Distribution")
    print("======================================")

    if df.empty:
        print("\nNo valid session data found.")
        return

    print("\nSession Scores:")

    print(
        df[
            [
                "session_id",
                "integrity_score",
                "risk_label"
            ]
        ].to_string(index=False)
    )

    print("\nRisk Distribution:")

    print(
        df["risk_label"]
        .value_counts()
        .to_string()
    )

    print("\nScore Statistics:")

    print(
        df["integrity_score"]
        .describe()
        .round(2)
        .to_string()
    )


def plot_score_distribution(df):

    if df.empty:
        return

    plt.figure(figsize=(8, 5))

    plt.hist(
        df["integrity_score"],
        bins=10,
        edgecolor="black"
    )

    plt.title(
        "Integrity Score Distribution"
    )

    plt.xlabel(
        "Integrity Score"
    )

    plt.ylabel(
        "Number of Sessions"
    )

    plt.tight_layout()

    plt.savefig(
        "data/integrity_score_distribution.png"
    )

    plt.close()

    print(
        "\nChart saved to: "
        "data/integrity_score_distribution.png"
    )


# ============================================================
# 3. GET ALL EVENT DATA
# ============================================================

def get_event_data():

    connection = sqlite3.connect(
        DATABASE
    )

    # Face events
    face_events = pd.read_sql_query(
        """
        SELECT
            session_id,
            event_type,
            start_time AS event_time,
            duration_seconds
        FROM face_events
        ORDER BY session_id
        """,
        connection
    )

    # Browser events
    browser_events = pd.read_sql_query(
        """
        SELECT
            session_id,
            event_type,
            event_time,
            NULL AS duration_seconds
        FROM browser_events
        ORDER BY session_id
        """,
        connection
    )

    connection.close()

    # Combine both event sources
    events = pd.concat(
        [
            face_events,
            browser_events
        ],
        ignore_index=True
    )

    return events


# ============================================================
# 4. EVENT FREQUENCY ANALYSIS
# ============================================================

def show_event_summary(events):

    print("\n======================================")
    print("ExamGuard Event Frequency Analysis")
    print("======================================")

    if events.empty:

        print(
            "\nNo integrity events found."
        )

        return

    print("\nEvent Frequency:")

    print(
        events["event_type"]
        .value_counts()
        .to_string()
    )

    print("\nEvent Details:")

    print(
        events[
            [
                "session_id",
                "event_type",
                "duration_seconds"
            ]
        ].to_string(index=False)
    )


# ============================================================
# 5. EVENT FREQUENCY HEATMAP
# ============================================================

def plot_event_frequency_heatmap():

    events = get_event_data()

    if events.empty:

        print(
            "\nNo event data available "
            "for heatmap."
        )

        return

    events["session_label"] = (
        events["session_id"]
        .fillna("Unknown")
        .astype(str)
    )

    heatmap_data = pd.crosstab(
        events["event_type"],
        events["session_label"]
    )

    print("\nHeatmap Data:")

    print(
        heatmap_data.to_string()
    )

    plt.figure(figsize=(10, 5))

    plt.imshow(
        heatmap_data,
        aspect="auto"
    )

    plt.colorbar(
        label="Event Frequency"
    )

    plt.xticks(
        range(len(heatmap_data.columns)),
        heatmap_data.columns
    )

    plt.yticks(
        range(len(heatmap_data.index)),
        heatmap_data.index
    )

    plt.xlabel(
        "Session ID"
    )

    plt.ylabel(
        "Event Type"
    )

    plt.title(
        "Event Frequency Heatmap"
    )

    plt.tight_layout()

    plt.savefig(
        "data/event_frequency_heatmap.png"
    )

    plt.close()

    print(
        "\nHeatmap saved to: "
        "data/event_frequency_heatmap.png"
    )


# ============================================================
# 6. PREPARE K-MEANS DATA
# ============================================================

def prepare_clustering_data(df):

    events = get_event_data()

    if events.empty:

        event_counts = pd.DataFrame(
            columns=[
                "session_id",
                "event_count"
            ]
        )

    else:

        valid_events = events[
            events["session_id"].notna()
        ].copy()

        if valid_events.empty:

            event_counts = pd.DataFrame(
                columns=[
                    "session_id",
                    "event_count"
                ]
            )

        else:

            event_counts = (
                valid_events
                .groupby("session_id")
                .size()
                .reset_index(
                    name="event_count"
                )
            )

    clustering_df = df[
        [
            "session_id",
            "integrity_score",
            "face_presence_ratio"
        ]
    ].copy()

    clustering_df = clustering_df.merge(
        event_counts,
        on="session_id",
        how="left"
    )

    clustering_df["event_count"] = (
        clustering_df["event_count"]
        .fillna(0)
    )

    return clustering_df


# ============================================================
# 7. K-MEANS SESSION CLUSTERING
# ============================================================

def perform_kmeans_clustering(df):

    print("\n======================================")
    print("ExamGuard K-Means Session Clustering")
    print("======================================")

    clustering_df = prepare_clustering_data(
        df
    )

    if clustering_df.empty:

        print(
            "\nNo session data available "
            "for K-Means clustering."
        )

        return clustering_df

    if len(clustering_df) < 2:

        print(
            "\nAt least 2 sessions are required "
            "for K-Means clustering."
        )

        return clustering_df

    features = [
        "integrity_score",
        "face_presence_ratio",
        "event_count"
    ]

    X = clustering_df[features]

    number_of_clusters = min(
        2,
        len(clustering_df)
    )

    model = KMeans(
        n_clusters=number_of_clusters,
        random_state=42,
        n_init=10
    )

    clustering_df["cluster"] = (
        model.fit_predict(X)
    )

    print("\nClustering Features:")

    print(
        clustering_df[
            [
                "session_id",
                "integrity_score",
                "face_presence_ratio",
                "event_count",
                "cluster"
            ]
        ].to_string(index=False)
    )

    print("\nCluster Centers:")

    centers = pd.DataFrame(
        model.cluster_centers_,
        columns=features
    )

    print(
        centers.round(4).to_string(
            index=True
        )
    )

    clustering_df.to_csv(
        "data/session_clusters.csv",
        index=False
    )

    print(
        "\nCluster results saved to: "
        "data/session_clusters.csv"
    )

    return clustering_df


# ============================================================
# 8. COHORT RISK PROFILING
# ============================================================

def generate_cohort_risk_profile(df):

    print("\n======================================")
    print("ExamGuard Cohort Risk Profiling")
    print("======================================")

    if df.empty:

        print(
            "\nNo session data available "
            "for cohort profiling."
        )

        return pd.DataFrame(
            columns=[
                "risk_level",
                "session_count",
                "percentage"
            ]
        )

    risk_profile = (
        df["risk_label"]
        .value_counts()
        .reindex(
            [
                "Low",
                "Medium",
                "High"
            ],
            fill_value=0
        )
        .reset_index()
    )

    risk_profile.columns = [
        "risk_level",
        "session_count"
    ]

    total_sessions = len(df)

    risk_profile["percentage"] = (
        risk_profile["session_count"]
        / total_sessions
        * 100
    ).round(2)

    print("\nCohort Risk Profile:")

    print(
        risk_profile.to_string(
            index=False
        )
    )

    risk_profile.to_csv(
        "data/cohort_risk_profile.csv",
        index=False
    )

    print(
        "\nCohort profile saved to: "
        "data/cohort_risk_profile.csv"
    )

    return risk_profile


# ============================================================
# 9. MAIN PROGRAM
# ============================================================

if __name__ == "__main__":

    print("\n======================================")
    print("ExamGuard Data Science & Analytics")
    print("======================================")

    # Generate integrity scores
    dataframe = generate_integrity_scores()

    # Score distribution
    show_score_distribution(
        dataframe
    )

    plot_score_distribution(
        dataframe
    )

    # Event analysis
    events = get_event_data()

    show_event_summary(
        events
    )

    # Event heatmap
    plot_event_frequency_heatmap()

    # K-Means clustering
    perform_kmeans_clustering(
        dataframe
    )

    # Cohort risk profiling
    generate_cohort_risk_profile(
        dataframe
    )

    print("\n======================================")
    print("All Analytics Completed Successfully")
    print("======================================")

