🧸 E-Commerce Toy Store (Django Project)

A full-stack E-Commerce Toy Store Web Application built using Python (Django), HTML, CSS, and SQLite.
The platform allows users to browse toys, view product details, add items to their cart, and place orders through a simple and user-friendly interface.

This project demonstrates backend development using Django, database management using SQLite, and frontend implementation with HTML and CSS.

🚀 Features

User Registration and Login

Browse Toys by Category

Product Detail Page

Add to Cart Functionality

Order Placement

Admin Panel for Product Management

Responsive and Clean UI

SQLite Database Integration

🛠️ Tech Stack

Backend

Python

Django Framework

Frontend

HTML

CSS

Database

SQLite

📂 Project Structure
toy_store/
│
├── toy_store/        # Main Django project folder
├── store/            # Application folder
├── templates/        # HTML templates
├── static/           # CSS and static files
├── db.sqlite3        # SQLite database
├── manage.py
└── requirements.txt
⚙️ Installation
1️⃣ Clone the Repository
git clone https://github.com/yourusername/toy-store-django.git
cd toy-store-django
2️⃣ Create Virtual Environment
python -m venv venv

Activate it:

Windows

venv\Scripts\activate

Mac/Linux

source venv/bin/activate
3️⃣ Install Dependencies
pip install -r requirements.txt
4️⃣ Apply Migrations
python manage.py makemigrations
python manage.py migrate
5️⃣ Create Superuser
python manage.py createsuperuser
6️⃣ Run Development Server
python manage.py runserver

Open in browser:

http://127.0.0.1:8000/
🧑‍💻 Admin Panel

Access the Django admin panel:

http://127.0.0.1:8000/admin/

From here you can:

Add Toys

Manage Products

View Orders

Manage Users

📸 Future Improvements

Online Payment Integration

Product Search & Filters

Wishlist Feature

Product Reviews & Ratings

REST API with Django REST Framework

Deployment on AWS / Heroku

📄 License

This project is developed for learning and educational purposes.
