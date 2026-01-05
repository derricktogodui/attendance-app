import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import pandas as pd

# --- 1. PRO PAGE CONFIG ---
st.set_page_config(
    page_title="TrackerAP",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a "Mobile-First" clean look
st.markdown("""
    <style>
    /* Background for the main page */
    .main { background-color: #f5f7f9; }
    
    /* Sidebar Visibility Fix */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e6e9ef;
    }
    
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stMarkdown {
        color: #1e293b !important;
    }

    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stSelectbox, .stDateInput { border-radius: 10px; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #4CAF50; }
    
    /* School Theme Text Styling */
    .school-header {
        text-align: center;
        color: #1e293b;
        font-family: 'Serif';
        margin-bottom: 0px;
    }
    .school-subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.1em;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Setup Connection
conn = st.connection("supabase", type=SupabaseConnection)

# --- 3. HELPER FUNCTIONS ---
def get_classes():
    return conn.table("classes").select("id, name").execute()

def get_students(class_id):
    return conn.table("students").select("id, full_name").eq("class_id", class_id).execute()

def upload_student_photo(file, student_id):
    # SAFETY GATE: If there's no ID, stop immediately
    if not student_id:
        st.error("Internal Error: No Student ID found. Upload cancelled.")
        return None

    file_ext = file.name.split('.')[-1]
    file_path = f"{student_id}.{file_ext}"
    
    # Upload to Storage
    conn.client.storage.from_("student_photos").upload(
        path=file_path,
        file=file.getvalue(),
        file_options={"upsert": "true", "content-type": f"image/{file_ext}"}
    )
    
    public_url = conn.client.storage.from_("student_photos").get_public_url(file_path)
    
    # THE CRITICAL FIX: Ensure .eq("id", student_id) is strictly targeted
    conn.table("students").update({"photo_url": public_url}).eq("id", student_id).execute()
    
    return public_url

def get_all_students():
    return conn.table("students").select("id, full_name, class_id, gender").execute()
# --- 4. CENTERED LOGIN PAGE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # This CSS hides the sidebar only on the login screen
    st.markdown("<style> [data-testid='stSidebar'] { display: none; } </style>", unsafe_allow_html=True)

    # Creating three columns: Left (1), Middle (2), Right (1)
    _, center_col, _ = st.columns([1, 2, 1])

    with center_col:
        st.markdown("<h1 class='school-header'>🎓 TrackerAP</h1>", unsafe_allow_html=True)
        st.markdown("<p class='school-subtitle'>Teacher Management Portal</p>", unsafe_allow_html=True)
        st.divider()
        
        # Wrapping inputs in a container for alignment
        with st.container():
            password = st.text_input("Enter Password", type="password", placeholder="Enter your credentials...")
            if st.button("Sign In to Classroom"):
                if password == "admin123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please contact your administrator.")
        
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.8em; margin-top: 50px;'>© 2026 Academic Tracking System</p>", unsafe_allow_html=True)
    st.stop()

# --- NAVIGATION ---
with st.sidebar:
    st.title("🎓 TrackerAP")
    st.write(f"Logged in as: **Teacher**")
    st.divider()
    page = st.radio(
        "Menu",
        ["Dashboard", "Student Profile", "Take Attendance", "Record Scores", "First Time Setup", "Manage Records"],
        index=0
    )
    st.divider()
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

# --- PAGE: DASHBOARD ---
# --- PAGE: DASHBOARD ---
if page == "Dashboard":
    st.header("Academic Overview")
    
    classes_res = get_classes()
    if not classes_res.data:
        st.warning("Welcome! Please go to 'First Time Setup' to add your first class.")
    else:
        df_classes = pd.DataFrame(classes_res.data)
        # NEW: Allow the teacher to pick one class or see everything
        class_list = {c['name']: c['id'] for c in classes_res.data}
        view_filter = st.selectbox("🔍 Filter View", ["All Classes"] + list(class_list.keys()))

        with st.spinner("Analyzing classroom data..."):
            students_res = conn.table("students").select("*").execute()
            scores_res = conn.table("scores").select("*").execute()
            att_res = conn.table("attendance").select("*").execute()
            
            df_students = pd.DataFrame(students_res.data)
            df_scores = pd.DataFrame(scores_res.data)
            df_att = pd.DataFrame(att_res.data)

            # APPLY CLASS FILTER
            # APPLY CLASS FILTER
            if view_filter != "All Classes":
                target_cid = class_list[view_filter]
                df_students = df_students[df_students['class_id'] == target_cid]
                
                # Get the IDs of students in this specific class
                valid_ids = df_students['id'].tolist()
                
                # THE FIX: Only filter if the dataframes are not empty
                if not df_scores.empty:
                    df_scores = df_scores[df_scores['student_id'].isin(valid_ids)]
                
                if not df_att.empty:
                    df_att = df_att[df_att['student_id'].isin(valid_ids)]

        # STEP 2: CALCULATE METRICS
        total_classes = len(df_classes)
        total_students = len(df_students)
        
        # Gender Logic
        if not df_students.empty and 'gender' in df_students.columns:
            # We use .get() or check values to be safe
            boys = len(df_students[df_students['gender'].str.lower() == 'boy'])
            girls = len(df_students[df_students['gender'].str.lower() == 'girl'])
            gender_text = f"👦 {boys} | 👧 {girls}"
        else:
            gender_text = "No Data"

        # Weekly Attendance Logic
        att_display = "No logs"
        if not df_att.empty:
            df_att['date'] = pd.to_datetime(df_att['date']).dt.date
            one_week_ago = datetime.date.today() - datetime.timedelta(days=7)
            weekly_data = df_att[df_att['date'] >= one_week_ago]
            if not weekly_data.empty:
                att_display = f"{weekly_data['is_present'].mean() * 100:.1f}%"

        # Red Flag Logic
        red_flags = 0
        if not df_scores.empty and not df_att.empty:
            att_means = df_att.groupby('student_id')['is_present'].mean() * 100
            df_scores['pct'] = (df_scores['score_value'] / df_scores['max_score']) * 100
            grade_means = df_scores.groupby('student_id')['pct'].mean()
            combined = pd.merge(att_means, grade_means, on='student_id')
            red_flags = len(combined[(combined['is_present'] < 50) & (combined['pct'] < 50)])

        # STEP 3: DISPLAY METRIC GRID
        st.markdown("""
            <style>
            .metric-container {
                background-color: white; padding: 15px; border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-bottom: 3px solid #4CAF50;
                text-align: center; margin-bottom: 10px;
            }
            .m-label { color: #64748b; font-size: 0.8em; font-weight: bold; text-transform: uppercase; }
            .m-value { color: #1e293b; font-size: 1.4em; font-weight: 800; }
            </style>
        """, unsafe_allow_html=True)

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1: st.markdown(f'<div class="metric-container"><div class="m-label">Total Enrollment</div><div class="m-value">{total_students}</div></div>', unsafe_allow_html=True)
        with m_col2: st.markdown(f'<div class="metric-container"><div class="m-label">Gender Balance</div><div class="m-value">{gender_text}</div></div>', unsafe_allow_html=True)
        with m_col3: st.markdown(f'<div class="metric-container"><div class="m-label">Weekly Presence</div><div class="m-value">{att_display}</div></div>', unsafe_allow_html=True)
        with m_col4: 
            f_color = "#ff4b4b" if red_flags > 0 else "#1e293b"
            st.markdown(f'<div class="metric-container"><div class="m-label">Priority Support</div><div class="m-value" style="color: {f_color};">{red_flags} Students</div></div>', unsafe_allow_html=True)

        s_col1, s_col2, s_col3 = st.columns(3)
        s_col1.metric("Active Classes", total_classes)
        s_col2.metric("System Status", "Online", "Ready")
        s_col3.metric("Current Term", "2026-Q1")
        st.divider()

        # STEP 4: DISPLAY TABS
        if total_students == 0:
            st.info("Classes are ready. Now upload students in 'First Time Setup' to see analytics.")
        else:
            tabs = st.tabs(["Engagement Pulse", "At-Risk/Intervention", "Comparative Class Analytics", "Assessment Analysis", "Semester Outcomes"])
            
            with tabs[0]:
                if not df_att.empty:
                    daily = df_att.groupby('date')['is_present'].mean() * 100
                    st.line_chart(daily)
                else: st.info("No attendance data recorded.")

            with tabs[1]:
                if not df_scores.empty and not df_att.empty:
                    # Logic is already calculated above in red_flags section
                    analytics = pd.merge(att_means, grade_means, on='student_id')
                    analytics = pd.merge(analytics, df_students.set_index('id'), left_index=True, right_index=True)
                    st.scatter_chart(analytics, x="is_present", y="pct", color="#ff4b4b")
                else: st.info("More data needed for correlation analysis.")

            with tabs[2]:
                if not df_scores.empty:
                    merged = pd.merge(df_scores, df_students[['id', 'class_id']], left_on='student_id', right_on='id')
                    merged = pd.merge(merged, df_classes, left_on='class_id', right_on='id')
                    st.bar_chart(merged.groupby('name')['pct'].mean())

            with tabs[3]:
                if not df_scores.empty:
                    st.bar_chart(df_scores.groupby('category')['pct'].mean().sort_values(), horizontal=True)

            with tabs[4]:
                if not df_scores.empty:
                    bins = [0, 50, 75, 100]
                    labels = ['Support Required', 'Progressing', 'Excellence']
                    st.bar_chart(pd.cut(grade_means, bins=bins, labels=labels).value_counts())

# --- PAGE: SETUP ---
elif page == "First Time Setup":
    st.header("1️⃣ Create a Class")
    with st.form("add_class_form"):
        new_class_name = st.text_input("Class Name")
        if st.form_submit_button("Create Class"):
            conn.table("classes").insert({"name": new_class_name}).execute()
            st.success("Class Created!")
            st.rerun()

    st.divider()
    st.header("2️⃣ Bulk Upload Students")
    classes_data = get_classes()
    if classes_data.data:
        class_map = {c['name']: c['id'] for c in classes_data.data}
        target_class = st.selectbox("Upload to which class?", list(class_map.keys()))
        uploaded_file = st.file_uploader("Upload CSV or Excel", type=['csv', 'xlsx'])
        
        if uploaded_file:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip().str.lower()
            if 'name' not in df.columns:
                st.error("Column 'name' not found.")
            else:
                if st.button("Import All Students"):
                    student_list = [{"full_name": r['name'], "class_id": class_map[target_class], "gender": r.get('gender', 'Not Specified')} for _, r in df.iterrows()]
                    try:
                        conn.table("students").upsert(student_list, on_conflict="full_name, class_id").execute()
                        st.success(f"Successfully imported {len(student_list)} students!")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

# --- PAGE: ATTENDANCE ---
elif page == "Take Attendance":
    st.header("Daily Attendance")
    classes_data = get_classes()
    
    if not classes_data.data:
        st.warning("Please add a class in Setup first.")
    else:
        col1, col2 = st.columns(2)
        selected_date = col1.date_input("Date", datetime.date.today())
        class_map = {c['name']: c['id'] for c in classes_data.data}
        selected_class_name = col2.selectbox("Class", list(class_map.keys()))
        class_id = class_map[selected_class_name]
        
        # 1. FETCH STUDENTS & EXISTING RECORDS
        students_res = get_students(class_id)
        existing_att = conn.table("attendance").select("*").eq("date", str(selected_date)).execute()
        
        if not students_res.data:
            st.info("No students enrolled in this class.")
        else:
            # Create a dictionary of existing attendance for quick lookup
            # This is the "History" part
            history_dict = {str(rec['student_id']): rec['is_present'] for rec in existing_att.data}
            
            # Prepare the list for the editor
            # If student has a record in history_dict, use it. Otherwise, default to True.
            display_data = []
            for s in students_res.data:
                s_id = str(s['id'])
                is_present = history_dict.get(s_id, True) # Default to Present
                display_data.append({"ID": s['id'], "Student Name": s['full_name'], "Status": is_present})
            
            df_display = pd.DataFrame(display_data)
            
            # Professional Warning if data already exists
            if existing_att.data:
                st.info(f"Records for {selected_date} already exist. Saving will update the current list.")

            # 2. DATA EDITOR
            edited_df = st.data_editor(
                df_display,
                column_config={
                    "ID": None, # Hide the ID
                    "Status": st.column_config.CheckboxColumn("Present?", default=True)
                },
                disabled=["Student Name"],
                hide_index=True,
                use_container_width=True
            )
            
            # 3. SAVE LOGIC (Using UPSERT to prevent duplicates)
            if st.button("Finalize Attendance"):
                with st.spinner("Syncing records..."):
                    attendance_records = [
                        {
                            "student_id": row['ID'], 
                            "is_present": row['Status'], 
                            "date": str(selected_date)
                        } for _, row in edited_df.iterrows()
                    ]
                    
                    # 'upsert' automatically handles the "don't mark twice" logic
                    # It updates the record if (student_id + date) matches, otherwise inserts.
                    conn.table("attendance").upsert(attendance_records).execute()
                    st.success(f"Successfully recorded attendance for {len(attendance_records)} students.")
# --- PAGE: SCORES ---
elif page == "Record Scores":
    st.header("Assessment")
    classes_data = get_classes()
    
    if not classes_data.data:
        st.warning("Please add a class in Setup first.")
    else:
        # 1. Inputs for the Assessment
        col1, col2, col3 = st.columns([2, 2, 1])
        score_date = col1.date_input("Assessment Date", datetime.date.today())
        category = col2.selectbox("Category", ["Quiz", "Exercise", "Midterm", "Assignment", "Presentation", "Group Work", "Class Participation"])
        max_pts = col3.number_input("Max Points", min_value=1.0, value=10.0, step=1.0)
        
        class_map = {c['name']: c['id'] for c in classes_data.data}
        selected_class = st.selectbox("Select Target Class", list(class_map.keys()))
        class_id = class_map[selected_class]
        
        # 2. Fetch Students & Existing Scores for this specific Date/Category
        students_res = get_students(class_id)
        # Search if scores already exist for this date and category
        existing_scores_res = conn.table("scores").select("*").eq("recorded_at", str(score_date)).eq("category", category).execute()
        
        if not students_res.data:
            st.info("No students enrolled in this class.")
        else:
            # Create a history map: {student_id: score_value}
            history_map = {str(rec['student_id']): rec['score_value'] for rec in existing_scores_res.data}
            
            # Prepare data for the editor
            display_data = []
            for s in students_res.data:
                s_id = str(s['id'])
                # Pre-load existing score if found, else default to 0.0
                current_score = history_map.get(s_id, 0.0)
                display_data.append({
                    "ID": s['id'], 
                    "Student Name": s['full_name'], 
                    "Points Earned": float(current_score)
                })
            
            df_display = pd.DataFrame(display_data)

            # UI Feedback for History
            if existing_scores_res.data:
                st.info(f"Found existing '{category}' records for {score_date}. You can edit and save to update them.")

            st.write(f"### Score Sheet: {category} (Out of {max_pts})")
            
            # 3. Data Editor
            edited_df = st.data_editor(
                df_display,
                column_config={
                    "ID": None, # Hide ID
                    "Points Earned": st.column_config.NumberColumn(
                        label=f"Points / {max_pts}", 
                        min_value=0.0, 
                        max_value=float(max_pts), 
                        format="%.1f"
                    )
                },
                disabled=["Student Name"],
                hide_index=True,
                use_container_width=True
            )
            
            # 4. Save Logic (Using Upsert)
            if st.button("Finalize & Save Scores"):
                with st.spinner("Processing results..."):
                    score_records = []
                    for _, row in edited_df.iterrows():
                        score_records.append({
                            "student_id": row['ID'],
                            "category": category,
                            "score_value": row['Points Earned'],
                            "max_score": max_pts,
                            "recorded_at": str(score_date)
                        })
                    
                    try:
                        # UPSERT prevents double-entries for the same student/category/date
                        conn.table("scores").upsert(score_records).execute()
                        st.success(f"Scores finalized. Class Average: {edited_df['Points Earned'].mean():.1f}/{max_pts}")
                    except Exception as e:
                        st.error(f"Error saving data: {e}")

# --- PAGE: STUDENT PROFILE ---
elif page == "Student Profile":
    # 1. Fetch fresh data
    all_students_res = conn.table("students").select("id, full_name, class_id, gender, photo_url").execute()
    
    if not all_students_res.data:
        st.info("No records found in the Student Directory.")
    else:
        df_all = pd.DataFrame(all_students_res.data)
        
        # THE PROFESSIONAL FIX: Create a dictionary mapping display labels to FULL IDs
        # Format: {"John Doe (Ref: 4cde)": "4cde-full-uuid-here", ...}
        student_map = {
            f"{row['full_name']} (Ref: {str(row['id'])[:5]})": row['id'] 
            for _, row in df_all.iterrows()
        }
        
        selected_label = st.selectbox("📂 Access Student Portfolio", list(student_map.keys()))
        
        # We retrieve the FULL ID from the dictionary using the label
        target_id = student_map[selected_label] 
        
        # Extract the specific row using the full unique ID
        student_row = df_all[df_all['id'] == target_id].iloc[0]
        
        # Lock in variables
        target_gender = student_row['gender']
        target_photo = student_row['photo_url'] if pd.notna(student_row['photo_url']) else None

        # --- IDENTITY CARD ---
        id_col1, id_col2 = st.columns([1, 4])
        
        with id_col1:
            if target_photo:
                import time
                cb = int(time.time())
                st.markdown(f"""
                    <div style="display: flex; justify-content: center; margin-bottom: 10px;">
                        <img src="{target_photo}?v={cb}" style="
                            width: 150px; height: 150px;
                            border-radius: 50%; object-fit: cover; 
                            border: 3px solid #4CAF50; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                        ">
                    </div>
                """, unsafe_allow_html=True)
            else:
                initials = "".join([n[0] for n in student_row['full_name'].split()[:2]]).upper()
                st.markdown(f"""
                    <div style="display: flex; justify-content: center; margin-bottom: 10px;">
                        <div style="width: 150px; height: 150px; background-color: #4CAF50; color: white; 
                            display: flex; align-items: center; justify-content: center; 
                            border-radius: 50%; font-size: 50px; font-weight: bold;
                            box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                            {initials}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            with st.popover("Update Portrait"):
                uploaded_file = st.file_uploader("Upload official photo", type=['png', 'jpg', 'jpeg'])
                if uploaded_file:
                    with st.spinner("Writing to database..."):
                        # Use the target_id we locked in above
                        upload_student_photo(uploaded_file, target_id)
                        st.success("Portfolio updated!")
                        st.rerun()

        with id_col2:
            st.markdown(f"<h1 style='margin-bottom:0; color: #1e293b;'>{student_row['full_name']}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: #64748b; font-size: 1.1em;'>REF: #{str(target_id)[:8].upper()} | GROUP: {target_gender.upper()}</p>", unsafe_allow_html=True)
        
        st.divider()

        # 2. Fetch Individual Data
        # 2. Fetch Individual Data (UPDATED TO USE target_id)
        s_scores = conn.table("scores").select("*").eq("student_id", target_id).execute()
        s_att = conn.table("attendance").select("*").eq("student_id", target_id).execute()
        
        df_s_scores = pd.DataFrame(s_scores.data) if s_scores.data else pd.DataFrame()
        df_s_att = pd.DataFrame(s_att.data) if s_att.data else pd.DataFrame()

        # 3. Top Row Metrics
        col1, col2, col3 = st.columns(3)
        
        # Calculate Personal Attendance %
        att_pct = 0
        if not df_s_att.empty:
            att_pct = df_s_att['is_present'].mean() * 100
        
        # Calculate Personal Grade %
        grade_pct = 0
        if not df_s_scores.empty:
            df_s_scores['pct'] = (df_s_scores['score_value'] / df_s_scores['max_score']) * 100
            grade_pct = df_s_scores['pct'].mean()

        # Determine academic standing for a professional touch
        standing = "High Achiever" if grade_pct >= 75 else "Progressing" if grade_pct >= 50 else "⚠️ Support Needed"

        col1.metric("Cumulative Average", f"{grade_pct:.1f}%")
        col2.metric("Attendance Rate", f"{att_pct:.1f}%")
        col3.metric("Gender Group", target_gender.upper())

        st.info(f"**Academic Standing:** {standing}")
        st.markdown("---")

        # 4. Charts Section
        left_chart, right_chart = st.columns(2)

        with left_chart:
            st.subheader("Performance Momentum")
            if not df_s_scores.empty:
                # Sort by date
                df_s_scores['recorded_at'] = pd.to_datetime(df_s_scores['recorded_at'])
                momentum_df = df_s_scores.sort_values('recorded_at')
                st.line_chart(momentum_df.set_index('recorded_at')['pct'])
                st.caption("Chronological trend of assessment results.")
            else:
                st.info("No assessment data found for this student.")

        with right_chart:
            st.subheader("Mastery by Category")
            if not df_s_scores.empty:
                cat_mastery = df_s_scores.groupby('category')['pct'].mean()
                st.bar_chart(cat_mastery, horizontal=True)
                st.caption("Comparison of strengths across different task types.")
            else:
                st.info("Record scores to view category mastery.")

        st.markdown("---")

        # 5. Raw Data History
        st.subheader("Historical Record")
        tab_h_scores, tab_h_att = st.tabs(["Gradebook Entries", "Attendance Logs"])
        
        with tab_h_scores:
            if not df_s_scores.empty:
                st.dataframe(df_s_scores[['recorded_at', 'category', 'score_value', 'max_score', 'pct']], use_container_width=True, hide_index=True)
            else:
                st.write("No grades recorded.")

        with tab_h_att:
            if not df_s_att.empty:
                # Highlight absences
                df_s_att['Status'] = df_s_att['is_present'].apply(lambda x: "✅ Present" if x else "❌ Absent")
                st.dataframe(df_s_att[['date', 'Status']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.write("No attendance logs found.")

# --- PAGE: MANAGE RECORDS ---
elif page == "Manage Records":
    st.header("Classroom Administration")
    
    classes_res = get_classes()
    if not classes_res.data:
        st.warning("No classes found. Create one in 'First Time Setup'.")
    else:
        # 1. Select Class to Manage
        class_map = {c['name']: c['id'] for c in classes_res.data}
        manage_class_name = st.selectbox("Select Class to Manage", list(class_map.keys()))
        manage_class_id = class_map[manage_class_name]
        
        # 2. Fetch Students
        students_res = conn.table("students").select("*").eq("class_id", manage_class_id).execute()
        
        if not students_res.data:
            st.info("This class has no students.")
            if st.button("Delete Empty Class"):
                conn.table("classes").delete().eq("id", manage_class_id).execute()
                st.success("Class deleted.")
                st.rerun()
        else:
            df_manage = pd.DataFrame(students_res.data)
            
            st.subheader("Student Roster")
            st.caption("Double-click a cell to edit. Click 'Save Changes' to update the database.")
            
            # 3. Data Editor for Editing Names/Gender
            edited_df = st.data_editor(
                df_manage[['id', 'full_name', 'gender']],
                column_config={
                    "id": None, # Hide ID
                    "full_name": st.column_config.TextColumn("Full Name", required=True),
                    "gender": st.column_config.SelectboxColumn("Gender", options=["Boy", "Girl", "Not Specified"])
                },
                use_container_width=True,
                hide_index=True,
                key="roster_editor"
            )

            # SAVE EDITS BUTTON
            if st.button("Save Changes to Roster"):
                with st.spinner("Updating records..."):
                    for _, row in edited_df.iterrows():
                        conn.table("students").update({
                            "full_name": row['full_name'],
                            "gender": row['gender']
                        }).eq("id", row['id']).execute()
                    st.success("Roster updated successfully!")
                    st.rerun()

            st.divider()

            # 4. DELETION SECTION (The "Dangerous" Zone)
            st.subheader("Danger Zone")
            st.warning("Deleting a student will permanently remove all their attendance and score history.")
            
            delete_student_name = st.selectbox("Select Student to Permanently Remove", df_manage['full_name'].tolist())
            delete_id = df_manage[df_manage['full_name'] == delete_student_name]['id'].values[0]

            # Use a Popover to confirm deletion (to prevent accidental clicks)
            with st.popover("Delete Student"):
                st.write(f"Are you absolutely sure you want to delete **{delete_student_name}**?")
                st.write("This action cannot be undone.")
                if st.button("Confirm Permanent Deletion"):
                    # Delete linked records first to satisfy database constraints
                    conn.table("scores").delete().eq("student_id", delete_id).execute()
                    conn.table("attendance").delete().eq("student_id", delete_id).execute()
                    # Finally delete the student
                    conn.table("students").delete().eq("id", delete_id).execute()
                    
                    st.error(f"Record for {delete_student_name} has been erased.")
                    st.rerun()


























