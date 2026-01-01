import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import pandas as pd

# --- 1. PRO PAGE CONFIG ---
st.set_page_config(
    page_title="TrackerAp",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a "Mobile-First" clean look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
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
    </style>
    """, unsafe_allow_html=True)

# 2. Setup Connection
conn = st.connection("supabase", type=SupabaseConnection)

# --- 3. HELPER FUNCTIONS (Defined early to avoid errors) ---
def get_classes():
    return conn.table("classes").select("id, name").execute()

def get_students(class_id):
    return conn.table("students").select("id, full_name").eq("class_id", class_id).execute()

# 4. Simple Login Protection
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🎓 EduTrack Pro")
    st.subheader("Please sign in to continue")
    with st.container():
        password = st.text_input("Admin Password", type="password")
        if st.button("Login to Dashboard"):
            if password == "admin123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials.")
    st.stop()

# --- NAVIGATION ---
with st.sidebar:
    st.title("🎓 EduTrack")
    st.write(f"Logged in as: **Teacher**")
    st.divider()
    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "📝 Take Attendance", "🏆 Record Scores", "⚙️ First Time Setup"],
        index=0
    )
    st.divider()
    if st.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()

# --- PAGE: DASHBOARD ---
if page == "🏠 Dashboard":
    st.title("🏫 Classroom Overview")
    classes_data = get_classes()
    
    if classes_data.data:
        total_classes = len(classes_data.data)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Classes", total_classes, help="Active classes in your profile")
        col2.metric("System Status", "Online", "Ready")
        col3.metric("Current Term", "2026-Q1")
        st.divider()
        st.info("Welcome back! Select an action from the sidebar to manage your classes.")
    else:
        st.warning("Welcome! Please go to 'First Time Setup' to add your first class.")

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

