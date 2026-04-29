import os
import tempfile
import uuid
from datetime import date

import pandas as pd
import streamlit as st

DATA_FILE = "jobs.csv"
INTERNAL_ID_COL = "_job_id"
EXPECTED_COLUMNS = [
    INTERNAL_ID_COL,
    "Job #",
    "Client",
    "Type",
    "Stage",
    "Next Task",
    "Due Date",
    "Assigned To",
    "Notes",
]
PROJECT_TYPES = ["Awning", "Sign", "Canopy", "Other"]
STAGES = ["Survey", "Drafting", "Permitting", "Fabrication", "Install"]


def new_job_id() -> str:
    return str(uuid.uuid4())


def ensure_expected_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in EXPECTED_COLUMNS:
        if column not in df.columns:
            if column == INTERNAL_ID_COL:
                df[column] = ""
            else:
                df[column] = ""
    return df


def ensure_internal_ids(jobs: list[dict]) -> list[dict]:
    seen = set()
    for job in jobs:
        current = str(job.get(INTERNAL_ID_COL, "")).strip()
        if not current or current in seen:
            current = new_job_id()
        job[INTERNAL_ID_COL] = current
        seen.add(current)
    return jobs


def load_jobs() -> tuple[list[dict], str | None]:
    if not os.path.exists(DATA_FILE):
        return [], None

    try:
        df = pd.read_csv(DATA_FILE, dtype=str).fillna("")
        df = ensure_expected_columns(df)
        jobs = df.to_dict("records")
        jobs = ensure_internal_ids(jobs)
        return jobs, None
    except Exception as exc:
        message = f"Could not load {DATA_FILE}: {exc}"
        return [], message


def save_jobs(jobs: list[dict]) -> tuple[bool, str | None]:
    temp_path = None
    try:
        jobs = ensure_internal_ids(jobs)
        df = pd.DataFrame(jobs)
        df = ensure_expected_columns(df)

        data_dir = os.path.dirname(os.path.abspath(DATA_FILE)) or "."
        with tempfile.NamedTemporaryFile("w", delete=False, dir=data_dir, newline="", encoding="utf-8") as tmp:
            temp_path = tmp.name
            df.to_csv(tmp, index=False)
            tmp.flush()
            os.fsync(tmp.fileno())

        os.replace(temp_path, DATA_FILE)
        return True, None
    except Exception as exc:
        message = f"Could not save {DATA_FILE}: {exc}"
        return False, message
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def parse_due_date(due_date_str: str):
    if not due_date_str or not str(due_date_str).strip():
        return None
    due = pd.to_datetime(str(due_date_str).strip(), errors="coerce")
    if pd.isna(due):
        return None
    return due.date()


def due_status(due_date_str: str) -> str:
    due = parse_due_date(due_date_str)
    if due is None:
        return "No valid due date"
    if due < date.today():
        return "Overdue"
    return "Not overdue"


def due_in_next_7_days(due_date_str: str) -> bool:
    due = parse_due_date(due_date_str)
    if due is None:
        return False
    delta = (due - date.today()).days
    return 0 <= delta <= 7


st.set_page_config(page_title="ASC Project Dashboard", layout="wide")
st.title("🏗️ ASC Project Management Dashboard")

if "jobs" not in st.session_state:
    loaded_jobs, load_error = load_jobs()
    if load_error:
        st.error(load_error)
        st.info("CSV could not be loaded. Starting with an empty job list.")
        st.session_state.jobs = []
    else:
        st.session_state.jobs = loaded_jobs
else:
    loaded_jobs, load_error = load_jobs()
    if load_error:
        st.error(load_error)
        st.info("Existing in-memory data was preserved.")

st.session_state.jobs = ensure_internal_ids(st.session_state.jobs)
st.caption(f"Data file: {os.path.abspath(DATA_FILE)}")

with st.expander("➕ Add New Job"):
    with st.form("job_form"):
        job_number = st.text_input("Job Number")
        client = st.text_input("Client Name")
        job_type = st.selectbox("Project Type", PROJECT_TYPES)
        stage = st.selectbox("Stage", STAGES)
        next_task = st.text_input("Next Task")
        due_date = st.date_input("Due Date", value=date.today())
        assigned_to = st.text_input("Assigned To")
        notes = st.text_area("Notes", height=100)
        submit = st.form_submit_button("Add Job")

        if submit:
            clean_job_number = job_number.strip()
            clean_client = client.strip()

            if not clean_job_number or not clean_client:
                st.warning("Job Number and Client Name are required.")
            else:
                existing_job_numbers = {
                    str(job.get("Job #", "")).strip().lower() for job in st.session_state.jobs
                }
                if clean_job_number.lower() in existing_job_numbers:
                    st.warning(f"Job #{clean_job_number} already exists. Use a unique Job Number.")
                else:
                    st.session_state.jobs.append(
                        {
                            INTERNAL_ID_COL: new_job_id(),
                            "Job #": clean_job_number,
                            "Client": clean_client,
                            "Type": job_type,
                            "Stage": stage,
                            "Next Task": next_task.strip(),
                            "Due Date": due_date.strftime("%Y-%m-%d"),
                            "Assigned To": assigned_to.strip(),
                            "Notes": notes.strip(),
                        }
                    )
                    ok, save_error = save_jobs(st.session_state.jobs)
                    if ok:
                        st.success("✅ Job added and saved!")
                    else:
                        st.error(save_error)

jobs_df = pd.DataFrame(st.session_state.jobs)
jobs_df = ensure_expected_columns(jobs_df)

# KPI cards
if jobs_df.empty:
    total_jobs = 0
    overdue_jobs = 0
    due_soon_jobs = 0
else:
    status_series = jobs_df["Due Date"].apply(due_status)
    total_jobs = len(jobs_df)
    overdue_jobs = (status_series == "Overdue").sum()
    due_soon_jobs = jobs_df["Due Date"].apply(due_in_next_7_days).sum()

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Total Jobs", int(total_jobs))
kpi2.metric("Overdue Jobs", int(overdue_jobs))
kpi3.metric("Due in Next 7 Days", int(due_soon_jobs))

st.markdown("### 🔎 Filters")

stage_options = ["All"] + sorted([x for x in jobs_df["Stage"].fillna("").unique().tolist() if x != ""])
assigned_options = ["All"] + sorted(
    [x for x in jobs_df["Assigned To"].fillna("").unique().tolist() if x != ""]
)

f_col1, f_col2, f_col3 = st.columns(3)
selected_stage = f_col1.selectbox("Stage", stage_options)
selected_assigned = f_col2.selectbox("Assigned To", assigned_options)
overdue_filter = f_col3.selectbox(
    "Due Date Status",
    ["All", "Overdue", "Not overdue", "No valid due date"],
)

filtered_df = jobs_df.copy()

if selected_stage != "All":
    filtered_df = filtered_df[filtered_df["Stage"] == selected_stage]

if selected_assigned != "All":
    filtered_df = filtered_df[filtered_df["Assigned To"] == selected_assigned]

if overdue_filter != "All":
    filtered_df = filtered_df[filtered_df["Due Date"].apply(due_status) == overdue_filter]

st.markdown("### 📋 Job List")
visible_df = filtered_df.drop(columns=[INTERNAL_ID_COL], errors="ignore")
if visible_df.empty:
    st.info("No jobs match the selected filters.")
else:
    st.dataframe(visible_df, width="stretch")

csv_data = visible_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download Jobs CSV",
    data=csv_data,
    file_name="jobs_export.csv",
    mime="text/csv",
)

st.markdown("### ✏️ Manage Existing Job")
if jobs_df.empty:
    st.info("No jobs available to edit or delete.")
else:
    manage_df = jobs_df.copy()
    manage_df["_label"] = manage_df.apply(
        lambda r: f"{r['Job #']} — {r['Client']} (ID: {str(r[INTERNAL_ID_COL])[:8]})",
        axis=1,
    )
    selected_label = st.selectbox("Select a job to edit or delete", manage_df["_label"].tolist())
    selected_row = manage_df[manage_df["_label"] == selected_label].iloc[0]
    selected_id = str(selected_row[INTERNAL_ID_COL])

    original_due_date_raw = str(selected_row.get("Due Date", ""))
    parsed_due = parse_due_date(original_due_date_raw)
    due_mode_options = ["Keep existing value", "Set/replace due date"]
    default_due_mode = "Set/replace due date" if parsed_due else "Keep existing value"

    with st.form("edit_job_form"):
        edit_job_number = st.text_input("Edit Job Number", value=str(selected_row["Job #"]))
        edit_client = st.text_input("Edit Client Name", value=str(selected_row["Client"]))
        edit_type = st.selectbox(
            "Edit Project Type",
            PROJECT_TYPES,
            index=PROJECT_TYPES.index(selected_row["Type"]) if selected_row["Type"] in PROJECT_TYPES else 0,
        )
        edit_stage = st.selectbox(
            "Edit Stage",
            STAGES,
            index=STAGES.index(selected_row["Stage"]) if selected_row["Stage"] in STAGES else 0,
        )
        edit_next_task = st.text_input("Edit Next Task", value=str(selected_row["Next Task"]))

        due_mode = st.radio("Due Date", due_mode_options, index=due_mode_options.index(default_due_mode))
        if parsed_due:
            due_input_default = parsed_due
        else:
            due_input_default = date.today()
        edit_due_date = st.date_input("Set Due Date", value=due_input_default)
        if due_mode == "Keep existing value":
            st.caption(f"Current Due Date value will be kept as-is: '{original_due_date_raw}'")

        edit_assigned_to = st.text_input("Edit Assigned To", value=str(selected_row["Assigned To"]))
        edit_notes = st.text_area("Edit Notes", value=str(selected_row["Notes"]), height=100)

        confirm_delete = st.checkbox(
            f"Confirm delete Job #{selected_row['Job #']} for {selected_row['Client']}"
        )
        save_edit = st.form_submit_button("Save Changes")
        delete_job = st.form_submit_button("Delete Job")

        if save_edit:
            clean_job_number = edit_job_number.strip()
            clean_client = edit_client.strip()

            if not clean_job_number or not clean_client:
                st.warning("Job Number and Client Name are required.")
            else:
                duplicate = False
                for job in st.session_state.jobs:
                    if str(job.get(INTERNAL_ID_COL, "")) == selected_id:
                        continue
                    if str(job.get("Job #", "")).strip().lower() == clean_job_number.lower():
                        duplicate = True
                        break

                if duplicate:
                    st.warning(f"Job #{clean_job_number} already exists. Use a unique Job Number.")
                else:
                    target_idx = None
                    for i, job in enumerate(st.session_state.jobs):
                        if str(job.get(INTERNAL_ID_COL, "")) == selected_id:
                            target_idx = i
                            break

                    if target_idx is None:
                        st.error("Could not find the selected job. Please refresh and try again.")
                    else:
                        updated_job = dict(st.session_state.jobs[target_idx])
                        updated_job["Job #"] = clean_job_number
                        updated_job["Client"] = clean_client
                        updated_job["Type"] = edit_type
                        updated_job["Stage"] = edit_stage
                        updated_job["Next Task"] = edit_next_task.strip()
                        if due_mode == "Set/replace due date":
                            updated_job["Due Date"] = edit_due_date.strftime("%Y-%m-%d")
                        else:
                            updated_job["Due Date"] = original_due_date_raw
                        updated_job["Assigned To"] = edit_assigned_to.strip()
                        updated_job["Notes"] = edit_notes.strip()
                        updated_job[INTERNAL_ID_COL] = selected_id

                        st.session_state.jobs[target_idx] = updated_job
                        ok, save_error = save_jobs(st.session_state.jobs)
                        if ok:
                            st.success("✅ Job updated and saved!")
                        else:
                            st.error(save_error)

        if delete_job:
            if not confirm_delete:
                st.warning("Please confirm delete before removing this job.")
            else:
                original_count = len(st.session_state.jobs)
                st.session_state.jobs = [
                    job for job in st.session_state.jobs if str(job.get(INTERNAL_ID_COL, "")) != selected_id
                ]
                if len(st.session_state.jobs) == original_count:
                    st.error("Could not find the selected job to delete. Please refresh and try again.")
                else:
                    ok, save_error = save_jobs(st.session_state.jobs)
                    if ok:
                        st.success("✅ Job deleted and saved!")
                    else:
                        st.error(save_error)
