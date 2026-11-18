# The Bigger Family Portal

An official, private web portal and ancestral registry built specifically for **The Bigger Family**.

- **Headquarters**: Adabraka Family House, Accra (*"Ataa shi ɛfolo"*)
- **Branches**: **Adabraka**, **Abossey Okai**, and **Ofankor**
- **Membership**: Strictly aged 16 and above
- **Welfare Dues**: Monthly contributions in Ghanaian Cedi (**GH₵ 50.00 / month**)
- **Assemblies**: Bi-weekly family meetings (**every 14 days**)
- **Notifications**: Instant in-app alerts and notifications

---

## 🌟 Core Features

### 1. Headquarters & The 3 Family Branches
1. **Adabraka Branch (Headquarters)**
   - Seat: *Adabraka Family House, Accra ("Ataa shi ɛfolo")*
   - Representative: Elder Kofi Kwabena Bigger
   - Role: Coordinates central family administration, heritage preservation, and hosts bi-weekly general meetings.
2. **Abossey Okai Branch**
   - Representative: Dr. Kwesi Samuel Bigger
   - Role: Uniting family members and business enterprises in Abossey Okai, Kaneshie, and surrounding areas.
3. **Ofankor Branch**
   - Representative: Deaconess Abena Adobea Bigger
   - Role: Uniting family members residing across Ofankor, Achimota, Pokuase, and greater Ga North.

### 2. Member Registration (Strict 16+ Rule)
- **Age Verification**: Registration enforces that members must be **at least 16 years of age**.
  - Real-time client-side calculation from Date of Birth with visual eligibility indicator.
  - Server-side Python age verification preventing underage registration.
  - Younger dependents can be registered through their parents' branch profile.
- **Lineage Connection**: Members choose their branch (Adabraka, Abossey Okai, Ofankor) and can link their immediate parent in the family.

### 3. Monthly Welfare Dues Management (GH₵)
- **Monthly Dues Cycle**: Fixed at **GH₵ 50.00 / month** per 16+ member.
- **Payment Channels**:
  - **MTN Mobile Money**: `024 456 7890` (Name: *The Bigger Family Welfare*)
  - **Telecel Cash / AT Money**: `020 812 3456`
  - **GCB Bank Transfer**: `1441002345678`
- **Member Self-Service**: Members submit their MoMo SMS transaction reference code for verification.
- **Admin Clearance**: Family Treasurer verifies references with 1-click approval.
- **Official Digital Receipts**: Downloadable and printable receipts (`REC-xxxxx`) featuring official family stamp.

### 4. Bi-Weekly Meetings (Every 2 Weeks)
- **Venue**: Hybrid (*Adabraka Family House "Ataa shi ɛfolo", Accra* + Virtual Zoom).
- **Automated 14-Day Recurrence**: Schedules meetings every two weeks (e.g., Assembly #23, #24, #25).
- **Interactive RSVP**: Members mark **Attending**, **Tentative**, or send an **Apology / Absent**.
- **Minutes & Resolutions Archive**: Records meeting minutes, action items, and roll-call attendance.

### 5. In-App Notification Center
- **Live Badge Counter**: Unread notification counter in the top navigation bar.
- **Categorized Feed**: Filter alerts by *Meetings*, *Monthly Dues*, *New 16+ Members*, and *Announcements*.
- **Admin Broadcast**: Family elders and administrators can broadcast urgent alerts to all members.

---

## 🚀 How to Run the Application

From the project directory:
```powershell
cd "THE_BIGGER_FAMILY_PORTAL"
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Demo Accounts for Testing

| Role | Name | Branch | Email | Password | Age / Notes |
|---|---|---|---|---|---|
| **Admin / Family Head** | Elder Kofi Kwabena Bigger | Adabraka (HQ) | `admin@biggerfamily.org` | `admin123` | Age 68, Full Admin |
| **Branch Leader** | Dr. Kwesi Samuel Bigger | Abossey Okai | `kwesi.bigger@gmail.com` | `password123` | Age 42, Physician |
| **Branch Leader** | Deaconess Abena Adobea Bigger | Ofankor | `abena.adobea@gmail.com` | `password123` | Age 61, Educationist |
| **Youth Member** | Akosua Serwaa Bigger | Adabraka | `serwaa.bigger@outlook.com` | `password123` | Age 19, Student |
| **Junior Member** | Kofi Junior Bigger | Adabraka | `kofi.jr@gmail.com` | `password123` | Age 16 (Newly 16+) |

---

## 🧪 Automated Testing
Run the automated test suite at any time:
```powershell
python "THE_BIGGER_FAMILY_PORTAL\test_portal.py"
```
*(7/7 tests passing)*
