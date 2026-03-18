import pandas as pd

# --------------------------------------------------
# Normalizers (same behavior as app.py)
# --------------------------------------------------
def normalize_phone(phone):
    if pd.isna(phone):
        return None
    phone = str(phone)
    phone = "".join(filter(str.isdigit, phone))
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


# --------------------------------------------------
# Decide match column EXACTLY like app.py
# --------------------------------------------------
def get_match_column(pre_df, post_df):
    if pre_df["phone_clean"].notna().any() or post_df["phone_clean"].notna().any():
        return "phone_clean"
    elif pre_df["email_clean"].notna().any() or post_df["email_clean"].notna().any():
        return "email_clean"
    else:
        return "name_clean"


# --------------------------------------------------
# Source of truth: Completed Both participants
# --------------------------------------------------
def get_completed_both_participants(all_participants, selected_programs):
    return all_participants[
        (all_participants["Program"].isin(selected_programs)) &
        (all_participants["Group"] == "Completed Both")
    ].copy()


# --------------------------------------------------
# KPI count (EXACT match with app.py)
# --------------------------------------------------
def get_completed_both_count(all_participants, selected_programs):
    return len(
        all_participants[
            (all_participants["Program"].isin(selected_programs)) &
            (all_participants["Group"] == "Completed Both")
        ]
    )


# --------------------------------------------------
# Get Pre/Post tables (Completed Both ONLY)
# --------------------------------------------------
def get_pre_post_tables(all_participants, surveys, selected_programs):
    pre_list = []
    post_list = []

    completed_both_df = get_completed_both_participants(
        all_participants, selected_programs
    )

    for program in selected_programs:
        survey_data = surveys.get(program)
        if survey_data is None:
            continue

        pre_df = survey_data["pre"].copy()
        post_df = survey_data["post"].copy()

        # Ensure clean columns exist
        pre_df["phone_clean"] = pre_df["Phone Number"].apply(normalize_phone)
        post_df["phone_clean"] = post_df["Phone Number"].apply(normalize_phone)
        pre_df["email_clean"] = pre_df["Email"].apply(normalize_email)
        post_df["email_clean"] = post_df["Email"].apply(normalize_email)
        pre_df["name_clean"] = pre_df["Name"].apply(normalize_name)
        post_df["name_clean"] = post_df["Name"].apply(normalize_name)

        match_column = get_match_column(pre_df, post_df)

        program_participants = completed_both_df[
            completed_both_df["Program"] == program
        ].copy()

        if program_participants.empty:
            continue

        keys = set(program_participants[match_column].dropna())

        pre_data = pre_df[pre_df[match_column].isin(keys)].copy()
        post_data = post_df[post_df[match_column].isin(keys)].copy()

        pre_data = pre_data.add_prefix("Pre-")
        post_data = post_data.add_prefix("Post-")

        pre_data["Program"] = program
        post_data["Program"] = program

        pre_list.append(pre_data)
        post_list.append(post_data)

    pre_final = pd.concat(pre_list, ignore_index=True) if pre_list else pd.DataFrame()
    post_final = pd.concat(post_list, ignore_index=True) if post_list else pd.DataFrame()

    return pre_final, post_final


# --------------------------------------------------
# Combined Pre + Post table (EXACT app.py logic)
# --------------------------------------------------
def get_completed_both_table(all_participants, surveys, selected_programs):
    combined_rows = []

    completed_both_df = get_completed_both_participants(
        all_participants, selected_programs
    )

    for _, participant in completed_both_df.iterrows():
        program = participant["Program"]
        survey_data = surveys.get(program)
        if survey_data is None:
            continue

        pre_df = survey_data["pre"].copy()
        post_df = survey_data["post"].copy()

        # Clean columns
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

        pre_row = pre_row.add_prefix("Pre-")
        post_row = post_row.add_prefix("Post-")

        combined = pd.concat(
            [pre_row.reset_index(drop=True), post_row.reset_index(drop=True)],
            axis=1
        )
        combined["Program"] = program

        combined_rows.append(combined)

    if combined_rows:
        return pd.concat(combined_rows, ignore_index=True)

    return pd.DataFrame()





# --------------------------------------------------
# Get Completed Both counts per Pre-Category
# --------------------------------------------------
def get_completed_both_category_counts(completed_both_table, category_column="Pre-Category"):
    """
    Returns a dataframe of counts per category per program, with a TOTAL row at the bottom.
    """
    if completed_both_table.empty or category_column not in completed_both_table.columns:
        return pd.DataFrame()

    df = completed_both_table.copy()

    # Remove missing or empty category
    df = df[df[category_column].notna() & (df[category_column] != "")]

    if df.empty:
        return pd.DataFrame()

    # Group by Program and Category
    counts = (
        df.groupby(["Program", category_column])
        .size()
        .reset_index(name="Count")
    )

    # Pivot to have categories as columns
    pivot_df = counts.pivot(index="Program", columns=category_column, values="Count").fillna(0)

    # Add TOTAL row
    total_row = pivot_df.sum().to_frame().T
    total_row.index = ["TOTAL"]

    pivot_df = pd.concat([pivot_df, total_row], ignore_index=False).reset_index()
    pivot_df = pivot_df.rename(columns={"index": "Program Name"})

    return pivot_df
