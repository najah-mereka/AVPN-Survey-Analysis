import streamlit as st
import pandas as pd
import re
import plotly.express as px
import Insights
import visuals


# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="Survey Comparison Dashboard",
    layout="wide"
)

# --------------------------------------------------
# Initialize Session State
# --------------------------------------------------
if "surveys" not in st.session_state:
    st.session_state.surveys = {}

if "show_uploads" not in st.session_state:
    st.session_state.show_uploads = False

if "survey_name" not in st.session_state:
    st.session_state.survey_name = "Program 1"

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def normalize_phone(phone):
    if pd.isna(phone):
        return None
    phone = str(phone)
    phone = re.sub(r"\D", "", phone)
    if phone.startswith("0"):
        phone = phone[1:]
    return phone

def normalize_email(email):
    if pd.isna(email):
        return None
    return str(email).strip().lower()

def normalize_name(name):
    if pd.isna(name):
        return None
    return str(name).strip().lower()

def ensure_column(df, column_name):
    if column_name not in df.columns:
        df[column_name] = None

# --------------------------------------------------
# Upload Program
# --------------------------------------------------
st.sidebar.title("Dashboard Controls")
if st.sidebar.button("Upload New Program"):
    st.session_state.show_uploads = True

if st.session_state.show_uploads:
    st.sidebar.subheader("Upload Survey Files")
    st.session_state.survey_name = st.sidebar.text_input(
        "Enter Program Name",
        value=st.session_state.survey_name
    )

    pre_survey_file = st.sidebar.file_uploader("Pre Survey (CSV)", type=["csv"])
    post_survey_file = st.sidebar.file_uploader("Post Survey (CSV)", type=["csv"])

    if pre_survey_file and post_survey_file:
        pre_df = pd.read_csv(pre_survey_file)
        post_df = pd.read_csv(post_survey_file)

        # Clean data
        for df in [pre_df, post_df]:
            ensure_column(df, "Phone Number")
            ensure_column(df, "Email")
            ensure_column(df, "Name")

            df["phone_clean"] = df["Phone Number"].apply(normalize_phone)
            df["email_clean"] = df["Email"].apply(normalize_email)
            df["name_clean"] = df["Name"].apply(normalize_name)

        st.session_state.surveys[st.session_state.survey_name] = {
            "pre": pre_df,
            "post": post_df
        }

        st.success(f"{st.session_state.survey_name} saved successfully!")

# --------------------------------------------------
# Program Selector
# --------------------------------------------------
program_options = list(st.session_state.surveys.keys())
selected_programs = st.multiselect(
    "Select Program(s) to View",
    options=program_options,
    default=program_options
)

# --------------------------------------------------
# Title
# --------------------------------------------------
st.title("Survey Comparison Dashboard")

selected_option = st.sidebar.selectbox(
    "Choose a view",
    ["Overview", "Participants", "Insights"]
)

# --------------------------------------------------
# Initialize KPI counters
# --------------------------------------------------
total_pre_raw = 0
total_post_raw = 0
total_both = 0

all_participants = pd.DataFrame()

# --------------------------------------------------
# Process Each Program Separately
# --------------------------------------------------
for program in selected_programs:
    survey_data = st.session_state.surveys.get(program)
    if survey_data is None:
        continue

    pre_df = survey_data["pre"].copy()
    post_df = survey_data["post"].copy()

    pre_df["Program"] = program
    post_df["Program"] = program

    # Raw participant counts
    total_pre_raw += len(pre_df)
    total_post_raw += len(post_df)

    # Choose matching column (Phone > Email > Name)
    if pre_df["phone_clean"].notna().any() or post_df["phone_clean"].notna().any():
        match_column = "phone_clean"
    elif pre_df["email_clean"].notna().any() or post_df["email_clean"].notna().any():
        match_column = "email_clean"
    else:
        match_column = "name_clean"

    st.write(f"Program **{program}** is matched using: **{match_column.replace('_clean','').capitalize()}**")

    # Keep all rows, do not drop missing
    pre_keys = pre_df[[match_column, "Name", "Email", "Phone Number"]].drop_duplicates()
    post_keys = post_df[[match_column, "Name", "Email", "Phone Number"]].drop_duplicates()

    pre_keys["Program"] = program
    post_keys["Program"] = program

    # Sets for membership, excluding NaN
    pre_set = set(pre_keys[match_column].dropna())
    post_set = set(post_keys[match_column].dropna())

    # Classify participants
    def classify(row):
        key = row[match_column]
        in_pre = key in pre_set if pd.notna(key) else False
        in_post = key in post_set if pd.notna(key) else False

        if in_pre and in_post:
            return "Completed Both"
        else:
            return None  # Ignore Pre Only / Post Only

    all_keys = pd.concat([pre_keys, post_keys], ignore_index=True).drop_duplicates(subset=["Program", match_column])
    all_keys["Group"] = all_keys.apply(classify, axis=1)

    # KPI for Completed Both
    total_both += len(all_keys[all_keys["Group"] == "Completed Both"])

    # Append to global participants table
    all_participants = pd.concat([all_participants, all_keys], ignore_index=True)

# --------------------------------------------------
# KPI Cards
# --------------------------------------------------

# Calculate weighted completion rate
if total_pre_raw > 0:
    completion_rate = (total_both / total_pre_raw) * 100
else:
    completion_rate = 0

col1, col2, col3, col4 = st.columns(4)

col1.metric("Pre Survey", total_pre_raw)
col2.metric("Post Survey", total_post_raw)
col3.metric("Completed Both", total_both)
col4.metric("Completion Rate", f"{completion_rate:.1f}%")

st.divider()




# --------------------------------------------------
# Views
# --------------------------------------------------
if selected_option == "Overview":
    st.subheader("Program Progress Overview")

    if not selected_programs:
        st.info("Select program(s) to view overview.")
    else:
        # -----------------------------
        # 🔹 STARTED / ENDED SUMMARY
        # -----------------------------
        summary_rows = []

        for program in selected_programs:
            survey_data = st.session_state.surveys.get(program)
            if survey_data is None:
                continue

            # 🔹 STARTED = Raw Pre count
            pre_count = len(survey_data["pre"])

            # 🔹 ENDED = Completed Both count
            ended_count = len(
                all_participants[
                    (all_participants["Program"] == program) &
                    (all_participants["Group"] == "Completed Both")
                ]
            )

            summary_rows.append({
                "Program Name": program,
                "Started": pre_count,
                "Ended": ended_count
            })

        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)

            # 🔹 Add TOTAL row
            total_row = pd.DataFrame([{
                "Program Name": "TOTAL",
                "Started": summary_df["Started"].sum(),
                "Ended": summary_df["Ended"].sum()
            }])

            summary_df = pd.concat([summary_df, total_row], ignore_index=True)

            st.dataframe(summary_df, use_container_width=True)

        else:
            st.info("No data available.")

        # -----------------------------
        # 🔹 CATEGORY COUNTS TABLE
        # -----------------------------
        completed_both_table = Insights.get_completed_both_table(
            all_participants,
            st.session_state.surveys,
            selected_programs
        )

        category_table = Insights.get_completed_both_category_counts(
            completed_both_table,
            category_column="Pre-Category"
        )

        if not category_table.empty:
            st.subheader("Completed Both Participants by Pre-Category")
            st.dataframe(category_table, use_container_width=True)
        else:
            st.info("No category data available for Completed Both participants.")




elif selected_option == "Participants":
    st.subheader("Participants")

    if all_participants.empty:
        st.info("Upload and select program(s) to view participants.")
    else:
        # Only show Completed Both participants
        filtered_df = all_participants[all_participants["Group"] == "Completed Both"][
            ["Program", "Name", "Email", "Phone Number"]
        ]

        st.dataframe(filtered_df)

        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="completed_both_participants.csv",
            mime="text/csv"
        )


#######################################
# INSIGHTSSS
#######################################
elif selected_option == "Insights":
    st.subheader("Insights")

    if all_participants.empty or not selected_programs:
        st.info("Upload and select program(s) to view insights.")
    else:
        # Get Pre/Post separately
        pre_data, post_data = Insights.get_pre_post_tables(
            all_participants,
            st.session_state.surveys,
            selected_programs
        )

        # Get Combined Completed Both Table
        completed_both_table = Insights.get_completed_both_table(
            all_participants,
            st.session_state.surveys,
            selected_programs
        )

        # 🎯 Donut Chart
        visuals.post_rating_donut(completed_both_table)

        # 👩‍🦰👨 Gender Pie Chart (Pre Survey)
        visuals.pre_gender_pie(completed_both_table)

        # 💰 Income Group Pie Chart
        visuals.pre_income_group_pie(completed_both_table)


        # DOUBLE LINE chart (Started vs Completed)
        visuals.pre_post_completed_per_month_line(completed_both_table)

        # KPI
        completed_both_count = Insights.get_completed_both_count(
            all_participants,
            selected_programs
        )

        st.metric(
            label="Participants who completed BOTH Pre & Post",
            value=completed_both_count
        )

        # -----------------------------------
        # 🔥 ADD SANKEY HERE
        # -----------------------------------
        summary_rows = []

        for program in selected_programs:
            survey_data = st.session_state.surveys.get(program)
            if survey_data is None:
                continue

            pre_count = len(survey_data["pre"])

            ended_count = len(
                all_participants[
                    (all_participants["Program"] == program) &
                    (all_participants["Group"] == "Completed Both")
                ]
            )

            summary_rows.append({
                "Program Name": program,
                "Started": pre_count,
                "Ended": ended_count
            })

        if summary_rows:
            summary_df = pd.DataFrame(summary_rows)
            visuals.program_progress_sankey(summary_df)

        # -----------------------------------
        # TABLE SELECTOR
        # -----------------------------------
        table_choice = st.selectbox(
            "Select Data to View",
            ["Pre Survey Data", "Post Survey Data", "Completed Both Data"]
        )

        if table_choice == "Pre Survey Data":
            st.dataframe(pre_data)
        elif table_choice == "Post Survey Data":
            st.dataframe(post_data)
        elif table_choice == "Completed Both Data":
            st.dataframe(completed_both_table)
