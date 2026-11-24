# CareLedger: Web-Based Sickness and Drug Management System

A web application for clinics and health centres to record patient sicknesses and manage drug stock in one place. It replaces paper records with a single system that connects diagnosis, prescription, dispensing and inventory.

Project topic: **Design and Implementation of a Web-Based Sickness and Drug Management System**

---

## Problem

Many clinics still keep patient records and drug stock on paper. This leads to lost patient history, slow prescriptions, drugs running out unnoticed, expired drugs being kept or dispensed, and no easy way to see what is happening across the clinic.

## Objectives

- Record and store patient sickness and treatment history
- Manage drug inventory (stock levels, expiry dates, low-stock alerts)
- Handle prescriptions and dispensing, with stock updating automatically
- Provide role-based access for admin, doctor and pharmacist

## Features

**Accounts and roles**
- Login and logout
- Three roles: **Admin**, **Doctor**, **Pharmacist**, each limited to the pages they need
- Roles are assigned from the Django admin site

**Dashboard**
- Summary cards: patients, visits today, pending prescriptions, low or out-of-stock drugs, expired and expiring drugs
- Lists of pending prescriptions, drugs needing attention, and recent visits

**Patients**
- Register, edit and search patients
- Patient profile with full visit history
- Allergies recorded and shown as a warning on the profile, the visit form and the prescription

**Visits and prescriptions**
- Doctors record symptoms, diagnosis and notes
- Drugs can be added to a visit dynamically (drug, dosage, quantity)
- A drug cannot be prescribed beyond its available stock or after it has expired
- Prescription statuses: pending, dispensed, cancelled

**Drug inventory**
- Add, edit, delete and search drugs (name, category, quantity, reorder level, price, supplier, expiry date)
- Status flags: in stock, low stock, out of stock, expiring within 30 days, expired
- Filters for low or out of stock, expiring soon, and expired
- A drug that appears on a prescription cannot be deleted

**Dispensing**
- Pharmacist reviews a prescription and confirms dispensing
- A confirmation dialog shows exactly what will be deducted from stock
- Stock is deducted automatically, and the operation either fully succeeds or fully fails
- A prescription cannot be dispensed twice, and cannot be dispensed if a drug is expired or short on stock

**Interface**
- Responsive layout with a sidebar
- SweetAlert2 confirmations for irreversible actions and toast notifications for feedback
- Short GSAP animations (under 200 ms)
- Print receipt button on prescriptions

## Technology

| Part | Tool |
|---|---|
| Backend | Python, Django |
| Database | SQLite (Django default) |
| Environment | Pipenv |
| Frontend | HTML, CSS, JavaScript |
| Styling | Tailwind CSS (CDN) and custom CSS |
| Animation | GSAP (CDN) |
| Alerts | SweetAlert2 (CDN) |
| Icons | Lucide (CDN) |

The CDN libraries need an internet connection when the pages load.

## Workflow

1. A patient is registered
2. The doctor records the visit and diagnosis
3. The doctor prescribes drugs
4. The pharmacist sees the pending prescription and dispenses it
5. Drug stock reduces automatically
6. Admin monitors the dashboard for low-stock and expiring drugs

## Roles and permissions

| Action | Admin | Doctor | Pharmacist |
|---|:---:|:---:|:---:|
| View dashboard, patients, drugs, prescriptions | Yes | Yes | Yes |
| Register and edit patients | Yes | Yes | No |
| Record visits and prescribe | Yes | Yes | No |
| Add, edit and delete drugs | Yes | No | Yes |
| Dispense prescriptions | Yes | No | Yes |
| Cancel pending prescriptions | Yes | Yes | No |
| Manage users and roles | Yes | No | No |

## Project structure

```
myproject/            Django project (settings, root urls)
myapp/
  models.py           Profile, Patient, Visit, Drug, Prescription, PrescriptionItem
  forms.py            Forms and the prescription formset
  views.py            Page logic and role checks
  urls.py             App routes
  admin.py            Admin site setup (including user roles)
  management/commands/seed_demo.py   Optional demo data
  static/css/style.css               Colours and components
  static/js/brain.js                 Alerts, animations, dynamic prescription rows
  templates/          base, login, dashboard, drugs/, patients/, visits/, prescriptions/
```

## Getting started

Requirements: Python 3 and Pipenv.

```bash
# 1. Install dependencies and enter the environment
pipenv install django
pipenv shell

# 2. Create the database tables
python manage.py makemigrations myapp
python manage.py migrate

# 3. Create the first account (it becomes the Admin)
python manage.py createsuperuser

# 4. Optional: load sample drugs, patients and demo staff
python manage.py seed_demo

# 5. Run the server
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in.

### Setting roles

Log in at `/admin/`, open **Users**, choose a user, and set their **Role** (Doctor or Pharmacist). Superusers are always Admins.

### Demo accounts

`seed_demo` creates two sample staff accounts:

| Username | Role | Password |
|---|---|---|
| doctor1 | Doctor | Demo@12345 |
| pharmacist1 | Pharmacist | Demo@12345 |

Delete these accounts before submitting or deploying the project.

## Settings required

In `myproject/settings.py`:

```python
INSTALLED_APPS = [..., "myapp"]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
```

In `myproject/urls.py`:

```python
path("admin/", admin.site.urls),
path("", include("myapp.urls")),
```

## Limitations and future improvements

- Summary reports with charts (illness trends, drug usage)
- Export reports to PDF or Excel
- A managed list of diseases (diagnosis is currently free text)
- Password reset by email
- Patient self-service access
- A user-management screen inside the app (currently done through the Django admin)

## Security notes

- Passwords are hashed by Django
- Every page requires login, and access is checked by role
- Destructive actions (delete, dispense, cancel) accept POST requests only and are CSRF protected
- Before real deployment, set `DEBUG = False`, use a strong `SECRET_KEY`, configure `ALLOWED_HOSTS`, and move to a production database