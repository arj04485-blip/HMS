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

c.execute("CREATE TABLE IF NOT EXISTS room_config (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, room_type TEXT, capacity INTEGER, rent INTEGER)")
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
def setup_rooms(owner_id):
    st.write("Configure Rooms & Rent")
    room_types = ["Single","2 Sharing","2 Sharing (Attached Bathroom)","3 Sharing"]
    for r in room_types:
        c.execute("SELECT capacity,rent FROM room_config WHERE owner_id=? AND room_type=?", (owner_id,r))
        row = c.fetchone()
        cap = row[0] if row else 0
        rent = row[1] if row else 0
        new_cap = st.number_input(r+" Capacity", min_value=0, value=cap, key="cap_"+r)
        new_rent = st.number_input(r+" Rent", min_value=0, value=rent, key="rent_"+r)
        if st.button("Save "+r, key="save_"+r):
            c.execute("DELETE FROM room_config WHERE owner_id=? AND room_type=?", (owner_id,r))
            c.execute("INSERT INTO room_config (owner_id,room_type,capacity,rent) VALUES (?,?,?,?)", (owner_id,r,new_cap,new_rent))
            conn.commit()
            st.success(r+" saved")

def vacancy_data(owner_id):
    c.execute("SELECT room_type,building,capacity FROM room_config WHERE owner_id=?", (owner_id,))
    rows = c.fetchall()
    for r in rows:
        c.execute("SELECT COUNT(*) FROM tenants WHERE owner_id=? AND room_type=? AND status='active'", (owner_id,r[0]))
        occupied = c.fetchone()[0]
        st.write(r[0], "| Building:", r[1], "| Occupied:", occupied, "| Vacant:", r[2]-occupied)



# ---------------- SESSION ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ---------------- AUTH ----------------
def login():
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login", key="login_btn"):
        c.execute("SELECT id,password FROM users WHERE email=?", (email,))
        u = c.fetchone()
        if u and u[1] == hash_password(password):
            st.session_state.user_id = u[0]
            st.rerun()
        else:
            st.error("Invalid login")


def signup():
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")
    if st.button("Signup", key="signup_btn"):
        try:
            c.execute("INSERT INTO users (email,password) VALUES (?,?)", (email, hash_password(password)))
            conn.commit()
            st.success("Account created")
        except:
            st.error("Email already exists")


# ---------------- TENANT FUNCTIONS ----------------
def add_tenant(owner_id):
    name = st.text_input("Tenant Name")
    contact = st.text_input("Contact Number")
    room_type = st.selectbox("Room Type", ["Single","2 Sharing","2 Sharing (Attached Bathroom)","3 Sharing"])
    c.execute("SELECT rent FROM room_config WHERE owner_id=? AND room_type=?", (owner_id,room_type))
    r = c.fetchone()
    rent = r[0] if r else 0
    building = st.text_input("Building No (Optional)")
    st.write("Monthly Rent: ₹", rent)
    if st.button("Add Tenant"):
        if rent == 0:
            st.error("Please configure rooms first")
        else:
            c.execute("INSERT INTO tenants (owner_id,name,contact,room_type,rent,building,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                      (owner_id,name,contact,room_type,rent,building,"active",datetime.now().isoformat()))
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

    menu = st.sidebar.radio("Menu", ["Room Setup","Add Tenant","Active Tenants","Vacancy Dashboard","Checked-out Tenants","Logout"]
                            
    if menu == "Room Setup":
    setup_rooms(st.session_state.user_id)
    
    elif menu == "Add Tenant":
        add_tenant(st.session_state.user_id)

    elif menu == "Vacancy Dashboard":
    data = vacancy_data(st.session_state.user_id)
    if not data:
        st.info("Please configure rooms first")
    for d in data:
        st.write(d[0], "| Occupied:", d[1], "| Vacant:", d[2])

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


