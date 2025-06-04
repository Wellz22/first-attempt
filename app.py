import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="ASC Project Dashboard", layout="wide")
st.title("🏗️ ASC Project Management Dashboard")

if "jobs" not in st.session_state:
    st.session_state.jobs = []

with st.expander("➕ Add New Job"):
    with st.form("job_form"):
        job_number = st.text_input("Job Number")
        client = st.text_input("Client Name")
        job_type = st.selectbox("Project Type", ["Awning", "Sign", "Canopy", "Other"])
        stage = st.selectbox("Stage", ["Survey", "Drafting", "Permitting", "Fabrication", "Install"])
        next_task = st.text_input("Next Task")
        due_date = st.date_input("Due Date", value=date.today())
        assigned_to = st.text_input("Assigned To")
        notes = st.text_area("Notes", height=100)
        submit = st.form_submit_button("Add Job")

        if submit:
            st.session_state.jobs.append({
                "Job #": job_number,
                "Client": client,
                "Type": job_type,
                "Stage": stage,
                "Next Task": next_task,
                "Due Date": due_date.strftime("%Y-%m-%d"),
                "Assigned To": assigned_to,
                "Notes": notes
            })
            st.success("✅ Job added!")

st.markdown("### 📋 Job List")

if st.session_state.jobs:
    df = pd.DataFrame(st.session_state.jobs)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No jobs added yet.")
