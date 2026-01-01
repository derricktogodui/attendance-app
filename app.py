import streamlit as st
from st_supabase_connection import SupabaseConnection
import datetime
import pandas as pd

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
    st.stop() 

# --- FUNCTIONS ---
def get_classes():
    return conn.table("classes").select("id, name").execute()

def get_students(class_id):
    return conn.table("students").select("id, full_name").eq("class_id", class_id).execute()

# --- NAVIGATION ---
st.sidebar.title("Menu")
page = st.sidebar.radio("Navigate to:", ["First Time Setup", "Take Attendance", "Record Scores"])

st.title("Attendance & Grades Pro")

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
