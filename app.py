import streamlit as st
from st_supabase_connection import SupabaseConnection

# 1. Connection with Error Handling
try:
    conn = st.connection("supabase", type=SupabaseConnection)
    st.success("✅ Connection to Supabase is active!")
except Exception as e:
    st.error(f"❌ Connection Failed. Check your Secrets. Error: {e}")
    st.stop() # Stops the app here if keys are wrong

st.title("Attendance & Grades Pro")

# 2. Navigation Sidebar
st.sidebar.title("Menu")
page = st.sidebar.radio("Navigate to:", ["First Time Setup", "Take Attendance", "Record Scores"])

# --- PAGE 1: SETUP (Do this first!) ---
if page == "First Time Setup":
    st.header("1️⃣ Add a Class")
    st.info("You must add a class before you can add students.")
    
    with st.form("add_class_form"):
        new_class = st.text_input("Enter Class Name (e.g. Science 101)")
        if st.form_submit_button("Create Class"):
            conn.table("classes").insert({"name": new_class}).execute()
            st.success(f"Class '{new_class}' created!")

    st.divider()

    st.header("2️⃣ Add Students")
    # Fetch classes to show in dropdown
    classes = conn.query("id, name", table="classes").execute()
    
    if not classes.data:
        st.warning("No classes found. Add a class above first.")
    else:
        class_options = {c['name']: c['id'] for c in classes.data}
        selected_c = st.selectbox("Select Class", list(class_options.keys()))
        
        with st.form("add_student_form"):
            s_name = st.text_input("Student Full Name")
            if st.form_submit_button("Add Student"):
                conn.table("students").insert({
                    "full_name": s_name, 
                    "class_id": class_options[selected_c]
                }).execute()
                st.success(f"Added {s_name} to {selected_c}!")

# --- PAGE 2: ATTENDANCE ---
elif page == "Take Attendance":
    st.header("📝 Attendance")
    # This will be blank until you do 'Step 1'
    classes = conn.query("id, name", table="classes").execute()
    if not classes.data:
        st.error("No data! Go to 'First Time Setup' in the sidebar.")
    else:
        st.write("Once you add students, they will appear here as checkboxes.")

# --- PAGE 3: SCORES ---
else:
    st.header("🏆 Scores")
    st.write("Once you have students, you can record Quiz, Midterm, etc. here.")
