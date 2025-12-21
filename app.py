import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date

        
# ---------------- SESSION ----------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    

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
    room_id INTEGER,
    rent INTEGER,
    building TEXT,
    status TEXT,
    created_at TEXT,
    join_date TEXT,
    checkout_date TEXT,
    security_deposit INTEGER,
    monthly_rent INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    room_type TEXT,
    room_label TEXT,
    total_beds INTEGER
)
""")
conn.commit()

c.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER,
    owner_id INTEGER,
    amount INTEGER,
    paid_for_month TEXT,
    paid_on TEXT
)
""")
conn.commit()


c.execute("CREATE TABLE IF NOT EXISTS room_config (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, room_type TEXT, building TEXT, capacity INTEGER, rent INTEGER)")
conn.commit()



# ---------------- HELPERS ----------------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()


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

def tenant_balance(tenant_id):
    c.execute("SELECT join_date, monthly_rent FROM tenants WHERE id=?", (tenant_id,))
    row = c.fetchone()
    if not row or not row[0]:
        return 0, 0, 0

    join_date, rent = row

    # ✅ Robust date parsing
    try:
        jd = datetime.strptime(join_date, "%Y-%m-%d").date()
    except ValueError:
        jd = datetime.strptime(join_date[:10], "%Y-%m-%d").date()

    today = date.today()

    months = (today.year - jd.year) * 12 + (today.month - jd.month) + 1
    if months < 1:
        months = 1

    expected = months * rent

    c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE tenant_id=?", (tenant_id,))
    paid = c.fetchone()[0]

    remaining = expected - paid
    return expected, paid, remaining


def checkout_summary(tenant_id):
    c.execute(
        "SELECT security_deposit FROM tenants WHERE id=?",
        (tenant_id,)
    )
    deposit = c.fetchone()[0] or 0

    expected, paid, remaining = tenant_balance(tenant_id)

    refund = deposit - remaining
    return expected, paid, remaining, deposit, refund

def assign_room(owner_id, room_type):
    beds_map = {
        "Single": 1,
        "2 Sharing": 2,
        "3 Sharing": 3
    }
    beds = beds_map[room_type]

    # Try to find an existing room with empty bed
    c.execute("""
    SELECT r.id, r.total_beds, COUNT(t.id) AS occupied
    FROM rooms r
    LEFT JOIN tenants t
        ON r.id = t.room_id AND t.status='active'
    WHERE r.owner_id=? AND r.room_type=?
    GROUP BY r.id
    HAVING occupied < r.total_beds
    LIMIT 1
    """, (owner_id, room_type))

    room = c.fetchone()
    if room:
        return room[0]

    # Otherwise create new room
    c.execute(
        "SELECT COUNT(*) FROM rooms WHERE owner_id=? AND room_type=?",
        (owner_id, room_type)
    )
    count = c.fetchone()[0] + 1

    label = f"{room_type.replace(' ', '')}-{count}"

    c.execute("""
    INSERT INTO rooms (owner_id, room_type, room_label, total_beds)
    VALUES (?, ?, ?, ?)
    """, (owner_id, room_type, label, beds))

    conn.commit()
    return c.lastrowid

def manage_rooms(owner_id):
    st.subheader("Room Management")

    c.execute(
        "SELECT id, room_label, room_type, total_beds FROM rooms WHERE owner_id=?",
        (owner_id,)
    )
    rooms = c.fetchall()

    if not rooms:
        st.info("No rooms available")
        return

    for r in rooms:
        with st.expander(f"{r[1]} ({r[2]})"):
            new_label = st.text_input(
                "Room Name",
                value=r[1],
                key=f"room_label_{r[0]}"
            )

            st.write(f"Total Beds: {r[3]}")

            if st.button("Update Name", key=f"update_room_{r[0]}"):
                c.execute(
                    "UPDATE rooms SET room_label=? WHERE id=? AND owner_id=?",
                    (new_label, r[0], owner_id)
                )
                conn.commit()
                st.success("Room name updated")
                st.rerun()
                

    
def load_demo_data(owner_id):
    tenants = [
        ("Aman", "999000001", "Single", 5000, 3000),
        ("Rohit", "999000002", "2 Sharing", 4000, 3000),
        ("Suresh", "999000003", "2 Sharing", 4000, 3000),
        ("Vikas", "999000004", "3 Sharing", 3000, 2000),
        ("Ankit", "999000005", "Single", 5000, 3000),
        ("Rahul", "999000006", "3 Sharing", 3000, 2000),
        ("Deepak", "999000007", "2 Sharing", 4000, 3000),
        ("Nitin", "999000008", "Single", 5000, 3000),
        ("Manoj", "999000009", "3 Sharing", 3000, 2000),
        ("Kunal", "999000010", "2 Sharing", 4000, 3000),
    ]

    for t in tenants:
        c.execute("""
        INSERT INTO tenants
        (owner_id, name, contact, room_type, monthly_rent, security_deposit, join_date, status)
        VALUES (?, ?, ?, ?, ?, ?, DATE('now','-2 months'), 'active')
        """, (owner_id, t[0], t[1], t[2], t[3], t[4]))

    conn.commit()


# ---------------- AUTH ----------------
def login():
    st.subheader("Login")

    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_btn"):
        c.execute("SELECT id, password FROM users WHERE email=?", (email,))
        u = c.fetchone()

        if u and u[1] == hash_password(password):
            st.session_state.user_id = u[0]
            st.success("Login successful")
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
def record_payment(owner_id):
    st.subheader("Record Tenant Payment")

    tenants = c.execute(
        "SELECT id, name FROM tenants WHERE owner_id=? AND status='active'",
        (owner_id,)
    ).fetchall()

    if not tenants:
        st.info("No active tenants")
        return

    tenant_map = {f"{t[1]} (ID:{t[0]})": t[0] for t in tenants}
    selected = st.selectbox("Select Tenant", list(tenant_map.keys()))

    amount = st.number_input("Amount Paid", min_value=0,step_value=500)
    month = st.selectbox(
        "Paid For Month",
        ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    )

    if st.button("Save Payment"):
        c.execute(
            "INSERT INTO payments (tenant_id, owner_id, amount, paid_for_month, paid_on) VALUES (?,?,?,?,DATE('now'))",
            (tenant_map[selected], owner_id, amount, month)
        )
        conn.commit()
        st.success("Payment recorded")
             

def add_tenant(owner_id):
    name = st.text_input("Tenant Name")
    contact = st.text_input("Contact Number")
    room_type = st.selectbox("Room Type", ["Single","2 Sharing","2 Sharing (Attached Bathroom)","3 Sharing"])
    deposit = st.number_input("Security Deposit",min_value=0,step=500)
    c.execute("SELECT rent FROM room_config WHERE owner_id=? AND room_type=?", (owner_id,room_type))
    r = c.fetchone()
    rent = r[0] if r else 0
    building = st.text_input("Building No (Optional)")
    st.write("Monthly Rent: ₹", rent)
    if st.button("Add Tenant"):
        if rent == 0:
            st.error("Please configure rooms first")
        else:
            room_id = assign_room(owner_id, room_type)
            c.execute("""INSERT INTO tenants(owner_id, name, contact, room_type, room_id,monthly_rent, security_deposit, join_date, status)VALUES (?, ?, ?, ?, ?, ?, ?, DATE('now'), 'active')""", 
                      (owner_id, name, contact, room_type, room_id,rent, deposit))
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
    st.title("Hostel Management System")

    st.sidebar.title("Hostel Menu")

    menu = st.sidebar.radio("Menu", ["Dashboard","Room config","Room","Record Payment","Add Tenant","Active Tenants","Vacancy Dashboard","Checked-out Tenants","Logout"])
                            
    if menu == "Dashboard":
        st.subheader("Welcome to Dashboard")
        st.write("Select an option from sidebar")
    elif menu == "Room config":
        setup_rooms(st.session_state.user_id)
    elif menu == "Rooms":
        manage_rooms(st.session_state.user_id)
    elif menu == "Record Payment":
        record_payment(st.session_state.user_id)
    elif menu == "Add Tenant":
        add_tenant(st.session_state.user_id)

    elif menu == "Active Tenants":
        st.subheader("Active Tenants")
        tenants = c.execute(
            "SELECT id, name FROM tenants WHERE owner_id=? AND status='active'",
            (st.session_state.user_id,)
        ).fetchall()
        for t in tenants:
            with st.expander(t[1]):
                expected, paid, remaining, deposit, refund = checkout_summary(t[0])
                st.write(f"Total Rent Till Date: ₹{expected}")
                st.write(f"Total Paid: ₹{paid}")
                st.write(f"Outstanding Due: ₹{remaining}")
                st.write(f"Security Deposit: ₹{deposit}")
                if refund >= 0:
                    st.success(f"Refund to Tenant: ₹{refund}")
                else:
                    st.error(f"Amount to Collect: ₹{-refund}")
                if st.button("Checkout Tenant", key=f"checkout_{t[0]}"):
                    c.execute("UPDATE tenants SET status='checked_out', checkout_date=DATE('now') WHERE id=?",
                              (t[0],)
                             )
                    conn.commit()
                    st.success("Tenant checked out successfully")
                    st.rerun()

    elif menu == "Checked-out Tenants":
        st.subheader("Checked-out Tenants")
        tenants = list_tenants(st.session_state.user_id, "checked_out")
        for t in tenants:
            st.write(f"{t[1]} | {t[3]} | ₹{t[4]}")

    elif menu == "Logout":
        st.session_state.user_id = None
        st.rerun()
            
    st.divider()
    st.subheader("Active Tenant Balances")
    tenants = c.execute("SELECT id, name, join_date, monthly_rent FROM tenants WHERE owner_id=? AND status='active'",
    (st.session_state.user_id,)).fetchall()
    if not tenants:
        st.info("No active tenants")
    else:
        for t in tenants:
            expected, paid, remaining = tenant_balance(t[0])
            st.write(
                f"""
                **{t[1]}**
                | Joined: {t[2]}
                | Rent: ₹{t[3]}
                | Paid: ₹{paid}
                | Due: ₹{remaining}
                """
            )
    
    st.subheader("Room & Bed Vacancy")
    c.execute("""SELECT r.room_label,
       r.room_type,
       r.total_beds,
       COUNT(t.id) AS occupied,
       (r.total_beds - COUNT(t.id)) AS vacant
       FROM rooms r
       LEFT JOIN tenants t
       ON r.id = t.room_id
       AND t.checkout_date IS NULL
       WHERE r.owner_id=?
       GROUP BY r.id""", (st.session_state.user_id,))
    rooms = c.fetchall()
    if not rooms:
        st.info("No rooms created yet")
    else:
        for r in rooms:
            st.write(
                f"{r[0]} ({r[1]}) | Beds: {r[2]} | Occupied: {r[3]} | Vacant: {r[4]}"
            )

    
    if st.button("Load Demo Data (Temporary)"):
        load_demo_data(st.session_state.user_id)
        st.success("Demo data loaded")
        st.rerun()

# ---------------- MAIN ----------------

if st.session_state.user_id is None:
    tab1, tab2 = st.tabs(["Login", "Signup"])
    with tab1:
        login()
    with tab2:
        signup()
else:
    dashboard()
