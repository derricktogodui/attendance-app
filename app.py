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
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # Clean headers
            df.columns = df.columns.str.strip().str.lower()
            st.write("Preview of cleaned data:", df.head())
            
            if 'name' not in df.columns:
                st.error("Column 'name' not found.")
            else:
                # We use a unique key for the button to prevent accidental clicks
                if st.button("🚀 Import All Students", key="bulk_import_btn"):
                    student_list = []
                    for index, row in df.iterrows():
                        student_list.append({
                            "full_name": row['name'], 
                            "class_id": class_map[target_class],
                            "gender": row.get('gender', 'Not Specified') 
                        })
                    
                    try:
                        # Using UPSERT instead of INSERT to avoid duplicates
                        conn.table("students").upsert(student_list, on_conflict="full_name, class_id").execute()
                        st.success(f"Successfully imported {len(student_list)} students!")
                        # This clears the file uploader and prevents double-clicking
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during import: {e}")
# --- PAGE: ATTENDANCE ---
elif page == "Take Attendance":
    st.header("📝 Daily Attendance")
    
    classes_data = get_classes()
    if not classes_data.data:
        st.warning("Please add a class and students first.")
    else:
        class_map = {c['name']: c['id'] for c in classes_data.data}
        selected_class = st.selectbox("Select Class", list(class_map.keys()))
        
        students = get_students(class_map[selected_class])
        
        if not students.data:
            st.info("No students enrolled in this class.")
        else:
            st.write(f"Taking attendance for: **{datetime.date.today()}**")
            
            # --- THE "MARK ALL" LOGIC ---
            # We use a toggle button to set the default state for all checkboxes
            if "all_present" not in st.session_state:
                st.session_state.all_present = True
            
            if st.button("Toggle: Mark All Present/Absent"):
                st.session_state.all_present = not st.session_state.all_present
                st.rerun()

            st.divider()

            # Create the list of checkboxes
            attendance_results = []
            for s in students.data:
                # Value is driven by the 'all_present' state
                is_present = st.checkbox(
                    s['full_name'], 
                    value=st.session_state.all_present, 
                    key=f"check_{s['id']}"
                )
                attendance_results.append({
                    "student_id": s['id'], 
                    "is_present": is_present, 
                    "date": str(datetime.date.today())
                })

            st.divider()
            
            if st.button("💾 Save Attendance to Supabase"):
                # .upsert handles both new records and updates to existing ones
                conn.table("attendance").upsert(attendance_results).execute()
                st.success(f"Attendance for {selected_class} has been saved!")



