import plotly.express as px
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
################################
#RATING- DONUT CHART
#################################
def post_rating_donut(completed_both_table):
    # Check if table exists
    if completed_both_table.empty:
        st.info("No completed participants to visualize.")
        return

    # Check if column exists
    if "Post-Rating" not in completed_both_table.columns:
        st.warning("Post-Rating column not found.")
        return

    # Clean rating column (ensure numeric)
    ratings = pd.to_numeric(
        completed_both_table["Post-Rating"],
        errors="coerce"
    ).dropna()

    if ratings.empty:
        st.info("No valid ratings found.")
        return

    # Count occurrences of each rating 1-5
    rating_counts = (
        ratings.value_counts()
        .sort_index()
        .reindex([1, 2, 3, 4, 5], fill_value=0)
        .reset_index()
    )

    rating_counts.columns = ["Rating", "Count"]

    # Create Donut Chart
    fig = px.pie(
        rating_counts,
        names="Rating",
        values="Count",
        hole=0.5,
        title="Ratings"
    )

    # Show percentage on chart
    fig.update_traces(
        textinfo="percent",
        hovertemplate=
        "<b>Rating %{label}</b><br>" +
        "Count: %{value}<br>" +
        "Percentage: %{percent}"
    )

    fig.update_layout(
        title_x=0.5
    )

    st.plotly_chart(fig, use_container_width=True)

################################
# ENDED - SANKEY CHART
#################################

def program_progress_sankey(summary_df):
    if summary_df.empty:
        st.info("No program data to visualize.")
        return

    # Remove TOTAL row if exists
    summary_df = summary_df[summary_df["Program Name"] != "TOTAL"].copy()

    if summary_df.empty:
        return

    labels = []
    sources = []
    targets = []
    values = []

    node_index = {}

    def get_index(label):
        if label not in node_index:
            node_index[label] = len(labels)
            labels.append(label)
        return node_index[label]

    for _, row in summary_df.iterrows():
        program = row["Program Name"]
        started = row["Started"]
        ended = row["Ended"]
        dropped = started - ended

        program_node = get_index(program)
        ended_node = get_index(f"{program} - Ended")
        dropped_node = get_index(f"{program} - Dropped")

        # Flow to Ended
        sources.append(program_node)
        targets.append(ended_node)
        values.append(ended)

        # Flow to Dropped
        sources.append(program_node)
        targets.append(dropped_node)
        values.append(dropped)

    fig = go.Figure(go.Sankey(
        node=dict(
            pad=20,
            thickness=20,
            label=labels
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            hovertemplate='Count: %{value}<extra></extra>'
        )
    ))

    fig.update_layout(
        title_text="Program Progress Flow",
        font_size=12
    )

    st.plotly_chart(fig, use_container_width=True)

################################
# line chart for per month
#################################

def pre_post_completed_per_month_line(completed_both_table):
    if completed_both_table.empty:
        st.info("No completed participants to visualize.")
        return

    df = completed_both_table.copy()

    # Check required columns
    if "Post-Start Date (UTC)" not in df.columns:
        st.warning("Post-Start Date (UTC) column not found.")
        return

    if "Pre-Start Date (UTC)" not in df.columns:
        st.warning("Pre-Start Date (UTC) column not found.")
        return

    # Convert to datetime
    df["Post-Start Date (UTC)"] = pd.to_datetime(
        df["Post-Start Date (UTC)"],
        errors="coerce"
    )

    df["Pre-Start Date (UTC)"] = pd.to_datetime(
        df["Pre-Start Date (UTC)"],
        errors="coerce"
    )

    # Drop rows with no valid dates
    df = df.dropna(
        subset=["Post-Start Date (UTC)", "Pre-Start Date (UTC)"],
        how="all"
    )

    if df.empty:
        st.info("No valid dates found.")
        return

    # Create month columns
    df["Post Month"] = df["Post-Start Date (UTC)"].dt.to_period("M").astype(str)
    df["Pre Month"] = df["Pre-Start Date (UTC)"].dt.to_period("M").astype(str)

    # Count per month (Completed = Post)
    post_counts = (
        df.dropna(subset=["Post Month"])
        .groupby("Post Month")
        .size()
        .reset_index(name="Count")
    )
    post_counts["Type"] = "Completed"

    # Count per month (Started = Pre)
    pre_counts = (
        df.dropna(subset=["Pre Month"])
        .groupby("Pre Month")
        .size()
        .reset_index(name="Count")
    )
    pre_counts["Type"] = "Started"

    # Standardize column name
    post_counts = post_counts.rename(columns={"Post Month": "Year-Month"})
    pre_counts = pre_counts.rename(columns={"Pre Month": "Year-Month"})

    # Combine both
    combined = pd.concat([post_counts, pre_counts], ignore_index=True)
    combined = combined.sort_values("Year-Month")

    # DOUBLE LINE CHART
    fig = px.line(
        combined,
        x="Year-Month",
        y="Count",
        color="Type",
        markers=True,
        title="Started vs Completed Participants Per Month",
        color_discrete_map={
            "Completed": "#2563EB",  # Blue
            "Started": "#F97316"     # Orange
        }
    )

    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Number of Participants",
        title_x=0.5
    )

    st.plotly_chart(fig, use_container_width=True)


################################
# Gender Pie chart 
#################################

def pre_gender_pie(completed_both_table):
    if completed_both_table.empty:
        st.info("No completed participants to visualize.")
        return

    if "Pre-Gender:" not in completed_both_table.columns:
        st.warning("'Pre-Gender:' column not found.")
        return

    df = completed_both_table.copy()

    # Keep only Male/Female
    df = df[df["Pre-Gender:"].isin(["Male", "Female"])]

    if df.empty:
        st.info("No valid Male/Female gender data found.")
        return

    gender_counts = df["Pre-Gender:"].value_counts().reset_index()
    gender_counts.columns = ["Gender", "Count"]

    # Pie Chart
    fig = px.pie(
        gender_counts,
        names="Gender",
        values="Count",
        color="Gender",
        color_discrete_map={"Male": "#1f77b4", "Female": "#ff69b4"},  # Blue & Pink
        title="Gender Distribution of Completed Participants (Pre Survey)"
    )

    fig.update_traces(textinfo="percent+label")

    st.plotly_chart(fig, use_container_width=True)

################################
# Income  Pie chart 
#################################


def pre_income_group_pie(completed_both_table):
    if completed_both_table.empty:
        st.info("No completed participants to visualize.")
        return

    if "Pre-Income Group" not in completed_both_table.columns:
        st.warning("'Pre-Income Group' column not found.")
        return

    df = completed_both_table.copy()

    # Drop rows with missing or empty values
    df = df[df["Pre-Income Group"].notna() & (df["Pre-Income Group"] != "")]

    if df.empty:
        st.info("No valid income group data found.")
        return

    income_counts = df["Pre-Income Group"].value_counts().reset_index()
    income_counts.columns = ["Income Group", "Count"]

    # Pie Chart
    fig = px.pie(
        income_counts,
        names="Income Group",
        values="Count",
        title="Income Group Distribution of Completed Participants (Pre Survey)",
        hole=0.3  # optional, makes it a donut
    )

    fig.update_traces(textinfo="percent+label")  # show both %

    st.plotly_chart(fig, use_container_width=True)
