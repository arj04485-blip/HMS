import streamlit as st
import sqlite3
import hashlib
from datetime import datetime

# ---------------- DATABASE ----------------
conn = sqlite3.connect("hostel.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,
    subscription TEXT DEFAULT 'trial'
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    name TEXT,
    contact TEXT,
    room_type TEXT,
    rent INTEGER,
    building TEXT,
    status TEXT,
    created_at TEXT
)
""")
conn.commit()

# ---------------- HELPERS ----------------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

ROOM_RENT = {
    "Single": 6000,
    "2 Sharing": 4500,
    "2 Sharing (Attached Bathroom)": 5500,
    "3 Sharing": 3500
}

# ---------------- SESSION ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ---------------- AUTH ----------------
def login():
    st.subheader("Login")
    email = st.text_input("Email")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        c.execute("SELECT id, password FROM users WHERE email=?", (email,))
        user = c.fetchone()
        if user and user[1] == hash_password(pwd):
            st.session_state.user_id = user[0]
            st.success("Logged in")
            st.rerun()
        else:
            st.error("Invalid credentials")

def signup():
    st.subheader("Create Account")
    email = st.text_input("Email")
    pwd = st.text_input("Password", type="password")

    if st.button("Signup"):
        try:
            c.execute(
                "INSERT INTO users (email, password) VALUES (?,?)",
                (email, hash_password(pwd))
            )
            conn.commit()
            st.success("Account created. Please login.")
        except:
            st.error("Email already exists")

# ---------------- TENANT FUNCTIONS ----------------
def add_tenant(owner_id):
    st.subheader("Add New Tenant")
    name = st.text_input("Tenant Name")
    contact = st.text_input("Contact Number")
    room_type = st.selectbox("Room Type", list(ROOM_RENT.keys()))
    rent = ROOM_RENT[room_type]
    building = st.text_input("Building No (Optional)")

    st.info(f"Monthly Rent: ₹{rent}")

    if st.button("Add Tenant"):
        c.execute("""
        INSERT INTO tenants 
        (owner_id, name, contact, room_type, rent, building, status, created_at)
        VALUES (?,?,?,?,?,?,?,?)
        """, (
            owner_id, name, contact, room_type,
            rent, building, "active", datetime.now().isoformat()
        ))
        conn.commit()
        st.success("Tenant added")

def list_tenants(owner_id, status):
    c.execute("""
    SELECT id, name, contact, room_type, rent, building 
    FROM tenants WHERE owner_id=? AND status=?
    """, (owner_id, status))
    return c.fetchall()

def checkout_tenant(tenant_id):
    c.execute("UPDATE tenants SET status='checked_out' WHERE id=?", (tenant_id,))
    conn.commit()

# ---------------- DASHBOARD ----------------
def dashboard():
    st.sidebar.title("Hostel Menu")

    menu = st.sidebar.radio(
        "Navigate",
        ["Add Tenant", "Active Tenants", "Checked-out Tenants", "Logout"]
    )

    if menu == "Add Tenant":
        add_tenant(st.session_state.user_id)

    elif menu == "Active Tenants":
        st.subheader("Active Tenants")
        tenants = list_tenants(st.session_state.user_id, "active")
        for t in tenants:
            with st.expander(t[1]):
                st.write(f"Contact: {t[2]}")
                st.write(f"Room: {t[3]}")
                st.write(f"Rent: ₹{t[4]}")
                st.write(f"Building: {t[5]}")
                if st.button("Checkout", key=t[0]):
                    checkout_tenant(t[0])
                    st.rerun()

    elif menu == "Checked-out Tenants":
        st.subheader("Checked-out Tenants")
        tenants = list_tenants(st.session_state.user_id, "checked_out")
        for t in tenants:
            st.write(f"{t[1]} | {t[3]} | ₹{t[4]}")

    elif menu == "Logout":
        st.session_state.user_id = None
        st.rerun()

# ---------------- MAIN ----------------
st.title("Hostel Management System")

if st.session_state.user_id is None:
    tab1, tab2 = st.tabs(["Login", "Signup"])
    with tab1:
        login()
    with tab2:
        signup()
else:
    dashboard()


