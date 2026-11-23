# Blood Group Search System

A beginner-friendly Flask + SQLite implementation based on the uploaded Software Engineering Project Document.

## Features included
- Donor and requester registration and login
- Password hashing
- Donor profile management and availability updates
- Administrator verification of donor profiles
- Search verified donors by blood group, city, and availability
- Blood request creation and request-status management
- Basic in-app notifications
- Search history storage
- Role-based page access
- SQLite database created automatically

## Requirements
- Python 3.9 or newer
- pip

## Run on Windows
1. Extract this ZIP file.
2. Open the extracted `blood_group_search_system` folder in VS Code.
3. Open Terminal in VS Code.
4. (Recommended) Create a virtual environment:
   ```bash
   py -m venv venv
   venv\Scripts\activate
   ```
5. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
6. Start the website:
   ```bash
   python app.py
   ```
7. Open this address in Chrome:
   `http://127.0.0.1:5000`

The SQLite database file `blood_system.db` is created automatically the first time the app starts.

## Demo administrator
- Username: `admin`
- Password: `Admin@123`

Log in as admin to verify donor profiles and manage blood request statuses. Donors will not appear in requester searches until an administrator verifies their profiles.

## Typical demonstration flow
1. Register a donor account with a unique username.
2. Log out and register a requester account.
3. Log in using the administrator account and verify the donor.
4. Log in as requester and search using the donor's blood group and city.
5. Create a blood request.
6. Log in as admin and update its status.
7. Log in as donor and update availability in My Profile.

## Project structure
```text
blood_group_search_system/
├── app.py
├── requirements.txt
├── README.md
├── blood_system.db       # generated on first run
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── profile.html
    ├── search.html
    ├── request_form.html
    ├── admin_requests.html
    ├── notifications.html
    └── message.html
```

## Important notes
- This is an academic demonstration project, not a production healthcare service.
- Use only test data while developing. Do not enter real patient or donor information on a publicly accessible demo.
- Before deployment, set a strong random `SECRET_KEY`, disable Flask debug mode, use HTTPS, add CSRF protection, apply stricter validation and privacy controls, and arrange secure backups.
- Donor profile verification is an administrative workflow; it does not determine medical eligibility to donate blood.
- Contact details are shown to logged-in users with access to the donor search. Review privacy and consent requirements before real-world use.

## Document coverage
The implementation covers the document's main modules: login/authentication, donor management, blood group management through validated blood-group choices, blood request management, search/filtering, location, availability, notifications, search history, and basic administrator reporting through dashboard counts.
