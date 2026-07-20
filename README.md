# LawPilot - Legal Case & Practice Management System

LawPilot is a comprehensive, multi-tenant Django-based legal case and practice management system. It enables law firms, attorneys, clients, and administrative staff to manage case lifecycle activities, client relations, hearings, tasks, invoices, and legal resources.

---

## 🚀 Features

- **Role-Based Dashboards**: Customized interfaces for Firm Owners, Senior Lawyers, Junior Lawyers, Clients, and Accountants.
- **Case Lifecycle Management**: Record case details, upload documents, track case histories, and schedule hearings.
- **Task Assignment & Tracking**: Delegate tasks to junior lawyers or specific team members and monitor completion.
- **Financial & Invoicing System**: Create client invoices, mark them as paid/unpaid, and track overall firm revenue.
- **Reporting & PDF Generation**: Generate dynamic reports (such as Case Status, Hearing Lists, Lawyer Workloads, and Monthly Filings) in PDF format using `ReportLab`.
- **Legal Library**: Search judgments, justice registers, and reference precedents to support case research.
- **Firm Multi-Tenancy**: Support for creating and managing multiple law firms, office profiles, and staff assignments.

---

## 🛠️ Tech Stack

- **Backend**: Django (Python)
- **Database**: SQLite (Development) / PostgreSQL-ready
- **Templating**: Django Template Language (HTML, Tailwind / Bootstrap CSS)
- **PDF Generation**: ReportLab
- **Data Handling**: Pandas & OpenPyXL

---

## 📋 Setup & Installation

Follow these steps to run the project locally on your machine:

### 1. Prerequisites
Ensure you have Python 3.10+ and Git installed on your system.

### 2. Create a Virtual Environment
Navigate to the project root directory and create a virtual environment:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install all required libraries using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 4. Database Migrations
Apply migrations to set up the database schema:

```bash
python manage.py migrate
```

### 5. Create a Superuser (Admin)
Create an administrative user to access the Django admin panel and manage firms:

```bash
python manage.py createsuperuser
```

### 6. Run the Development Server
Start the local server:

```bash
python manage.py runserver
```

Open your browser and navigate to `http://127.0.0.1:8000/` to access the application.

---

## 📂 Project Structure

- `accounts/`: User authentication, profile bio data, custom active user middleware, and permission classes.
- `cases/`: Core case management, client records, document version control, hearings, tasks, invoicing, and PDF reports generator.
- `firms/`: Setup and details for registered law firms and associated courts.
- `legal_library/`: Models and view search logic for judgment lists, justices, and import commands.
- `templates/`: Centralized directory for all HTML views, dashboards, components, and layouts.