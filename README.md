FoodShare+
==========

FoodShare+ is a Flask web application that helps connect people with surplus food to people who need food support. Users can sign in, submit donation listings, submit food requests, view active listings, and manage a basic profile.

The app uses SQLite for local storage and keeps uploaded images in the local `static/uploads` folder.

Features
--------

- User sign-in with protected pages
- Food donation submission form
- Food request submission form
- Donation and request listings page
- Basic user profile page
- SQLite data persistence
- Image upload support for common image formats
- Server-side validation for submitted forms
- Automated tests with `pytest`

Project Structure
-----------------

```text
.
+-- app.py
+-- requirements.txt
+-- README.md
+-- .env.example
+-- .gitignore
+-- static/
|   +-- asset/
|   +-- css/
|   +-- uploads/
+-- templates/
+-- tests/
```

Requirements
------------

- Python 3.10 or newer
- `pip`

Setup
-----

Open PowerShell in the project folder:

```powershell
cd "C:\Users\User\Documents\Creativity & Innovation"
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run The App
-----------

Start the Flask development server:

```powershell
python app.py
```

Open the app in your browser:

```text
http://127.0.0.1:5000/
```

Default Login
-------------

```text
Email: user@example.com
Password: mypassword
```

The default account is created automatically the first time the app runs.

Configuration
-------------

Optional environment variables are listed in `.env.example`.

```text
SECRET_KEY=replace-with-a-long-random-secret
DATABASE=instance/foodshare.sqlite
UPLOAD_FOLDER=static/uploads
DEFAULT_USER_EMAIL=user@example.com
DEFAULT_USER_PASSWORD=mypassword
FLASK_DEBUG=1
```

For local development, the default settings are enough. Before deploying the app, use a strong `SECRET_KEY` and change the default login credentials.

Run Tests
---------

```powershell
python -m pytest -q
```

Local Data
----------

The SQLite database is stored in:

```text
instance/foodshare.sqlite
```

Uploaded images are stored in:

```text
static/uploads/
```

Notes
-----

- This project is intended for local development and demonstration.
- The current UI uses fixed background images and layout positioning, so major CSS changes should be made carefully.
- Do not commit real passwords, private keys, local databases, or uploaded user files.
