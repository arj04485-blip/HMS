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

if menu == "Rent Status":
    conn = get_connection()
    tenants = pd.read_sql_query("SELECT * FROM tenants", conn)

    for _, row in tenants.iterrows():
        st.write(f"{row['name']} - Room {row['room_number']} - ₹{row['rent']}")
        paid = st.checkbox("Paid", key=row['id'])

        if paid:
            month = "December-2025"
            cur = conn.cursor()
            cur.execute("INSERT INTO payments (tenant_id, month, paid) VALUES (?,?,1)",
                        (row['id'], month))
            conn.commit()
if menu == "Dashboard":
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM tenants", conn)
    st.metric("Total Tenants", len(df))

    payments = pd.read_sql_query("SELECT * FROM payments WHERE paid=1", conn)
    total_collected = payments.merge(df, left_on="tenant_id", right_on="id")["rent"].sum()

    st.metric("Total Rent Collected", f"₹{total_collected}")

if menu == "Export":
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM tenants", conn)
    df.to_excel("hostel_export.xlsx", index=False)
    st.success("Exported to hostel_export.xlsx")
