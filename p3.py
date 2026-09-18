import streamlit as st
import math
import json
from datetime import datetime, time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Enable widescreen mode
st.set_page_config(page_title="Automated Attendance Planner", page_icon="📅", layout="wide")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

now_dt = datetime.now()
today_name = now_dt.strftime("%A")
current_time = now_dt.time()

# --- GOOGLE SHEETS DIRECT CONNECTION (GSPREAD) ---
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds_dict = {
        "type": st.secrets["connections"]["gsheets"]["type"],
        "project_id": st.secrets["connections"]["gsheets"]["project_id"],
        "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
        "private_key": st.secrets["connections"]["gsheets"]["private_key"],
        "client_email": st.secrets["connections"]["gsheets"]["client_email"],
        "client_id": st.secrets["connections"]["gsheets"]["client_id"],
        "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
        "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"],
    }
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def get_worksheet():
    client = get_gspread_client()
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    spreadsheet = client.open_by_url(sheet_url)
    return spreadsheet.sheet1

def load_saved_data(user_id):
    try:
        ws = get_worksheet()
        records = ws.get_all_records()
        if records:
            df = pd.DataFrame(records)
            if "user_id" in df.columns:
                df["user_id"] = df["user_id"].astype(str).str.strip().str.lower()
                user_row = df[df["user_id"] == str(user_id).strip().lower()]
                if not user_row.empty:
                    raw_json = user_row.iloc[0]["data"]
                    return json.loads(raw_json)
    except Exception as e:
        st.sidebar.error(f"Read Error Details: {type(e).__name__} - {str(e)}")
    return None

def save_data():
    if "user_id" not in st.session_state or not st.session_state.user_id:
        return
        
    data_payload = {
        "subjects": st.session_state.subjects,
        "timetable": st.session_state.timetable,
        "target": st.session_state.target,
        "today_is_holiday": st.session_state.today_is_holiday,
        "holiday_mode": st.session_state.holiday_mode,
        "saturday_swap_day": st.session_state.saturday_swap_day,
    }
    
    try:
        ws = get_worksheet()
        records = ws.get_all_records()
        json_str = json.dumps(data_payload)
        curr_id = str(st.session_state.user_id).strip().lower()

        if records:
            df = pd.DataFrame(records)
            df["user_id"] = df["user_id"].astype(str).str.strip().str.lower()
            if curr_id in df["user_id"].values:
                df.loc[df["user_id"] == curr_id, "data"] = json_str
            else:
                new_row = pd.DataFrame([{"user_id": curr_id, "data": json_str}])
                df = pd.concat([df, new_row], ignore_index=True)
        else:
            df = pd.DataFrame([{"user_id": curr_id, "data": json_str}])

        ws.clear()
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        st.toast("Saved to Google Sheets!", icon="☁️")
    except Exception as e:
        st.error(f"Save Error Details: {type(e).__name__} - {str(e)}")

# --- PROFILE & DYNAMIC PERSISTENCE ---
st.sidebar.title("👤 User Profile")

if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"

with st.sidebar.form("profile_form"):
    profile_input = st.text_input("Enter Roll No / Profile:", value=st.session_state.user_id)
    submit_profile = st.form_submit_button("Load / Switch Profile")

if submit_profile:
    clean_id = "".join(c for c in profile_input.strip().lower() if c.isalnum() or c in ("_", "-")) or "default_user"
    st.session_state.user_id = clean_id
    
    fetched = load_saved_data(clean_id)
    if fetched:
        st.session_state.subjects = fetched.get("subjects", {})
        st.session_state.timetable = fetched.get("timetable", {})
        st.session_state.target = fetched.get("target", 75)
        st.session_state.today_is_holiday = fetched.get("today_is_holiday", False)
        st.session_state.holiday_mode = fetched.get("holiday_mode", False)
        st.session_state.saturday_swap_day = fetched.get("saturday_swap_day", "None")
        st.sidebar.success(f"Loaded profile: {clean_id}")
    else:
        st.sidebar.info(f"New profile created: {clean_id}")
    st.rerun()

# --- INITIALIZE SESSION STATE ---
if "subjects" not in st.session_state:
    loaded = load_saved_data(st.session_state.user_id)
    if loaded:
        st.session_state.subjects = loaded.get("subjects", {})
        st.session_state.timetable = loaded.get("timetable", {})
        st.session_state.target = loaded.get("target", 75)
        st.session_state.today_is_holiday = loaded.get("today_is_holiday", False)
        st.session_state.holiday_mode = loaded.get("holiday_mode", False)
        st.session_state.saturday_swap_day = loaded.get("saturday_swap_day", "None")
    else:
        st.session_state.subjects = {
            "Data Structures": {"attended": 18, "total": 20},
            "Database Systems": {"attended": 11, "total": 16},
            "Operating Systems": {"attended": 10, "total": 15},
        }
        st.session_state.timetable = {
            "Monday": [{"subject": "Data Structures", "start_time": "09:00", "end_time": "10:00"}],
            "Tuesday": [{"subject": "Database Systems", "start_time": "11:15", "end_time": "12:15"}],
            "Wednesday": [{"subject": "Data Structures", "start_time": "09:00", "end_time": "10:00"}],
            "Thursday": [{"subject": "Operating Systems", "start_time": "10:00", "end_time": "11:00"}],
            "Friday": [{"subject": "Data Structures", "start_time": "09:00", "end_time": "10:00"}],
            "Saturday": [],
            "Sunday": []
        }
        st.session_state.target = 75
        st.session_state.today_is_holiday = False
        st.session_state.holiday_mode = False
        st.session_state.saturday_swap_day = "None"

def parse_time_obj(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        return time(0, 0)

def calculate_skip_status(attended, total, target_pct):
    if total == 0:
        return 0.0, 0.0, 0, "No Data"
    raw_pct = (attended / total) * 100
    display_pct = round(raw_pct, 2)
    if raw_pct >= target_pct:
        max_skips = math.floor((100 * attended - target_pct * total) / target_pct)
        return raw_pct, display_pct, max(0, max_skips), "SAFE"
    else:
        needed = math.ceil((target_pct * total - 100 * attended) / (100 - target_pct))
        return raw_pct, display_pct, max(0, needed), "SHORTAGE"

# --- SIDEBAR BACKUP & RESTORE ---
st.sidebar.divider()
st.sidebar.title("⚙️ Backup & Restore")

export_data = {
    "subjects": st.session_state.subjects,
    "timetable": st.session_state.timetable,
    "target": st.session_state.target,
    "saturday_swap_day": st.session_state.saturday_swap_day,
}

st.sidebar.download_button(
    label="💾 Export Backup JSON",
    data=json.dumps(export_data, indent=4),
    file_name=f"attendance_backup_{st.session_state.user_id}.json",
    mime="application/json",
    use_container_width=True
)

uploaded_file = st.sidebar.file_uploader("📥 Import Backup JSON", type=["json"])
if uploaded_file is not None:
    try:
        data = json.load(uploaded_file)
        if "subjects" in data and "timetable" in data:
            st.session_state.subjects = data["subjects"]
            st.session_state.timetable = data["timetable"]
            st.session_state.target = data.get("target", 75)
            st.session_state.saturday_swap_day = data.get("saturday_swap_day", "None")
            save_data()
            st.sidebar.success("Loaded backup successfully!")
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error loading file: {e}")

st.sidebar.divider()
holiday_toggle = st.sidebar.toggle("🏖️ Enable Global Holiday Mode", value=st.session_state.holiday_mode)
if holiday_toggle != st.session_state.holiday_mode:
    st.session_state.holiday_mode = holiday_toggle
    save_data()
    st.rerun()

# --- MAIN UI ---
st.title("📅 Automated Attendance Planner")
st.caption(f"Active Profile: **{st.session_state.user_id}** | Today is **{today_name}** ({now_dt.strftime('%b %d, %Y')}) — Current Time: **{now_dt.strftime('%I:%M %p')}**")

target = st.slider("Required Minimum Portal Attendance (%)", min_value=50, max_value=90, value=st.session_state.target, step=5, key="target_slider")
if target != st.session_state.target:
    st.session_state.target = target
    save_data()
    st.rerun()

st.divider()

tab_landing, tab_today, tab_analytics, tab_manage, tab_timetable = st.tabs([
    "🚀 How to Use", "🔥 Daily Check-in", "📊 Subject Analytics", "⚙️ Manage Subjects", "🗓️ Set Timetable"
])

# --- HOW TO USE TAB (EXACT INSTRUCTIONS) ---
with tab_landing:
    st.markdown("## 👋 Welcome to Your Smart Attendance Planner")
    st.write("Never get caught off-guard by attendance shortages again. Cloud database active—your stats auto-save in real time across sessions!")

    st.divider()

    st.markdown("### 📌 Quick Start Guide")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Step 1: Profile Setup**\nEnter your Roll Number in the sidebar and click **Load / Switch Profile** to create or retrieve your cloud database save.")
    with col2:
        st.warning("**Step 2: Initialize Subjects**\nHead over to **⚙️ Manage Subjects** to input your current attended and total conducted classes directly from your college portal.")
    with col3:
        st.success("**Step 3: Track Daily**\nUse **🔥 Daily Check-in** to mark classes as **Attended** or **Skipped** with a single click after every class.")

    st.divider()

    with st.expander("🗓️ Setting Up & Managing Your Weekly Timetable"):
        st.markdown("""
        * Navigate to the **🗓️ Set Timetable** tab.
        * Select a day of the week from the dropdown menu.
        * Pick an added subject, set its start/end time, and click **Add to Schedule**.
        * **Daily Auto-Filtering:** Your **🔥 Daily Check-in** tab automatically pulls and displays only today's scheduled classes sorted chronologically by start time.
        * **Saturday Timetable Swap:** If your college operates a Saturday swap rule (e.g., Saturday follows a Monday schedule), configure the swap selector on the **Set Timetable** tab to automatically map the correct timetable.
        """)

    with st.expander("📊 Understanding Attendance Percentage & Bunk Calculations"):
        st.markdown("""
        * **Exact Calculation Logic:** Your attendance is tracked down to precise decimal values matching the official college portal without artificial ceiling rounding.
        * **Minimum Portal Target:** Adjust the slider at the top (default 75%) to set your target threshold.
        * **SAFE Status:** Tells you the exact maximum number of consecutive classes you can safely skip while staying strictly at or above your target percentage.
        * **SHORTAGE Status:** Calculates the exact number of consecutive upcoming classes you must attend without skipping to recover back to your target percentage.
        """)

    with st.expander("🏖️ Handling Holidays, Cancellations & Backups"):
        st.markdown("""
        * **Mark Today as Holiday:** If classes are unexpectedly canceled today, check the holiday box in **🔥 Daily Check-in** to hide today's class cards without modifying your recorded stats.
        * **Global Holiday Mode:** Toggle in the sidebar during mid-sems, semester breaks, or vacations to pause daily schedule prompts.
        * **Cloud Sync & Local Backups:** All updates save directly to Google Sheets under your Roll Number. You can also export or import a local JSON backup anytime via the sidebar **Backup & Restore** section.
        """)

with tab_today:
    effective_today = today_name
    if today_name == "Saturday" and st.session_state.saturday_swap_day != "None":
        effective_today = st.session_state.saturday_swap_day
        st.info(f"🔄 Saturday Schedule Swapped: Following **{effective_today}** Timetable")

    st.subheader(f"Today's Scheduled Classes ({effective_today})")
    todays_classes = st.session_state.timetable.get(effective_today, [])
    todays_classes_sorted = sorted(todays_classes, key=lambda x: parse_time_obj(x.get("start_time", "00:00")))

    is_today_cancelled = st.checkbox("🎉 Mark Today as Holiday / No Classes", value=st.session_state.today_is_holiday)
    if is_today_cancelled != st.session_state.today_is_holiday:
        st.session_state.today_is_holiday = is_today_cancelled
        save_data()
        st.rerun()

    st.divider()

    if not todays_classes_sorted or is_today_cancelled or st.session_state.holiday_mode:
        st.info("🎉 No active classes scheduled for today!")
    else:
        grid_cols = st.columns(2, gap="medium")
        for idx, item in enumerate(todays_classes_sorted):
            sub_name = item["subject"]
            if sub_name not in st.session_state.subjects:
                continue
            sub = st.session_state.subjects[sub_name]
            raw_pct, display_pct, val_num, status_type = calculate_skip_status(sub["attended"], sub["total"], target)
            
            with grid_cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"### 📖 {sub_name}")
                    st.caption(f"Time: {item.get('start_time')} - {item.get('end_time')} | Portal Attendance: **{display_pct}%**")
                    if status_type == "SAFE":
                        st.success(f"🟢 SAFE: You can skip **{val_num}** class(es)")
                    elif status_type == "SHORTAGE":
                        st.error(f"🔴 SHORTAGE: Attend next **{val_num}** class(es)")
                    
                    btn_att, btn_skip = st.columns(2)
                    if btn_att.button("✅ Attended", key=f"att_{idx}", use_container_width=True):
                        st.session_state.subjects[sub_name]["attended"] += 1
                        st.session_state.subjects[sub_name]["total"] += 1
                        save_data()
                        st.rerun()
                    if btn_skip.button("❌ Skipped", key=f"skip_{idx}", use_container_width=True):
                        st.session_state.subjects[sub_name]["total"] += 1
                        save_data()
                        st.rerun()

with tab_analytics:
    st.subheader("📊 Subject Attendance Breakdown")
    for sub_name, data in st.session_state.subjects.items():
        raw_pct, display_pct, val_num, status_type = calculate_skip_status(data["attended"], data["total"], target)
        with st.container(border=True):
            cols = st.columns([3, 2, 2])
            with cols[0]:
                st.markdown(f"### 📖 {sub_name}")
                st.caption(f"Attended: **{data['attended']}** / Total: **{data['total']}**")
            with cols[1]:
                st.metric("Portal Attendance", f"{display_pct}%", delta=f"{round(display_pct - target, 2)}% vs target")
            with cols[2]:
                if status_type == "SAFE":
                    st.success(f"Safe Skips Available: **{val_num}**")
                elif status_type == "SHORTAGE":
                    st.error(f"Classes Needed: **{val_num}**")

with tab_manage:
    st.subheader("⚙️ Manage Subjects")
    
    with st.form("add_new_sub"):
        st.markdown("#### ➕ Add New Subject")
        n_name = st.text_input("Subject Name")
        n_att = st.number_input("Classes Attended", min_value=0, value=0)
        n_tot = st.number_input("Total Classes Conducted", min_value=1, value=1)
        if st.form_submit_button("Add Subject"):
            if n_name.strip():
                st.session_state.subjects[n_name.strip()] = {"attended": int(n_att), "total": int(n_tot)}
                save_data()
                st.rerun()

    st.divider()
    st.markdown("#### ✏️ Update / Delete Existing Subjects")
    for s_name in list(st.session_state.subjects.keys()):
        with st.expander(f"Edit {s_name}"):
            c1, c2, c3 = st.columns([2, 2, 1])
            new_att = c1.number_input(f"Attended ({s_name})", min_value=0, value=st.session_state.subjects[s_name]["attended"], key=f"edit_att_{s_name}")
            new_tot = c2.number_input(f"Total ({s_name})", min_value=1, value=st.session_state.subjects[s_name]["total"], key=f"edit_tot_{s_name}")
            
            if c3.button("Save Changes", key=f"save_{s_name}"):
                st.session_state.subjects[s_name]["attended"] = int(new_att)
                st.session_state.subjects[s_name]["total"] = int(new_tot)
                save_data()
                st.rerun()
                
            if c3.button("🗑️ Delete", key=f"del_{s_name}"):
                del st.session_state.subjects[s_name]
                save_data()
                st.rerun()

with tab_timetable:
    st.subheader("🗓️ Set Timetable")
    
    swap_choice = st.selectbox("Saturday Timetable Order Swap:", ["None"] + WEEKDAYS, index=["None"] + WEEKDAYS.index(st.session_state.saturday_swap_day) if st.session_state.saturday_swap_day in WEEKDAYS else 0)
    if swap_choice != st.session_state.saturday_swap_day:
        st.session_state.saturday_swap_day = swap_choice
        save_data()
        st.rerun()

    st.divider()
    
    selected_day = st.selectbox("Select Day to Manage Schedule:", DAYS)
    available_subjects = list(st.session_state.subjects.keys())
    
    if available_subjects:
        with st.form(key=f"tt_form_{selected_day}"):
            f_sub = st.selectbox("Subject", available_subjects)
            t_start = st.time_input("Start Time", value=time(9,0))
            t_end = st.time_input("End Time", value=time(10,0))
            if st.form_submit_button("Add Class to Schedule"):
                st.session_state.timetable[selected_day].append({
                    "subject": f_sub, "start_time": t_start.strftime("%H:%M"), "end_time": t_end.strftime("%H:%M")
                })
                save_data()
                st.rerun()
    else:
        st.warning("Please add at least one subject in 'Manage Subjects' before setting up the timetable.")

    st.markdown(f"### Current Schedule for **{selected_day}**")
    day_schedule = st.session_state.timetable.get(selected_day, [])
    if not day_schedule:
        st.info("No classes scheduled for this day.")
    else:
        for idx, item in enumerate(day_schedule):
            c1, c2 = st.columns([4, 1])
            c1.write(f"📖 **{item['subject']}** ({item['start_time']} - {item['end_time']})")
            if c2.button("Remove", key=f"rem_{selected_day}_{idx}"):
                st.session_state.timetable[selected_day].pop(idx)
                save_data()
                st.rerun()