import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import pandas as pd

# --- 1. PRO PAGE CONFIG ---
st.set_page_config(
    page_title="EduTrack Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a "Mobile-First" clean look
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
    }
    .stSelectbox, .stDateInput {
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. Setup Connection
conn = st.connection("supabase", type=SupabaseConnection)

# 3. Simple Login Protection
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

# --- NAVIGATION WITH ICONS ---
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

# --- DASHBOARD PAGE (New Visual Home) ---
if page == "🏠 Dashboard":
    st.title("🏫 Classroom Overview")
    
    # Quick Stats Row
    classes_data = get_classes()
    if classes_data.data:
        total_classes = len(classes_data.data)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Classes", total_classes)
        col2.metric("System Status", "Online", "Ready")
        col3.metric("Current Term", "2026-Q1")
        
        st.divider()
        st.info("Select a page from the sidebar to start managing your students.")
    else:
        st.warning("Welcome! Please go to 'First Time Setup' to add your first class.")

# --- PAGE: SETUP ---
if page == "First Time Setup":
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
        
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip().str.lower()
            st.write("Preview of cleaned data:", df.head())
            
            if 'name' not in df.columns:
                st.error("Column 'name' not found.")
            else:
                if st.button("🚀 Import All Students", key="bulk_import_btn"):
                    student_list = []
                    for index, row in df.iterrows():
                        student_list.append({
                            "full_name": row['name'], 
                            "class_id": class_map[target_class],
                            "gender": row.get('gender', 'Not Specified') 
                        })
                    
                    try:
                        conn.table("students").upsert(student_list, on_conflict="full_name, class_id").execute()
                        st.success(f"Successfully imported {len(student_list)} students!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during import: {e}")
    else:
        st.info("Create a class first.")

# --- PAGE: ATTENDANCE ---
elif page == "Take Attendance":
    st.header("📝 Daily Attendance")
    classes_data = get_classes()
    
    if not classes_data.data:
        st.warning("Please add a class first.")
    else:
        # Date & Class Selection
        col1, col2 = st.columns(2)
        selected_date = col1.date_input("Date", datetime.date.today())
        class_map = {c['name']: c['id'] for c in classes_data.data}
        selected_class = col2.selectbox("Class", list(class_map.keys()))
        
        students = get_students(class_map[selected_class])
        
        if not students.data:
            st.info("No students enrolled.")
        else:
            # Prepare data for the table
            df = pd.DataFrame(students.data)
            df = df[['full_name']].copy()
            df['Present'] = True # Default to True
            
            st.write("💡 *Tip: Use the search icon (top right of table) to find a specific name.*")
            
            # THE BETTER WAY: st.data_editor
            # This shows 100 names in a scrollable, searchable box
            edited_df = st.data_editor(
                df,
                column_config={"Present": st.column_config.CheckboxColumn(required=True)},
                disabled=["full_name"], # Prevent editing names
                hide_index=True,
                use_container_width=True
            )

            if st.button("💾 Save Attendance"):
                final_records = []
                for i, row in edited_df.iterrows():
                    final_records.append({
                        "student_id": students.data[i]['id'],
                        "is_present": row['Present'],
                        "date": str(selected_date)
                    })
                
                conn.table("attendance").upsert(final_records).execute()
                st.success(f"Attendance saved for {len(final_records)} students!")

# --- PAGE: SCORES ---
elif page == "Record Scores":
    st.header("🏆 Record Class Scores")
    classes_data = get_classes()
    
    if not classes_data.data:
        st.warning("Please add a class and students first in the 'First Time Setup' page.")
    else:
        # 1. Configuration Inputs
        col1, col2 = st.columns(2)
        score_date = col1.date_input("Date of Activity", datetime.date.today())
        
        categories = ["Quiz", "Exercise", "Midterm", "Assignment", "Presentation", "Group Work", "Class Participation"]
        category = col2.selectbox("Category", categories)
        
        class_map = {c['name']: c['id'] for c in classes_data.data}
        selected_class = st.selectbox("Select Class", list(class_map.keys()))
        
        # Fetch Students
        students_response = get_students(class_map[selected_class])
        students = students_response.data
        
        if not students:
            st.info("No students enrolled in this class yet.")
        else:
            st.write(f"### Entering {category} scores for {len(students)} students")
            st.info("💡 You can **Search** (top right of table) or **Sort** by clicking column headers.")

            # 2. Build the Dataframe for the table
            # This ensures even with 100 students, it stays in one scrollable box
            df_scores = pd.DataFrame(students)
            df_scores = df_scores[['full_name']].rename(columns={'full_name': 'Student Name'})
            df_scores['Score (0-100)'] = 0.0  # Default value

            # 3. The Searchable Data Editor
            edited_df = st.data_editor(
                df_scores,
                column_config={
                    "Score (0-100)": st.column_config.NumberColumn(
                        "Score",
                        help="Enter the points earned (0-100)",
                        min_value=0,
                        max_value=100,
                        step=1,
                        format="%d"
                    )
                },
                disabled=["Student Name"], # User can't change the name here
                hide_index=True,
                use_container_width=True,
                num_rows="fixed" 
            )

            # 4. Save Logic
            if st.button("💾 Save All Scores to Database"):
                score_records = []
                for i, row in edited_df.iterrows():
                    score_records.append({
                        "student_id": students[i]['id'],
                        "category": category,
                        "score_value": row['Score (0-100)'],
                        "recorded_at": str(score_date) # Saving the chosen date
                    })
                
                try:
                    conn.table("scores").insert(score_records).execute()
                    st.success(f"Successfully saved {category} scores for {selected_class}!")
                except Exception as e:
                    st.error(f"Failed to save: {e}")


