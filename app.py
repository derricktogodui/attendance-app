import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime

# 1. Initialize Connection
conn = st.connection("supabase", type=SupabaseConnection)

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Take Attendance", "Record Scores", "Manage Class/Students"])

# --- PAGE: MANAGE ---
if page == "Manage Class/Students":
    st.header("⚙️ Setup Your Class")
    
    # Add Class
    with st.expander("Add New Class"):
        c_name = st.text_input("Class Name")
        if st.button("Create Class"):
            conn.table("classes").insert({"name": c_name}).execute()
            st.success("Class created!")
            st.rerun()

    # Add Student
    classes = conn.query("id, name", table="classes").execute()
    if classes.data:
        with st.expander("Add New Student"):
            class_map = {c['name']: c['id'] for c in classes.data}
            sel_class = st.selectbox("Select Class", list(class_map.keys()), key="add_stu_class")
            s_name = st.text_input("Student Full Name")
            if st.button("Enroll Student"):
                conn.table("students").insert({"full_name": s_name, "class_id": class_map[sel_class]}).execute()
                st.success(f"Added {s_name}")
    else:
        st.warning("Create a class first!")

# --- PAGE: ATTENDANCE ---
elif page == "Take Attendance":
    st.header("📝 Daily Check-in")
    classes = conn.query("id, name", table="classes").execute()
    
    if not classes.data:
        st.info("No classes found. Go to 'Manage' to add one.")
    else:
        class_map = {c['name']: c['id'] for c in classes.data}
        selected_class = st.selectbox("Select Class", list(class_map.keys()))
        
        class_id = class_map[selected_class]
        students = conn.query("id, full_name", table="students").filter("class_id", "eq", class_id).execute()
        
        if not students.data:
            st.warning("No students enrolled in this class.")
        else:
            # Mark All Logic
            if "att_dict" not in st.session_state:
                st.session_state.att_dict = {s['id']: True for s in students.data}

            if st.button("Reset: Mark All Present"):
                st.session_state.att_dict = {s['id']: True for s in students.data}
                st.rerun()

            # Checklist
            current_status = {}
            for s in students.data:
                current_status[s['id']] = st.checkbox(s['full_name'], value=st.session_state.att_dict.get(s['id'], True), key=f"check_{s['id']}")

            if st.button("Save Attendance"):
                records = [{"student_id": sid, "is_present": stat, "date": str(datetime.date.today())} for sid, stat in current_status.items()]
                conn.table("attendance").upsert(records).execute()
                st.success("Attendance Saved!")

# --- PAGE: SCORES ---
elif page == "Record Scores":
    st.header("🏆 Class Scores")
    categories = ['Quiz', 'Exercise', 'Midterm', 'Assignment', 'Presentation', 'Group Work', 'Participation']
    
    classes = conn.query("id, name", table="classes").execute()
    if classes.data:
        class_map = {c['name']: c['id'] for c in classes.data}
        sel_class = st.selectbox("Class", list(class_map.keys()))
        cat = st.selectbox("Category", categories)
        
        students = conn.query("id, full_name", table="students").filter("class_id", "eq", class_map[sel_class]).execute()
        
        # Simple Grade Form
        with st.form("grade_form"):
            grades_to_save = []
            for s in students.data:
                score = st.number_input(f"Score for {s['full_name']}", min_value=0, max_value=100, value=0)
                grades_to_save.append({"student_id": s['id'], "category": cat, "score_value": score})
            
            if st.form_submit_button("Save All Scores"):
                conn.table("scores").insert(grades_to_save).execute()
                st.success(f"{cat} scores saved!")
