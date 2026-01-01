import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime

conn = st.connection("supabase", type=SupabaseConnection)

st.title("Check-In 📝")

# 1. Selection
classes = conn.query("id, name", table="classes").execute()
class_map = {c['name']: c['id'] for c in classes.data}
selected_class = st.selectbox("Select Class", list(class_map.keys()))

if selected_class:
    class_id = class_map[selected_class]
    students = conn.query("id, full_name", table="students").filter("class_id", "eq", class_id).execute()
    
    # 2. The "Mark All" Logic using Session State
    if "attendance_dict" not in st.session_state:
        st.session_state.attendance_dict = {s['id']: True for s in students.data}

    st.subheader(f"Attendance for {datetime.date.today()}")
    
    # "Mark All" Button resets everything to True
    if st.button("Reset / Mark All Present"):
        for s in students.data:
            st.session_state.attendance_dict[s['id']] = True

    # 3. The List of Checkboxes
    updated_attendance = {}
    for s in students.data:
        # This displays the student and lets you uncheck them
        is_present = st.checkbox(
            s['full_name'], 
            value=st.session_state.attendance_dict[s['id']], 
            key=s['id']
        )
        updated_attendance[s['id']] = is_present

    # 4. Save to Supabase
    if st.button("Save Attendance to Database"):
        records = [
            {"student_id": s_id, "is_present": status, "date": str(datetime.date.today())}
            for s_id, status in updated_attendance.items()
        ]
        # Bulk insert into Supabase
        conn.table("attendance").upsert(records).execute()
        st.success("Attendance saved successfully!")
