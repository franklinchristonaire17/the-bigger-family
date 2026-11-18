import os
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from database import get_db_connection, init_db, calculate_age

def seed():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data safely
    cursor.execute("DELETE FROM broadcast_reads")
    cursor.execute("DELETE FROM notifications")
    cursor.execute("DELETE FROM attendance")
    cursor.execute("DELETE FROM meetings")
    cursor.execute("DELETE FROM dues_records")
    cursor.execute("DELETE FROM dues_settings")
    cursor.execute("DELETE FROM members")
    cursor.execute("DELETE FROM branches")

    # 1. Seed the 3 Branches
    branches_data = [
        (
            "Adabraka Branch (Headquarters)",
            "adabraka-branch",
            "Elder Kofi Kwabena Bigger",
            "The ancestral headquarters of The Bigger Family, based at Adabraka Family House, Accra (\"Ataa shi ɛfolo\"). Coordinates central family governance, welfare decisions, and hosts our bi-weekly general meetings.",
            "#1E3A8A" # Royal Blue
        ),
        (
            "Abossey Okai Branch",
            "abossey-okai-branch",
            "Dr. Kwesi Samuel Bigger",
            "Representing all Bigger family members and enterprises within Abossey Okai, Kaneshie, and surrounding communities. Active in family welfare and business mentorship.",
            "#059669" # Emerald Green
        ),
        (
            "Ofankor Branch",
            "ofankor-branch",
            "Deaconess Abena Adobea Bigger",
            "Uniting family members in Ofankor, Achimota, Pokuase, and greater Ga North. Dedicated to youth educational development and family community fellowship.",
            "#D97706" # Warm Amber
        )
    ]

    branch_ids = {}
    for name, slug, leader, desc, color in branches_data:
        cursor.execute(
            "INSERT INTO branches (name, slug, leader_name, description, color_code) VALUES (?, ?, ?, ?, ?)",
            (name, slug, leader, desc, color)
        )
        branch_ids[slug] = cursor.lastrowid

    # 2. Seed Members (All strictly 16 and above)
    today = date.today()
    default_password = generate_password_hash("password123")
    admin_password = generate_password_hash("admin123")

    members_data = [
        # (branch_slug, full_name, email, phone, dob, gender, occ, res, bio, role, is_admin, parent_key)
        (
            "adabraka-branch",
            "Elder Kofi Kwabena Bigger",
            "admin@biggerfamily.org",
            "+233 24 456 7890",
            "1958-04-12",
            "Male",
            "Retired Civil Engineer & Family Head",
            "Adabraka Family House (\"Ataa shi ɛfolo\"), Accra",
            "Preserving our ancestral heritage and uniting all branches under our Adabraka family seat.",
            "admin",
            admin_password,
            None
        ),
        (
            "abossey-okai-branch",
            "Dr. Kwesi Samuel Bigger",
            "kwesi.bigger@gmail.com",
            "+233 20 812 3456",
            "1984-08-20",
            "Male",
            "Senior Consultant Physician & Pharmacist",
            "Abossey Okai / Kaneshie, Accra",
            "Son of Elder Kofi. Coordinating medical welfare and the Abossey Okai branch affairs.",
            "branch_leader",
            default_password,
            "admin@biggerfamily.org"
        ),
        (
            "adabraka-branch",
            "Akosua Serwaa Bigger",
            "serwaa.bigger@outlook.com",
            "+233 55 987 6543",
            "2007-02-14", # 19 years old
            "Female",
            "Undergraduate Student, Computer Science",
            "Adabraka, Accra",
            "Daughter of Dr. Kwesi. Passionate about youth involvement and digital innovation for our family portal.",
            "member",
            default_password,
            "kwesi.bigger@gmail.com"
        ),
        (
            "adabraka-branch",
            "Kofi Junior Bigger",
            "kofi.jr@gmail.com",
            "+233 50 112 2334",
            "2010-09-05", # Exactly 16 years old
            "Male",
            "High School Senior (Achimota School)",
            "Adabraka, Accra",
            "Newly inducted 16-year-old junior member of the Adabraka branch eager to contribute to family affairs.",
            "member",
            default_password,
            "kwesi.bigger@gmail.com"
        ),
        (
            "ofankor-branch",
            "Deaconess Abena Adobea Bigger",
            "abena.adobea@gmail.com",
            "+233 24 334 5566",
            "1965-11-03",
            "Female",
            "Headmistress & Educationalist",
            "Ofankor Barrier, Accra",
            "Head of the Ofankor branch. Dedicated to youth mentorship, scholarship funds, and spiritual unity.",
            "branch_leader",
            default_password,
            None
        ),
        (
            "abossey-okai-branch",
            "Yaw Mensah Bigger",
            "yaw.mensah@gmail.com",
            "+233 27 778 8990",
            "1990-06-18",
            "Male",
            "Chartered Accountant & Auto Parts Merchant",
            "Abossey Okai, Accra",
            "Managing financial audit, receipt reconciliation, and welfare dues reporting.",
            "member",
            default_password,
            "abena.adobea@gmail.com"
        ),
        (
            "ofankor-branch",
            "Dr. Emmanuel Bigger Jr.",
            "emmanuel.jr@gmail.com",
            "+233 20 554 4332",
            "1972-03-25",
            "Male",
            "Geologist & Real Estate Consultant",
            "Ofankor Hills, Accra",
            "Supporting family property registry, documentation, and the Ofankor branch community projects.",
            "member",
            default_password,
            None
        ),
        (
            "adabraka-branch",
            "Madam Beatrice Bigger",
            "beatrice.bigger@yahoo.com",
            "+233 24 990 1234",
            "1968-12-10",
            "Female",
            "Business Executive & Caterer",
            "Adabraka, Accra",
            "Organizing our bi-weekly assembly hospitality and family anniversary welfare packages.",
            "branch_leader",
            default_password,
            None
        )
    ]

    member_ids = {}
    for item in members_data:
        branch_slug = item[0]
        full_name = item[1]
        email = item[2]
        phone = item[3]
        dob_str = item[4]
        gender = item[5]
        occ = item[6]
        res = item[7]
        bio = item[8]
        role = item[9]
        pwd = item[10]
        age = calculate_age(dob_str)

        cursor.execute('''
            INSERT INTO members (branch_id, full_name, email, phone, date_of_birth, age, gender, occupation, residence, bio, role, password_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (branch_ids[branch_slug], full_name, email, phone, dob_str, age, gender, occ, res, bio, role, pwd))
        member_ids[email] = cursor.lastrowid

    # Update parent_member_ids
    for item in members_data:
        email = item[2]
        parent_key = item[11]
        if parent_key and parent_key in member_ids:
            cursor.execute(
                "UPDATE members SET parent_member_id = ? WHERE id = ?",
                (member_ids[parent_key], member_ids[email])
            )

    # 3. Seed Dues Settings (Monthly GH₵ 50.00)
    cursor.execute('''
        INSERT INTO dues_settings (title, monthly_amount, currency, due_day_of_month, momo_number, momo_name, bank_name, bank_account, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "The Bigger Family Monthly Welfare Dues",
        50.00,
        "GH₵",
        28,
        "024 456 7890",
        "The Bigger Family Welfare Fund (Elder Kofi Bigger)",
        "GCB Bank Ghana - High Street / Kwame Nkrumah Avenue",
        "1441002345678",
        1
    ))

    # 4. Seed Dues Records (Current & Previous months)
    curr_period = today.strftime('%Y-%m')
    curr_label = today.strftime('%B %Y')
    
    prev_month_date = (today.replace(day=1) - timedelta(days=1))
    prev_period = prev_month_date.strftime('%Y-%m')
    prev_label = prev_month_date.strftime('%B %Y')

    admin_id = member_ids["admin@biggerfamily.org"]
    
    for email, m_id in member_ids.items():
        # Previous month: Paid
        cursor.execute('''
            INSERT INTO dues_records (member_id, period_month, period_label, amount_due, amount_paid, status, payment_method, transaction_reference, payment_date, verified_by, verified_at, admin_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            m_id,
            prev_period,
            prev_label,
            50.00,
            50.00,
            'paid',
            'MTN MoMo',
            f'TXN-PREV-{m_id:04d}',
            f'{prev_period}-25 14:30:00',
            admin_id,
            f'{prev_period}-26 09:00:00',
            'Confirmed via Welfare MoMo account'
        ))

        # Current month
        if email in ["admin@biggerfamily.org", "kwesi.bigger@gmail.com", "beatrice.bigger@yahoo.com"]:
            cursor.execute('''
                INSERT INTO dues_records (member_id, period_month, period_label, amount_due, amount_paid, status, payment_method, transaction_reference, payment_date, verified_by, verified_at, admin_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                m_id,
                curr_period,
                curr_label,
                50.00,
                50.00,
                'paid',
                'MTN MoMo',
                f'MOMO-NOV-{m_id:04d}98',
                f'{curr_period}-10 11:20:00',
                admin_id,
                f'{curr_period}-11 16:45:00',
                'Paid on time. Receipt issued.'
            ))
        elif email in ["serwaa.bigger@outlook.com", "yaw.mensah@gmail.com"]:
            cursor.execute('''
                INSERT INTO dues_records (member_id, period_month, period_label, amount_due, amount_paid, status, payment_method, transaction_reference, payment_date, admin_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                m_id,
                curr_period,
                curr_label,
                50.00,
                50.00,
                'pending_verification',
                'Telecel Cash',
                f'TEL-NOV-{m_id:04d}55',
                f'{curr_period}-15 18:00:00',
                'Awaiting admin bank/MoMo reconciliation'
            ))
        else:
            cursor.execute('''
                INSERT INTO dues_records (member_id, period_month, period_label, amount_due, amount_paid, status)
                VALUES (?, ?, ?, ?, 0.00, 'unpaid')
            ''', (
                m_id,
                curr_period,
                curr_label,
                50.00
            ))

    # 5. Seed Bi-Weekly Meetings (Every 2 weeks at Adabraka Family House "Ataa shi ɛfolo" & Zoom)
    next_meeting_date = (today + timedelta(days=6)).strftime('%Y-%m-%d')
    following_meeting_date = (today + timedelta(days=20)).strftime('%Y-%m-%d')
    past_meeting_date = (today - timedelta(days=8)).strftime('%Y-%m-%d')

    cursor.execute('''
        INSERT INTO meetings (title, meeting_type, scheduled_date, start_time, end_time, location_type, location_detail, agenda, minutes, status, cycle_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "Bigger Family Bi-Weekly Assembly #24",
        "Bi-Weekly General Assembly",
        next_meeting_date,
        "16:00",
        "18:00",
        "hybrid",
        "Headquarters: Adabraka Family House, Accra (\"Ataa shi ɛfolo\") & Virtual Zoom (Link: https://zoom.us/j/9876543210 - Passcode: BIGGER2026)",
        "1. Opening Prayer & Welcome by Elder Kofi Kwabena Bigger\n2. Review of Previous Minutes (Assembly #23)\n3. Reports from Branches (Adabraka, Abossey Okai, Ofankor)\n4. Monthly Welfare Fund (GH₵ 50.00) & Dues Compliance\n5. Adabraka Family House Renovation Updates\n6. Induction of New 16+ Family Members\n7. AOB & Closing Benediction",
        None,
        "upcoming",
        24
    ))
    upcoming_meeting_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO meetings (title, meeting_type, scheduled_date, start_time, end_time, location_type, location_detail, agenda, minutes, status, cycle_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "Bigger Family Bi-Weekly Assembly #25",
        "Bi-Weekly General Assembly",
        following_meeting_date,
        "16:00",
        "18:00",
        "virtual",
        "Virtual via Zoom (Passcode: BIGGER2026) & Family Compound, Adabraka (\"Ataa shi ɛfolo\")",
        "1. Opening Devotion\n2. Youth Mentorship & Educational Support\n3. Financial Audit Report (Adabraka, Abossey Okai, Ofankor)\n4. Welfare Scheme Subsidies\n5. Closing Prayer",
        None,
        "upcoming",
        25
    ))

    cursor.execute('''
        INSERT INTO meetings (title, meeting_type, scheduled_date, start_time, end_time, location_type, location_detail, agenda, minutes, status, cycle_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        "Bigger Family Bi-Weekly Assembly #23",
        "Bi-Weekly General Assembly",
        past_meeting_date,
        "16:00",
        "17:45",
        "hybrid",
        "Adabraka Family House, Accra (\"Ataa shi ɛfolo\") & Zoom Online",
        "1. Call to order by Elder Kofi Bigger\n2. Welfare dues compliance across branches (Adabraka, Abossey Okai, Ofankor)\n3. Recognition of youth turning 16 years\n4. Health insurance assistance",
        "MINUTES OF MEETING:\n- Assembly called to order at 4:05 PM at Adabraka Family House (\"Ataa shi ɛfolo\") by Elder Kofi Bigger.\n- Branch representatives from Adabraka, Abossey Okai, and Ofankor presented welfare reports.\n- 88% overall compliance on October monthly dues (GH₵ 50.00).\n- Officially recognized youth reaching age 16 eligible for portal registration.\n- Meeting adjourned at 5:45 PM with closing Ga and English benediction.",
        "completed",
        23
    ))
    past_meeting_id = cursor.lastrowid

    # Seed RSVP & Attendance for upcoming meeting
    cursor.execute("INSERT INTO attendance (meeting_id, member_id, rsvp_status) VALUES (?, ?, ?)", (upcoming_meeting_id, member_ids["admin@biggerfamily.org"], "attending"))
    cursor.execute("INSERT INTO attendance (meeting_id, member_id, rsvp_status) VALUES (?, ?, ?)", (upcoming_meeting_id, member_ids["kwesi.bigger@gmail.com"], "attending"))
    cursor.execute("INSERT INTO attendance (meeting_id, member_id, rsvp_status) VALUES (?, ?, ?)", (upcoming_meeting_id, member_ids["serwaa.bigger@outlook.com"], "attending"))
    cursor.execute("INSERT INTO attendance (meeting_id, member_id, rsvp_status) VALUES (?, ?, ?)", (upcoming_meeting_id, member_ids["abena.adobea@gmail.com"], "attending"))
    cursor.execute("INSERT INTO attendance (meeting_id, member_id, rsvp_status) VALUES (?, ?, ?)", (upcoming_meeting_id, member_ids["beatrice.bigger@yahoo.com"], "tentative"))

    # Seed Past meeting attendance
    for email, m_id in member_ids.items():
        attended_val = 1 if email not in ["kofi.jr@gmail.com"] else 0
        cursor.execute("INSERT INTO attendance (meeting_id, member_id, rsvp_status, attended) VALUES (?, ?, ?, ?)", (past_meeting_id, m_id, "attending", attended_val))

    # 6. Seed In-App Notifications
    notifs = [
        (
            None, # Broadcast
            "Upcoming Bi-Weekly Assembly #24",
            f"Reminder: Our next regular bi-weekly assembly takes place on {next_meeting_date} at 4:00 PM at Adabraka Family House (\"Ataa shi ɛfolo\") and via Zoom. Please RSVP your attendance.",
            "meeting",
            "normal",
            "/meetings"
        ),
        (
            None, # Broadcast
            "Monthly Dues for " + curr_label,
            f"Monthly welfare dues for {curr_label} (GH₵ 50.00) are currently being received for Adabraka, Abossey Okai, and Ofankor branches. Please send to MTN MoMo: 024 456 7890 (The Bigger Family Welfare).",
            "dues",
            "urgent",
            "/dues"
        ),
        (
            None, # Broadcast
            "Welcome New 16+ Members to Adabraka Headquarters!",
            "We are pleased to welcome Kofi Junior Bigger (16 yrs) and Akosua Serwaa Bigger registered under the Adabraka branch!",
            "member",
            "normal",
            "/family-tree"
        ),
        (
            member_ids["serwaa.bigger@outlook.com"],
            "Payment Receipt Under Review",
            "Your Telecel Cash dues payment for November 2026 has been submitted and is currently being verified by the Family Treasurer.",
            "dues",
            "normal",
            "/dues"
        )
    ]

    for m_id, title, msg, cat, prio, link in notifs:
        cursor.execute('''
            INSERT INTO notifications (member_id, title, message, category, priority, action_link)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (m_id, title, msg, cat, prio, link))

    conn.commit()
    conn.close()
    print("Seed data with Adabraka Headquarters ('Ataa shi ɛfolo'), Abossey Okai, and Ofankor branches successfully populated!")

if __name__ == '__main__':
    seed()
