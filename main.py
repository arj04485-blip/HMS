import streamlit as st
import pandas as pd
from db import get_connection, create_tables
import sqlite3

st.title("Hostel Management System (Basic Version)")
st.subheader('lets make the hostel management eaiser')

ROOM_RENT = {
    "Single": 2500,
    "2 Sharing": 1800,
    "2 Sharing Attached": 2200,
    "Triple": 1800
}

menu = st.sidebar.selectbox(
    "Menu",
    ["Dashboard", "Add Tenant", "View Tenants", "Rent Status", "Export"]
)
if menu == "Add Tenant":
    st.header("Add New Tenant")

    name = st.text_input("Name")
    building = st.selectbox("Building", ["A", "B"])
    floor = st.selectbox("Floor", [1, 2, 3])
    room_type = st.selectbox("Room Type", list(ROOM_RENT.keys()))
    room_number = st.number_input("Room Number", step=1)

    if st.button("Add Tenant"):
        rent = ROOM_RENT[room_type]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO tenants (name, building, floor, room_type, room_number, rent) VALUES (?,?,?,?,?,?)",
                    (name, building, floor, room_type, room_number, rent))
        conn.commit()
        conn.close()
        st.success("Tenant added successfully.")

if menu == "View Tenants":
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM tenants", conn)
    st.dataframe(df)

