import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import pandas as pd

# --- 1. PREMIUM PAGE CONFIG ---
st.set_page_config(
    page_title="TrackerAP Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. ADVANCED CSS (The "Pro" Look) ---
st.markdown("""
    <style>
    /* Background color for the whole app */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Custom Card Design */
    div[data-testid="stVerticalBlock"] > div:has(div.card-body) {
        background-color: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }

    /* Professional Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1e293b; /* Dark Navy */
        color: white;
    }
    
    /* Button Styling */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #10b981; /* Emerald Green */
        color: white;
        font-weight: 700;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #059669;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }

    /* Navigation Radio Styling */
    div[data-testid="stSidebarNav"] { padding-top: 2rem; }
    
    /* Metric Styling */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        border-left: 5px solid #3b82f6; /* Blue Accent */
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Connection & Logic Setup
conn = st.connection("supabase", type=SupabaseConnection)

# --- LOGIN PAGE ENHANCEMENT ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Center the login box
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("<h1 style='text-align: center;'>🎓 TrackerAP</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>Secure Educator Portal</p>", unsafe_allow_html=True)
        
        with st.form("login_card"):
            password = st.text_input("Admin Password", type="password")
            if st.form_submit_button("Enter Dashboard"):
                if password == "admin123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Access Denied")
    st.stop()

# --- SIDEBAR ENHANCEMENT ---
with st.sidebar:
    st.markdown("<h2 style='color: white;'>🎓 TrackerAP</h2>", unsafe_allow_html=True)
    st.caption("v2.0 Professional Edition")
    st.divider()
    
    # Modern Radio Navigation
    page = st.radio(
        "MAIN MENU",
        ["🏠 Dashboard", "📝 Take Attendance", "🏆 Record Scores", "⚙️ Setup"],
        index=0
    )
    
    st.divider()
    # Sidebar Micro-Metric
    st.markdown(f"**Current Session**")
    st.caption(f"📅 {datetime.date.today().strftime('%A, %b %d')}")
    
    if st.button("🚪 Log Out"):
        st.session_state.logged_in = False
        st.rerun()
# --- PAGE: DASHBOARD ---
# --- PAGE: DASHBOARD ---
if page == "🏠 Dashboard":
    st.title("📊 Timeless Insight Dashboard")
    
    # 1. Fetch Necessary Data
    with st.spinner("Analyzing classroom data..."):
        students_res = conn.table("students").select("id, full_name, class_id").execute()
        classes_res = conn.table("classes").select("id, name").execute()
        scores_res = conn.table("scores").select("student_id, score_value, max_score, category").execute()
        att_res = conn.table("attendance").select("student_id, is_present").execute()

    if not classes_res.data:
        st.warning("Welcome! Please go to 'First Time Setup' to add your first class.")
    else:
        # --- 2. THE TOP METRICS ROW (Your Design) ---
        total_classes = len(classes_res.data)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Classes", total_classes, help="Active classes in your profile")
        col2.metric("System Status", "Online", "Ready")
        col3.metric("Current Term", "2026-Q1")
        st.divider()

        if not students_res.data:
            st.info("Classes are ready. Now upload students in 'First Time Setup' to see analytics.")
        else:
            # Convert to DataFrames for analysis
            df_students = pd.DataFrame(students_res.data)
            df_classes = pd.DataFrame(classes_res.data)
            df_scores = pd.DataFrame(scores_res.data) if scores_res.data else pd.DataFrame()
            df_att = pd.DataFrame(att_res.data) if att_res.data else pd.DataFrame()

            # --- 3. THE "BIG FOUR" CHART TABS ---
            tab_risk, tab_classes, tab_mastery, tab_projection = st.tabs([
                "🚩 Intervention (At-Risk)", 
                "🏫 Class Comparison", 
                "🎯 Subject Mastery", 
                "📈 Outcome Projection"
            ])

            # --- TAB 1: THE RED FLAG MATRIX ---
            with tab_risk:
                st.subheader("🎯 Student Success Matrix")
                if not df_scores.empty and not df_att.empty:
                    att_stats = df_att.groupby('student_id')['is_present'].mean() * 100
                    df_scores['pct'] = (df_scores['score_value'] / df_scores['max_score']) * 100
                    grade_stats = df_scores.groupby('student_id')['pct'].mean()
                    
                    analytics = pd.merge(att_stats, grade_stats, on='student_id')
                    analytics = pd.merge(analytics, df_students.set_index('id'), left_index=True, right_index=True)
                    analytics.columns = ['Attendance %', 'Average Grade %', 'Student Name', 'class_id']
                    
                    st.write("🔍 **Hover over dots to see names.**")
                    st.scatter_chart(analytics, x="Attendance %", y="Average Grade %", color="#ff4b4b", size="Average Grade %")
                else:
                    st.info("Record more attendance and scores to see the Success Matrix.")

            # --- TAB 2: THE CLASS PULSE ---
            with tab_classes:
                st.subheader("🏫 Class Performance Comparison")
                if not df_scores.empty:
                    df_merged = pd.merge(df_scores, df_students[['id', 'class_id']], left_on='student_id', right_on='id')
                    df_merged = pd.merge(df_merged, df_classes, left_on='class_id', right_on='id')
                    class_perf = df_merged.groupby('name')['pct'].mean()
                    st.bar_chart(class_perf)
                else:
                    st.info("No scores recorded yet.")

            # --- TAB 3: SUBJECT MASTERY ---
            with tab_mastery:
                st.subheader("📖 Performance by Category")
                if not df_scores.empty:
                    cat_perf = df_scores.groupby('category')['pct'].mean().sort_values()
                    st.bar_chart(cat_perf, horizontal=True)
                else:
                    st.info("No category data available.")

            # --- TAB 4: OUTCOME PROJECTION ---
            with tab_projection:
                st.subheader("🔮 End-of-Term Prediction")
                if not df_scores.empty:
                    # Logic: We use the grade_stats we calculated in Tab 1
                    bins = [0, 50, 75, 100]
                    labels = ['At-Risk', 'Passing', 'Excellent']
                    # Ensure grade_stats is a series for pd.cut
                    status_dist = pd.cut(grade_stats, bins=bins, labels=labels).value_counts()
                    st.bar_chart(status_dist)
                else:
                    st.info("No scores available for projection.")

# --- PAGE: SETUP ---
elif page == "⚙️ First Time Setup":
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
                if st.button("🚀 Import All Students"):
                    student_list = [{"full_name": r['name'], "class_id": class_map[target_class], "gender": r.get('gender', 'Not Specified')} for _, r in df.iterrows()]
                    try:
                        conn.table("students").upsert(student_list, on_conflict="full_name, class_id").execute()
                        st.success(f"Successfully imported {len(student_list)} students!")
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")

# --- PAGE: ATTENDANCE ---
elif page == "📝 Take Attendance":
    st.header("📝 Daily Attendance")
    classes_data = get_classes()
    if not classes_data.data:
        st.warning("Please add a class first.")
    else:
        col1, col2 = st.columns(2)
        selected_date = col1.date_input("Date", datetime.date.today())
        class_map = {c['name']: c['id'] for c in classes_data.data}
        selected_class = col2.selectbox("Class", list(class_map.keys()))
        students = get_students(class_map[selected_class])
        
        if not students.data: st.info("No students enrolled.")
        else:
            df = pd.DataFrame(students.data)[['full_name']].copy()
            df['Present'] = True
            edited_df = st.data_editor(df, column_config={"Present": st.column_config.CheckboxColumn(required=True)}, disabled=["full_name"], hide_index=True, use_container_width=True)
            if st.button("💾 Save Attendance"):
                records = [{"student_id": students.data[i]['id'], "is_present": row['Present'], "date": str(selected_date)} for i, row in edited_df.iterrows()]
                conn.table("attendance").upsert(records).execute()
                st.success("Attendance saved!")

# --- PAGE: SCORES ---
elif page == "🏆 Record Scores":
    st.header("🏆 Record Class Scores")
    classes_data = get_classes()
    
    if not classes_data.data:
        st.warning("Please add a class first.")
    else:
        # 1. Configuration Header
        col1, col2, col3 = st.columns([2, 2, 1])
        score_date = col1.date_input("Date", datetime.date.today())
        category = col2.selectbox("Category", ["Quiz", "Exercise", "Midterm", "Assignment", "Presentation", "Group Work", "Class Participation"])
        
        # THIS IS THE FIX: Set the "Out of" value here
        max_pts = col3.number_input("Max Points", min_value=1.0, value=10.0, step=1.0)
        
        class_map = {c['name']: c['id'] for c in classes_data.data}
        selected_class = st.selectbox("Select Class", list(class_map.keys()))
        
        students_res = get_students(class_map[selected_class])
        students = students_res.data
        
        if not students:
            st.info("No students enrolled.")
        else:
            st.write(f"### Recording: {category} (Total: {max_pts} pts)")
            
            # 2. Prepare the Table
            data = []
            for s in students:
                data.append({
                    "ID": s['id'], 
                    "Student Name": s['full_name'], 
                    "Points Earned": 0.0
                })
            
            df_scores = pd.DataFrame(data)

            # 3. Searchable Data Entry
            edited_df = st.data_editor(
                df_scores,
                column_config={
                    "ID": None, # Hide ID
                    "Points Earned": st.column_config.NumberColumn(
                        label=f"Points (max {max_pts})",
                        min_value=0.0, 
                        max_value=float(max_pts), 
                        format="%.1f"
                    )
                },
                disabled=["Student Name"],
                hide_index=True,
                use_container_width=True
            )
            
            # 4. Save Button
            if st.button("💾 Save All Scores"):
                score_records = []
                for _, row in edited_df.iterrows():
                    # Calculate percentage for the database (optional but helpful)
                    percentage = (row['Points Earned'] / max_pts) * 100
                    
                    score_records.append({
                        "student_id": row['ID'],
                        "category": category,
                        "score_value": row['Points Earned'],
                        "max_score": max_pts,
                        "recorded_at": str(score_date)
                    })
                
                try:
                    conn.table("scores").insert(score_records).execute()
                    st.success(f"Successfully recorded {category} scores! Average: {edited_df['Points Earned'].mean():.1f}/{max_pts}")
                except Exception as e:
                    st.error(f"Error saving scores: {e}")



