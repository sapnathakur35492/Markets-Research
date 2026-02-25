# Markets NXT Backend

A robust Django backend for managing market research reports, leads, and automated workflows.

## Features

- **Bulk Report Management**: Upload thousands of reports via Excel integration in the Admin panel.
- **Global Price Control**: Update prices for all or selected reports by a percentage globally.
- **SEO & URLs**: Auto-generating SEO-friendly slugs for reports and landing pages (Sample, Discount).
- **Lead Automation**: API endpoints to handle user inquiries and store them as Leads.
- **API First**: RESTful APIs for listing reports, categories, and report details.

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   pip install django djangorestframework django-cors-headers pandas openpyxl
   ```

2. **Database Setup**:
   ```bash
   python3 manage.py migrate
   ```

3. **Create Admin User**:
   ```bash
   python3 manage.py createsuperuser
   ```

4. **Run Server**:
   ```bash
   python3 manage.py runserver
   ```

## Usage

### Excel Upload
1. Login to Admin Panel (`/admin/`).
2. Go to **Reports**.
3. Click **"Import Reports via Excel"**.
4. Upload your Excel file. Ensure columns match: `Category`, `Title`, `Publish`, `Pages`, `Single User`, `Multi User`, `Corporate`, etc.

### Global Price Update
1. Select reports in the Admin list view.
2. Choose **"Update Prices Globally"** from the Actions dropdown.
3. Enter the percentage (e.g., `10` to increase by 10%).

### Inquiry
- **Endpoint**: `POST /api/leads/inquiry/`
- **Body**:
  ```json
  {
      "full_name": "John Doe",
      "email": "john@example.com",
      "lead_type": "SAMPLE|DISCOUNT|CONTACT",
      "message": "Interested in this report."
  }
  ```

## Project Structure

```
market_research/
├── manage.py              # Django CLI entry point
├── requirements.txt       # Python dependencies
├── market_research_backend/ # Project Configuration
│   ├── settings.py        # Global settings (Apps, DB, Email)
│   ├── urls.py            # Main URL routing
│   └── sitemaps.py        # SEO Sitemap logic
├── reports/               # Core App: Report Mgmt & Excel Engine
│   ├── models.py          # Report & Category Modules
│   ├── admin.py           # Excel Import & Price Update Logic
│   └── views.py           # Reports API
├── leads/                 # App: Forms & Automation
│   ├── models.py          # Lead Database
│   └── views.py           # Email Trigger Logic
├── blog/                  # App: SEO Blog System
└── pages/                 # App: Static Pages (About, Privacy)
```
