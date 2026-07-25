import streamlit as st
import math
import json
import os
from datetime import datetime, time

# Enable full widescreen mode
st.set_page_config(page_title="Automated Attendance Planner", page_icon="📅", layout="wide")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

now_dt = datetime.now()
today_name = now_dt.strftime("%A")
current_time = now_dt.time()

# --- PROFILE & DYNAMIC PERSISTENCE ---
st.sidebar.title("👤 User Profile")

if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"

# Sanitize user input to keep clean filenames
profile_input = st.sidebar.text_input(
    "Enter Profile Name / Roll No:", 
    value=st.session_state.user_id,
    help="Each profile gets its own isolated save file on disk so data isn't shared across students."
)

clean_user_id = "".join(c for c in profile_input.strip().lower() if c.isalnum() or c in ("_", "-")) or "default_user"

if clean_user_id != st.session_state.user_id:
    st.session_state.user_id = clean_user_id
    # Reset session keys so new profile data loads
    for key in ["subjects", "timetable", "target", "today_is_holiday", "holiday_mode", "saturday_swap_day"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

DATA_FILE = f"data_{st.session_state.user_id}.json"

def load_saved_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading saved data: {e}")
    return None

def save_data():
    data = {
        "subjects": st.session_state.subjects,
        "timetable": st.session_state.timetable,
        "target": st.session_state.target,
        "today_is_holiday": st.session_state.today_is_holiday,
        "holiday_mode": st.session_state.holiday_mode,
        "saturday_swap_day": st.session_state.saturday_swap_day,
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass  # Gracefully handle read-only environments when deployed

# --- INITIALIZE STATE WITH PROFILE-SPECIFIC PERSISTENCE ---
saved_data = load_saved_data()

if "subjects" not in st.session_state:
    st.session_state.subjects = saved_data.get("subjects", {}) if saved_data else {
        "Data Structures": {"attended": 18, "total": 20},
        "Database Systems": {"attended": 11, "total": 16},
        "Operating Systems": {"attended": 10, "total": 15},
    }

if "timetable" not in st.session_state:
    st.session_state.timetable = saved_data.get("timetable", {}) if saved_data else {
        "Monday": [
            {"subject": "Data Structures", "start_time": "09:00", "end_time": "10:00"},
            {"subject": "Operating Systems", "start_time": "10:00", "end_time": "11:00"}
        ],
        "Tuesday": [
            {"subject": "Database Systems", "start_time": "11:15", "end_time": "12:15"}
        ],
        "Wednesday": [
            {"subject": "Data Structures", "start_time": "09:00", "end_time": "10:00"},
            {"subject": "Database Systems", "start_time": "14:00", "end_time": "15:00"}
        ],
        "Thursday": [
            {"subject": "Operating Systems", "start_time": "10:00", "end_time": "11:00"}
        ],
        "Friday": [
            {"subject": "Data Structures", "start_time": "09:00", "end_time": "10:00"},
            {"subject": "Operating Systems", "start_time": "11:15", "end_time": "12:15"},
            {"subject": "Database Systems", "start_time": "14:00", "end_time": "15:00"}
        ],
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

# Save state for the profile
save_data()

# --- HELPER FUNCTIONS FOR TIME & MATH ---
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

target = st.slider(
    "Required Minimum Portal Attendance (%)", 
    min_value=50, 
    max_value=90, 
    value=st.session_state.target, 
    step=5,
    key="target_slider"
)
if target != st.session_state.target:
    st.session_state.target = target
    save_data()
    st.rerun()

st.divider()

# --- TABS FOR WORKFLOW ---
tab_landing, tab_today, tab_analytics, tab_manage, tab_timetable = st.tabs([
    "🚀 How to Use",
    "🔥 Daily Check-in",
    "📊 Subject Analytics",
    "⚙️ Manage Subjects", 
    "🗓️ Set Timetable"
])

# ==========================================
# TAB 0: LANDING PAGE & INSTRUCTIONS
# ==========================================
with tab_landing:
    st.markdown("## 👋 Welcome to Your Smart Attendance Planner")
    st.write(
        "Never get caught off-guard by attendance shortages or condonation fees again. "
        "This tool syncs with your college portal figures and calculates **exactly how many classes you can safely skip** "
        "or how many you **must attend back-to-back** to reach your target threshold."
    )
    
    st.divider()
    
    col_guide1, col_guide2 = st.columns([1, 1], gap="large")
    
    with col_guide1:
        st.markdown("### 📌 Step-by-Step Setup")
        
        st.markdown("#### 1️⃣ Enter Your Profile Name / Roll No")
        st.write("Look at the **Sidebar on the left**. Type your Roll Number or Name in the **Profile** field. This creates a personal, private save file (`data_yourname.json`) so your friends' data won't overwrite yours!")
        
        st.markdown("#### 2️⃣ Extract Attendance from College Portal")
        st.markdown("""
        1. **Log in to Portal:** Open your **College Web Portal** in a browser (*do not use the mobile app*).
        2. **Navigate to Calendar:** Go to **Attendance Tab** ➔ **Calendar**.
        3. **Set Custom Date Range:** Set the range **From:** `29 June 2026` **To:** `Current Date`.
        4. **Count Classes Per Subject:** 
           * Use the search bar to filter for each subject name one by one.
           * Count the **Total Classes Conducted** and **Number of Classes Attended**.
           * ⚠️ **Warning:** Be careful **not to mix up Labs and Lectures** while counting!
        5. **Enter in Planner:** Go to the **⚙️ Manage Subjects** tab on this site and enter each subject along with its accurate totals.
        6. **Verify Percentages:** Go to the **📊 Subject Analytics** tab and check if the calculated percentage matches your actual portal percentage for every subject. *If it doesn't match, recheck your counts!*
        """)
        
        st.markdown("#### 3️⃣ Input Your Weekly Timetable")
        st.write("Go to **🗓️ Set Timetable** tab. Select each weekday and add your recurring classes along with their start and end times.")

        st.markdown("#### 4️⃣ Daily One-Click Check-in")
        st.write("Every day, visit **🔥 Daily Check-in**. The app automatically highlights today's active classes. Simply click **✅ Attended** or **❌ Skipped** to update your stats instantly!")

    with col_guide2:
        st.markdown("### 📱 Portal Extraction Checklist")
        st.warning("⚠️ **Important:** Mobile apps often truncate or round attendance counts. Always use the web portal's calendar view for 100% accuracy.")
        
        st.markdown("#### 🛠️ Quick Verification Guide")
        st.info("""
        * **Date Range:** `29 June 2026` to `Today`
        * **Filter Method:** Search subject name in Calendar search bar
        * **Separation Rule:** Keep Lecture counts and Lab counts as separate subjects if they have distinct attendance requirements on your portal.
        * **Double Check:** `(Attended / Total) × 100` in **Subject Analytics** MUST equal your portal's displayed percentage!
        """)
        
        st.markdown(
            "> 💡 **Pro-Tip:** If a class was cancelled or you had a holiday, use the **'Mark Today as Holiday'** toggle on the Daily Check-in tab to pause attendance tracking for that day without messing up your numbers."
        )

# ==========================================
# TAB 1: DAILY CHECK-IN
# ==========================================
with tab_today:
    st.subheader(f"Today's Scheduled Classes ({today_name})")
    
    todays_classes = []
    
    if today_name == "Saturday" and st.session_state.saturday_swap_day != "None":
        if st.session_state.saturday_swap_day in WEEKDAYS:
            todays_classes = st.session_state.timetable.get(st.session_state.saturday_swap_day, [])
            st.info(f"🔁 **Compensation Saturday Active!** Running **{st.session_state.saturday_swap_day}'s** timetable today.")
        elif st.session_state.saturday_swap_day == "Custom":
            todays_classes = st.session_state.timetable.get("Saturday", [])
            st.info("🔁 **Compensation Saturday Active!** Running custom Saturday timetable.")
    else:
        todays_classes = st.session_state.timetable.get(today_name, [])

    todays_classes_sorted = sorted(todays_classes, key=lambda x: parse_time_obj(x.get("start_time", "00:00")))

    is_today_cancelled = st.checkbox("🎉 Mark Today as Holiday / No Classes", value=st.session_state.today_is_holiday)
    if is_today_cancelled != st.session_state.today_is_holiday:
        st.session_state.today_is_holiday = is_today_cancelled
        save_data()
        st.rerun()

    st.divider()

    if st.session_state.holiday_mode:
        st.info("🏖️ **Global Holiday Mode Active!** Attendance tracking is currently paused.")
    elif is_today_cancelled:
        st.info("🥳 **Today marked as No Classes!** No attendance logged or deducted.")
    elif not todays_classes_sorted:
        st.info("🎉 No classes scheduled for today! Enjoy your off day.")
    else:
        grid_cols = st.columns(2, gap="medium")
        
        for idx, item in enumerate(todays_classes_sorted):
            sub_name = item["subject"]
            start_t = parse_time_obj(item.get("start_time", "00:00"))
            end_t = parse_time_obj(item.get("end_time", "23:59"))
            
            s_fmt = format_time_12h(item.get("start_time", "00:00"))
            e_fmt = format_time_12h(item.get("end_time", "00:00"))
            
            if current_time < start_t:
                status_badge = "⏳ UPCOMING"
                border_color = False
            elif start_t <= current_time <= end_t:
                status_badge = "🟢 IN PROGRESS"
                border_color = True
            else:
                status_badge = "🏁 COMPLETED"
                border_color = False

            if sub_name not in st.session_state.subjects:
                continue
                
            sub = st.session_state.subjects[sub_name]
            att = sub["attended"]
            tot = sub["total"]
            
            raw_pct, display_pct, val_num, status_type = calculate_skip_status(att, tot, target)
            
            with grid_cols[idx % 2]:
                with st.container(border=border_color):
                    c_head, c_status = st.columns([3, 2])
                    c_head.markdown(f"### 📖 {sub_name}")
                    c_status.caption(f"Status: **{status_badge}**")
                    
                    st.caption(f"⏰ **Time:** {s_fmt} - {e_fmt} | Portal Attendance: **{display_pct}%**")
                    
                    if status_type == "SAFE":
                        if val_num == 0:
                            st.warning(f"⚠️ **Borderline ({display_pct}%)!** Skips remaining: 0. Attending today is recommended.")
                        else:
                            st.success(f"✅ **Safe to skip today!** You have **{val_num}** safe skip(s) available.")
                    else:
                        st.error(f"🚨 **Do not skip!** Shortage active ({display_pct}%). Must attend next **{val_num}** class(es).")
                    
                    st.write("**Did you attend or skip this class today?**")
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

# ==========================================
# TAB 2: SUBJECT ANALYTICS & SKIPS
# ==========================================
with tab_analytics:
    st.subheader("📊 Subject Attendance & Future Skip Breakdown")
    st.caption(f"Target Threshold: **{target}%** (Official Portal Standard)")
    
    if not st.session_state.subjects:
        st.info("No subjects added yet. Go to 'Manage Subjects' to enter your courses.")
    else:
        for sub_name, data in st.session_state.subjects.items():
            att = data["attended"]
            tot = data["total"]
            raw_pct, display_pct, val_num, status_type = calculate_skip_status(att, tot, target)
            
            with st.container(border=True):
                m1, m2, m3, m4 = st.columns([3, 2, 2, 3])
                
                m1.markdown(f"### 📖 {sub_name}")
                m1.caption(f"Classes: **{att} attended** / **{tot} conducted**")
                
                m2.metric("Portal Attendance", f"{display_pct}%")
                
                if status_type == "SAFE":
                    m3.metric("Future Skips Allowed", f"{val_num} class(es)", delta="Safe", delta_color="normal")
                    m4.success(f"🟢 **Good Standing!** You can skip up to **{val_num}** more class(es) without falling below {target}%.")
                else:
                    m3.metric("Classes Needed", f"{val_num} class(es)", delta="-Shortage", delta_color="inverse")
                    m4.error(f"🔴 **Shortage Active!** You must attend the next **{val_num}** class(es) to reach {target}%.")

# ==========================================
# TAB 3: MANAGE SUBJECTS
# ==========================================
with tab_manage:
    col_input, col_view = st.columns([1, 1], gap="large")
    
    with col_input:
        st.subheader("➕ Add New Subject")
        with st.form("add_new_sub"):
            n_name = st.text_input("Subject Name (e.g. Computer Networks)")
            n_att = st.number_input("Classes Attended so far", min_value=0, value=0)
            n_tot = st.number_input("Total Classes Conducted so far", min_value=1, value=1)
            
            if st.form_submit_button("Add Subject"):
                if n_name.strip():
                    st.session_state.subjects[n_name.strip()] = {"attended": int(n_att), "total": int(n_tot)}
                    save_data()
                    st.rerun()
                else:
                    st.error("Please enter a valid subject name.")

    with col_view:
        st.subheader("📋 Current Subject Records")
        if not st.session_state.subjects:
            st.info("No subjects added yet. Enter your subjects on the left!")
        else:
            subjects_to_delete = []
            
            for sub_name, data in list(st.session_state.subjects.items()):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.markdown(f"**{sub_name}**")
                
                new_att = c2.number_input(f"Attended", min_value=0, value=data["attended"], key=f"m_att_{sub_name}")
                new_tot = c3.number_input(f"Total", min_value=1, value=data["total"], key=f"m_tot_{sub_name}")
                
                if new_att != data["attended"] or new_tot != data["total"]:
                    st.session_state.subjects[sub_name]["attended"] = new_att
                    st.session_state.subjects[sub_name]["total"] = new_tot
                    save_data()
                
                if c4.button("🗑️", key=f"del_sub_{sub_name}"):
                    subjects_to_delete.append(sub_name)
                st.divider()

            if subjects_to_delete:
                for s_del in subjects_to_delete:
                    del st.session_state.subjects[s_del]
                    for day in DAYS:
                        st.session_state.timetable[day] = [
                            item for item in st.session_state.timetable[day] if item["subject"] != s_del
                        ]
                save_data()
                st.rerun()

# ==========================================
# TAB 4: SET WEEKLY TIMETABLE
# ==========================================
with tab_timetable:
    col_tt_input, col_tt_view = st.columns([1, 1], gap="large")
    available_subjects = list(st.session_state.subjects.keys())
    
    with col_tt_input:
        st.subheader("➕ Add Class to Timetable")
        selected_day = st.selectbox("Select Day to Edit", DAYS, index=0)
        
        if not available_subjects:
            st.warning("No subjects available! Add subjects in Step 3 first.")
        else:
            with st.form(key=f"add_class_form_{selected_day}"):
                f_sub = st.selectbox("Select Subject", available_subjects)
                
                t_col1, t_col2 = st.columns(2)
                t_start = t_col1.time_input("Start Time", value=time(9, 0))
                t_end = t_col2.time_input("End Time", value=time(10, 0))
                
                if st.form_submit_button("Add Class to Schedule"):
                    if t_start >= t_end:
                        st.error("End time must be after start time!")
                    else:
                        st.session_state.timetable[selected_day].append({
                            "subject": f_sub,
                            "start_time": t_start.strftime("%H:%M"),
                            "end_time": t_end.strftime("%H:%M")
                        })
                        save_data()
                        st.rerun()

        st.divider()
        st.subheader("⚙️ Schedule Overrides")
        
        swap_option = st.selectbox(
            "Saturday Compensation Day Setup",
            options=["None"] + WEEKDAYS + ["Custom Schedule"],
            index=0 if st.session_state.saturday_swap_day == "None" else 
                  (WEEKDAYS.index(st.session_state.saturday_swap_day) + 1 if st.session_state.saturday_swap_day in WEEKDAYS else 6)
        )
        
        new_swap = "Custom" if swap_option == "Custom Schedule" else swap_option
        if new_swap != st.session_state.saturday_swap_day:
            st.session_state.saturday_swap_day = new_swap
            save_data()
            st.rerun()

    with col_tt_view:
        st.subheader(f"📅 Schedule for **{selected_day}**")
        day_classes = st.session_state.timetable.get(selected_day, [])
        
        day_classes_sorted = sorted(day_classes, key=lambda x: parse_time_obj(x.get("start_time", "00:00")))
        
        if not day_classes_sorted:
            st.info(f"No classes scheduled for {selected_day}.")
        else:
            for idx, item in enumerate(day_classes_sorted):
                s_fmt = format_time_12h(item.get("start_time", "00:00"))
                e_fmt = format_time_12h(item.get("end_time", "00:00"))
                
                c1, c2, c3 = st.columns([3, 3, 1])
                c1.write(f"📖 **{item['subject']}**")
                c2.write(f"⏰ {s_fmt} - {e_fmt}")
                if c3.button("🗑️", key=f"del_class_{selected_day}_{idx}"):
                    orig_idx = day_classes.index(item)
                    st.session_state.timetable[selected_day].pop(orig_idx)
                    save_data()
                    st.rerun()