import streamlit as st
import pandas as pd
import re
#import plotly.express as px
import plotly.graph_objects as go

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
# Normalizers
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
# Matching logic
# --------------------------------------------------
def get_match_column(pre_df, post_df):
    if pre_df["phone_clean"].notna().any() or post_df["phone_clean"].notna().any():
        return "phone_clean"
    elif pre_df["email_clean"].notna().any() or post_df["email_clean"].notna().any():
        return "email_clean"
    else:
        return "name_clean"

# --------------------------------------------------
# Insights Functions
# --------------------------------------------------
def get_completed_both_participants(all_participants, selected_programs):
    return all_participants[
        (all_participants["Program"].isin(selected_programs)) &
        (all_participants["Group"] == "Completed Both")
    ].copy()

def get_completed_both_count(all_participants, selected_programs):
    return len(
        all_participants[
            (all_participants["Program"].isin(selected_programs)) &
            (all_participants["Group"] == "Completed Both")
        ]
    )

def get_pre_post_tables(all_participants, surveys, selected_programs):
    pre_list, post_list = [], []

    completed_both_df = get_completed_both_participants(all_participants, selected_programs)

    for program in selected_programs:
        survey_data = surveys.get(program)
        if survey_data is None:
            continue

        pre_df = survey_data["pre"].copy()
        post_df = survey_data["post"].copy()

        pre_df["phone_clean"] = pre_df["Phone Number"].apply(normalize_phone)
        post_df["phone_clean"] = post_df["Phone Number"].apply(normalize_phone)
        pre_df["email_clean"] = pre_df["Email"].apply(normalize_email)
        post_df["email_clean"] = post_df["Email"].apply(normalize_email)
        pre_df["name_clean"] = pre_df["Name"].apply(normalize_name)
        post_df["name_clean"] = post_df["Name"].apply(normalize_name)

        match_column = get_match_column(pre_df, post_df)

        program_participants = completed_both_df[
            completed_both_df["Program"] == program
        ]

        keys = set(program_participants[match_column].dropna())

        pre_data = pre_df[pre_df[match_column].isin(keys)].add_prefix("Pre-")
        post_data = post_df[post_df[match_column].isin(keys)].add_prefix("Post-")

        pre_data["Program"] = program
        post_data["Program"] = program

        pre_list.append(pre_data)
        post_list.append(post_data)

    return (
        pd.concat(pre_list, ignore_index=True) if pre_list else pd.DataFrame(),
        pd.concat(post_list, ignore_index=True) if post_list else pd.DataFrame()
    )

def get_completed_both_table(all_participants, surveys, selected_programs):
    combined_rows = []
    completed_both_df = get_completed_both_participants(all_participants, selected_programs)

    for _, participant in completed_both_df.iterrows():
        program = participant["Program"]
        survey_data = surveys.get(program)
        if survey_data is None:
            continue

        pre_df = survey_data["pre"].copy()
        post_df = survey_data["post"].copy()

        pre_df["phone_clean"] = pre_df["Phone Number"].apply(normalize_phone)
        post_df["phone_clean"] = post_df["Phone Number"].apply(normalize_phone)
        pre_df["email_clean"] = pre_df["Email"].apply(normalize_email)
        post_df["email_clean"] = post_df["Email"].apply(normalize_email)
        pre_df["name_clean"] = pre_df["Name"].apply(normalize_name)
        post_df["name_clean"] = post_df["Name"].apply(normalize_name)

        match_column = get_match_column(pre_df, post_df)
        key = participant[match_column]

        if pd.isna(key):
            continue

        pre_row = pre_df[pre_df[match_column] == key].head(1)
        post_row = post_df[post_df[match_column] == key].head(1)

        if pre_row.empty or post_row.empty:
            continue

        combined = pd.concat(
            [pre_row.add_prefix("Pre-").reset_index(drop=True),
             post_row.add_prefix("Post-").reset_index(drop=True)],
            axis=1
        )

        combined["Program"] = program
        combined_rows.append(combined)

    return pd.concat(combined_rows, ignore_index=True) if combined_rows else pd.DataFrame()

# --------------------------------------------------
# Visuals Functions
# --------------------------------------------------
def post_rating_donut(df):
    if df.empty or "Post-Rating" not in df.columns:
        return

    ratings = pd.to_numeric(df["Post-Rating"], errors="coerce").dropna()
    counts = ratings.value_counts().sort_index().reindex([1,2,3,4,5], fill_value=0).reset_index()
    counts.columns = ["Rating","Count"]

    fig = px.pie(counts, names="Rating", values="Count", hole=0.5, title="Ratings")
    st.plotly_chart(fig, use_container_width=True)

def pre_gender_pie(df):
    if df.empty or "Pre-Gender:" not in df.columns:
        return

    df = df[df["Pre-Gender:"].isin(["Male","Female"])]
    counts = df["Pre-Gender:"].value_counts().reset_index()
    counts.columns = ["Gender","Count"]

    fig = px.pie(counts, names="Gender", values="Count", title="Gender Distribution")
    st.plotly_chart(fig, use_container_width=True)

def pre_income_group_pie(df):
    if df.empty or "Pre-Income Group" not in df.columns:
        return

    counts = df["Pre-Income Group"].value_counts().reset_index()
    counts.columns = ["Income","Count"]

    fig = px.pie(counts, names="Income", values="Count", title="Income Distribution")
    st.plotly_chart(fig, use_container_width=True)

def program_progress_sankey(summary_df):
    if summary_df.empty:
        return

    labels, sources, targets, values = [], [], [], []
    index_map = {}

    def get_idx(x):
        if x not in index_map:
            index_map[x] = len(labels)
            labels.append(x)
        return index_map[x]

    for _, row in summary_df.iterrows():
        p = row["Program Name"]
        s = row["Started"]
        e = row["Ended"]

        sources += [get_idx(p), get_idx(p)]
        targets += [get_idx(f"{p}-Ended"), get_idx(f"{p}-Dropped")]
        values += [e, s - e]

    fig = go.Figure(go.Sankey(
        node=dict(label=labels),
        link=dict(source=sources, target=targets, value=values)
    ))

    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# Sidebar Upload
# --------------------------------------------------
st.sidebar.title("Dashboard Controls")

if st.sidebar.button("Upload New Program"):
    st.session_state.show_uploads = True

if st.session_state.show_uploads:
    name = st.sidebar.text_input("Program Name", value=st.session_state.survey_name)
    pre = st.sidebar.file_uploader("Pre CSV", type=["csv"])
    post = st.sidebar.file_uploader("Post CSV", type=["csv"])

    if pre and post:
        pre_df = pd.read_csv(pre)
        post_df = pd.read_csv(post)

        for df in [pre_df, post_df]:
            ensure_column(df,"Phone Number")
            ensure_column(df,"Email")
            ensure_column(df,"Name")

            df["phone_clean"] = df["Phone Number"].apply(normalize_phone)
            df["email_clean"] = df["Email"].apply(normalize_email)
            df["name_clean"] = df["Name"].apply(normalize_name)

        st.session_state.surveys[name] = {"pre":pre_df,"post":post_df}
        st.success("Uploaded!")

# --------------------------------------------------
# Main App
# --------------------------------------------------
st.title("Survey Comparison Dashboard")

programs = st.multiselect("Select Programs", list(st.session_state.surveys.keys()))

all_participants = pd.DataFrame()

for p in programs:
    data = st.session_state.surveys[p]
    pre, post = data["pre"], data["post"]

    match = get_match_column(pre, post)

    pre_set = set(pre[match].dropna())
    post_set = set(post[match].dropna())

    def classify(x):
        if x in pre_set and x in post_set:
            return "Completed Both"
        return None

    keys = pd.concat([pre,post])
    keys["Program"] = p
    keys["Group"] = keys[match].apply(classify)

    all_participants = pd.concat([all_participants, keys])

# --------------------------------------------------
# Insights View
# --------------------------------------------------
if not all_participants.empty:
    completed = get_completed_both_table(all_participants, st.session_state.surveys, programs)

    post_rating_donut(completed)
    pre_gender_pie(completed)
    pre_income_group_pie(completed)
