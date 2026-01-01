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
if page == "First Time Setup":
    st.header("1️⃣ Add a Class")
    with st.form("add_class"):
        new_class = st.text_input("Class Name")
        if st.form_submit_button("Create"):
            conn.table("classes").insert({"name": new_class}).execute()
            st.success("Done!")
            st.rerun()

    st.divider()
    
    classes = get_classes()
    if classes.data:
        st.header("2️⃣ Add Students")
        class_map = {c['name']: c['id'] for c in classes.data}
        sel_c = st.selectbox("Select Class", list(class_map.keys()))
        with st.form("add_student"):
            s_name = st.text_input("Student Name")
            if st.form_submit_button("Enroll"):
                conn.table("students").insert({"full_name": s_name, "class_id": class_map[sel_c]}).execute()
                st.success("Enrolled!")

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
