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
    st.header("1️⃣ Create a New Class")
    with st.form("add_class_form", clear_on_submit=True):
        new_class_name = st.text_input("Class Name (e.g., Computer Science 101)")
        if st.form_submit_button("Create Class"):
            if new_class_name:
                conn.table("classes").insert({"name": new_class_name}).execute()
                st.success(f"Class '{new_class_name}' added!")
                st.rerun()
            else:
                st.error("Please enter a name.")

    st.divider()
    
    # Check if classes exist before allowing student entry
    classes_data = get_classes()
    if classes_data.data:
        st.header("2️⃣ Enroll Students")
        # Create a dictionary to map names to IDs
        class_options = {c['name']: c['id'] for c in classes_data.data}
        selected_class = st.selectbox("Select Class", list(class_options.keys()))
        
        with st.form("add_student_form", clear_on_submit=True):
            student_name = st.text_input("Student Full Name")
            if st.form_submit_button("Enroll Student"):
                if student_name:
                    conn.table("students").insert({
                        "full_name": student_name, 
                        "class_id": class_options[selected_class]
                    }).execute()
                    st.success(f"Added {student_name} to {selected_class}!")
                else:
                    st.error("Please enter a student name.")
    else:
        st.info("Add your first class above to start enrolling students.")

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

