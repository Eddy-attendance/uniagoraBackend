# UniAGORA Backend

> The official backend API for **UniAGORA** — a modern multi-university student marketplace built with Django and Django REST Framework.

## 🚀 Overview

UniAGORA is a campus marketplace platform designed to connect students within their universities. It enables students to discover products, become vendors, communicate with buyers, and build trusted campus businesses through a secure and scalable platform.

This repository contains the backend services powering the UniAGORA ecosystem.

> **Project Status:** 🚧 Active Development (Bootstrap Phase)

---

## ✨ Core Features

* Multi-university architecture
* Secure JWT authentication
* Student and vendor accounts
* Product listings and management
* Store management
* Product categories
* Real-time messaging (Django Channels)
* Reviews and ratings
* Reporting and moderation
* RESTful API
* OpenAPI documentation
* Cloud media storage
* PostgreSQL database

---

## 🛠 Tech Stack

### Backend

* Python 3.12+
* Django 5
* Django REST Framework
* PostgreSQL
* Django Channels
* SimpleJWT

### Storage

* Cloudinary

### Documentation

* DRF Spectacular (OpenAPI)

### Development Tools

* Ruff
* Pre-commit
* Pytest

---

## 📁 Project Structure

```text
UniAGORA/
├── apps/
│   ├── admin_dashboard/
│   ├── authentication/
│   ├── categories/
│   ├── chat/
│   ├── common/
│   ├── core/
│   ├── notifications/
│   ├── products/
│   ├── reports/
│   ├── reviews/
│   ├── stores/
│   ├── universities/
│   ├── users/
│   └── vendors/
│
├── config/
├── requirements/
├── manage.py
└── README.md
```

---

## ⚙️ Getting Started

### Clone the repository

```bash
git clone git@github.com:Eddy-attendance/uniagoraBackend.git
cd uniagoraBackend
```

### Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements/dev.txt
```

### Configure environment variables

Create a `.env` file using `.env.example`.

### Apply migrations

```bash
python manage.py migrate
```

### Start the development server

```bash
python manage.py runserver
```

---

## 🏗 Development Workflow

Development follows a structured engineering process:

1. Plan the implementation.
2. Review the architecture.
3. Implement one application at a time.
4. Review code quality and security.
5. Merge after approval.

---

## 📌 Current Progress

* [x] Repository initialized
* [x] Django project bootstrapped
* [x] PostgreSQL configured
* [x] Modular settings
* [x] Project structure established
* [x] Development tooling configured
* [x] Shared infrastructure (`common & core`)
* [x] Users
* [x] Authentication
* [x] Universities
* [x] Vendors
* [x] Stores
* [x] Products
* [ ] Chat
* [ ] Reviews
* [ ] Notifications
* [ ] Production deployment

---

## 🤝 Contributing

This project is currently under active development.

Contribution guidelines, coding standards, and pull request requirements will be published as development progresses.

---

## 📄 License

License information will be added before the first public release.

---

## 👨‍💻 Backend Author

**Abdulsalam Abdulsomad Abdulkadir**

Computer Engineering Student • Backend Engineer

---

## ⭐ Vision

To build the most trusted campus commerce platform, empowering students to buy, sell, and grow businesses safely within their university communities.
