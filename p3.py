import streamlit as st
import math
import json
from datetime import datetime, time
from streamlit_gsheets import GSheetsConnection

# Enable widescreen mode
st.set_page_config(page_title="Automated Attendance Planner", page_icon="📅", layout="wide")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

now_dt = datetime.now()
today_name = now_dt.strftime("%A")
current_time = now_dt.time()

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_saved_data(user_id):
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty and "user_id" in df.columns:
            user_row = df[df["user_id"].astype(str) == str(user_id)]
            if not user_row.empty:
                raw_json = user_row.iloc[0]["data"]
                return json.loads(raw_json)
    except Exception:
        pass
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
        df = conn.read(ttl=0)
        json_str = json.dumps(data_payload)
        
        if df is None or df.empty or "user_id" not in df.columns:
            import pandas as pd
            df = pd.DataFrame([{"user_id": str(st.session_state.user_id), "data": json_str}])
        else:
            df["user_id"] = df["user_id"].astype(str)
            curr_id = str(st.session_state.user_id)
            if curr_id in df["user_id"].values:
                df.loc[df["user_id"] == curr_id, "data"] = json_str
            else:
                import pandas as pd
                new_row = pd.DataFrame([{"user_id": curr_id, "data": json_str}])
                df = pd.concat([df, new_row], ignore_index=True)
                
        conn.update(data=df)
    except Exception as e:
        st.error(f"Error saving to Cloud DB: {e}")

# --- PROFILE & DYNAMIC PERSISTENCE ---
st.sidebar.title("👤 User Profile")

if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"

profile_input = st.sidebar.text_input(
    "Enter Profile Name / Roll No:", 
    value=st.session_state.user_id,
    help="Each roll number gets its own cloud save slot."
)

clean_user_id = "".join(c for c in profile_input.strip().lower() if c.isalnum() or c in ("_", "-")) or "default_user"

if clean_user_id != st.session_state.user_id:
    st.session_state.user_id = clean_user_id
    for key in ["subjects", "timetable", "target", "today_is_holiday", "holiday_mode", "saturday_swap_day"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# --- INITIALIZE STATE FROM GOOGLE SHEETS ---
saved_data = load_saved_data(st.session_state.user_id)

if "subjects" not in st.session_state:
    st.session_state.subjects = saved_data.get("subjects", {}) if saved_data else {
        "Data Structures": {"attended": 18, "total": 20},
        "Database Systems": {"attended": 11, "total": 16},
        "Operating Systems": {"attended": 10, "total": 15},
    }

if "timetable" not in st.session_state:
    st.session_state.timetable = saved_data.get("timetable", {}) if saved_data else {
        "Monday": [{"subject": "Data Structures", "start_time": "09:00", "end_time": "10:00"}],
        "Tuesday": [{"subject": "Database Systems", "start_time": "11:15", "end_time": "12:15"}],
        "Wednesday": [{"subject": "Data Structures", "start_time": "09:00", "end_time": "10:00"}],
        "Thursday": [{"subject": "Operating Systems", "start_time": "10:00", "end_time": "11:00"}],
        "Friday": [{"subject": "Data Structures", "start_time": "09:00", "end_time": "10:00"}],
        "Saturday": [],
        "Sunday": []
    }

if "target" not in st.session_state:
    st.session_state.target = saved_data.get("target", 75) if saved_data else 75

if "today_is_holiday" not in st.session_state:
    st.session_state.today_is_holiday = saved_data.get("today_is_holiday", False) if saved_data else False

if "holiday_mode" not in st.session_state:
    st.session_state.holiday_mode = saved_data.get("holiday_mode", False) if saved_data else False

if "saturday_swap_day" not in st.session_state:
    st.session_state.saturday_swap_day = saved_data.get("saturday_swap_day", "None") if saved_data else "None"

def format_time_12h(time_str):
    try:
        return datetime.strptime(time_str, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return time_str

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

# --- SIDEBAR FOR BACKUP & RESTORE ---
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

# --- HEADER SECTION ---
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

with tab_landing:
    st.markdown("## 👋 Welcome to Your Smart Attendance Planner")
    st.write("Never get caught off-guard by attendance shortages again. Cloud database active—your stats auto-save in real time!")

with tab_today:
    st.subheader(f"Today's Scheduled Classes ({today_name})")
    todays_classes = st.session_state.timetable.get(today_name, [])
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
                    st.caption(f"Portal Attendance: **{display_pct}%**")
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
            st.markdown(f"### 📖 {sub_name}: **{display_pct}%** (Attended {data['attended']}/{data['total']})")

with tab_manage:
    st.subheader("➕ Manage Subjects")
    with st.form("add_new_sub"):
        n_name = st.text_input("Subject Name")
        n_att = st.number_input("Classes Attended", min_value=0, value=0)
        n_tot = st.number_input("Total Classes Conducted", min_value=1, value=1)
        if st.form_submit_button("Add Subject"):
            if n_name.strip():
                st.session_state.subjects[n_name.strip()] = {"attended": int(n_att), "total": int(n_tot)}
                save_data()
                st.rerun()

with tab_timetable:
    st.subheader("🗓️ Set Timetable")
    selected_day = st.selectbox("Select Day", DAYS)
    available_subjects = list(st.session_state.subjects.keys())
    if available_subjects:
        with st.form(key=f"tt_form_{selected_day}"):
            f_sub = st.selectbox("Subject", available_subjects)
            t_start = st.time_input("Start Time", value=time(9,0))
            t_end = st.time_input("End Time", value=time(10,0))
            if st.form_submit_button("Add to Schedule"):
                st.session_state.timetable[selected_day].append({
                    "subject": f_sub, "start_time": t_start.strftime("%H:%M"), "end_time": t_end.strftime("%H:%M")
                })
                save_data()
                st.rerun()