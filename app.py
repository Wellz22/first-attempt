import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="ASC Project Dashboard", layout="wide")

st.title("🏗️ ASC Project Management Dashboard")

# Session state to hold job data
if "jobs" not in st.session_state:
    st.session_state.jobs = []

# --- Job Entry Form ---
with st.expander("➕ Add New Job"):
    with st.form("add_job_form"):
        col1, col2, col3 = st.columns(3)
        job_number = col1.text_input("Job Number")
        client_name = col2.text_input("Client Name")
        project_type = col3.selectbox("Project Type", ["Awning", "Sign", "Canopy", "Other"])

        col4, col5, col6 = st.columns(3)
        stage = col4.selectbox("Stage", ["Survey", "Drafting", "Permitting", "Fabrication", "Install"])
        next_task = col5.text_input("Next Task")
        due_date = col6.date_input("Due Date", value=date.today())

        col7, col8 = st.columns(2)
        assigned_to = col7.text_input("Assigned To")
        notes = col8.text_area("Notes", height=50)

        submitted = st.form_submit_button("Add Job")
        if submitted:
            new_job = {
                "Job #": job_number,
                "Client": client_name,
                "Type": project_type,
                "Stage": stage,
                "Next Task": next_task,
                "Due Date": due_date.strftime("%Y-%m-%d"),
                "Assigned To": assigned_to,
                "Notes": notes,
            }
            st.session_state.jobs.append(new_job)
            st.success("✅ Job added!")

# --- Display Table ---
st.markdown("### 📋 Current Jobs")

if st.session_state.jobs:
    df = pd.DataFrame(st.session_state.jobs)

    # Optional filtering
    col1, col2 = st.columns(2)
    filter_stage = col1.selectbox("Filter by Stage", ["All"] + sorted(df["Stage"].unique().tolist()))
    filter_assignee = col2.selectbox("Filter by Assigned To", ["All"] + sorted(df["Assigned To"].unique().tolist()))

    filtered_df = df.copy()
    if filter_stage != "All":
        filtered_df = filtered_df[filtered_df["Stage"] == filter_stage]
    if filter_assignee != "All":
        filtered_df = filtered_df[filtered_df["Assigned To"] == filter_assignee]

    st.dataframe(filtered_df, use_container_width=True)
else:
    st.info("No jobs added yet. Use the form above to start.")
