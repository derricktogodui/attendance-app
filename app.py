import streamlit as st
from st_supabase_connection import SupabaseConnection

# 1. Setup Connection
conn = st.connection("supabase", type=SupabaseConnection)

# 2. Simple Login Protection
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 Teacher Login")
    password = st.text_input("Enter Admin Password", type="password")
    if st.button("Login"):
        if password == "admin123": # Change this to your preferred password!
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Wrong password")
    st.stop() # Stops the rest of the app from loading

# --- REST OF THE APP (Only shows if logged in) ---

st.sidebar.title("Menu")
page = st.sidebar.radio("Navigate to:", ["First Time Setup", "Take Attendance", "Record Scores"])

st.title("Attendance & Grades Pro")

# --- FIXED QUERY LOGIC ---
# We use .table().select() instead of .query() to avoid the AttributeError
def get_classes():
    return conn.table("classes").select("id, name").execute()

def get_students(class_id):
    return conn.table("students").select("id, full_name").eq("class_id", class_id).execute()

# --- PAGE: SETUP ---
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

    # 2️⃣ Bulk Upload Section
    st.header("2️⃣ Bulk Upload Students")
    classes_data = get_classes()
    
    if classes_data.data:
        class_map = {c['name']: c['id'] for c in classes_data.data}
        target_class = st.selectbox("Upload to which class?", list(class_map.keys()))
        
        uploaded_file = st.file_uploader("Upload CSV or Excel (Must have 'name' and 'gender' columns)", type=['csv', 'xlsx'])
        
        if uploaded_file is not None:
            import pandas as pd
            # Read the file
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write("Preview of data:", df.head())
            
            if st.button("Import All Students"):
                # Prepare data for Supabase
                student_list = []
                for index, row in df.iterrows():
                    student_list.append({
                        "full_name": row['name'], 
                        "class_id": class_map[target_class]
                        # Note: If you want to save gender, we need to add a gender column to your Supabase table first!
                    })
                
                conn.table("students").insert(student_list).execute()
                st.success(f"Successfully imported {len(student_list)} students!")
    else:
        st.info("Create a class first.")
# --- PAGE: ATTENDANCE ---
elif page == "Take Attendance":
    st.header("📝 Take Attendance")
    classes = get_classes()
    if not classes.data:
        st.warning("Please add a class first.")
    else:
        class_map = {c['name']: c['id'] for c in classes.data}
        sel_class = st.selectbox("Class", list(class_map.keys()))
        students = get_students(class_map[sel_class])
        
        if not students.data:
            st.info("No students in this class.")
        else:
            st.write("Check = Present | Uncheck = Absent")
            # Here is your "Mark All" Logic
            cols = st.columns(2)
            if cols[0].button("Select All"):
                st.session_state.all_checked = True
            if cols[1].button("Deselect All"):
                st.session_state.all_checked = False
            
            attendance_results = []
            for s in students.data:
                present = st.checkbox(s['full_name'], value=st.session_state.get('all_checked', True), key=s['id'])
                attendance_results.append({"student_id": s['id'], "is_present": present})
            
            if st.button("Save to Database"):
                conn.table("attendance").upsert(attendance_results).execute()
                st.success("Attendance Recorded!")


