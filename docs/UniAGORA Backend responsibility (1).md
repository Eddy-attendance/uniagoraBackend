## UniAGORA

## Backend Lead Responsibilities (Samad)

## Position Backend Lead



## Role Summary

You are responsible for designing, building and maintaining the entire backend of UniAgora.

The backend is the foundation of the platform and powers:

- Web Application

- Customer Mobile App

- Vendor Features

- Rider App

- Admin Dashboard

Your APIs will be consumed by all client applications.

## Technology Stack

You will use:

- Python

- Django

- Django REST Framework (DRF)

- PostgreSQL

- JWT Authentication

- Django Channels (Chat)

- Paystack

- Firebase Cloud Messaging

- Cloudflare R2

- Git & GitHub


# Primary Responsibilities

- 1. Backend Architecture

Design a clean Django project structure.

Create separate apps where appropriate, for example:

backend/

apps/

├── authentication/ ├── users/ ├── universities/ ├── stores/ ├── products/ ├── categories/ ├── cart/ ├── orders/ ├── payments/ ├── wallet/ ├── deliveries/ ├── chat/ ├── notifications/ ├── reviews/

└── admin_dashboard/

Every app should have a clear responsibility.

- 2. Database

Implement the approved database.

Responsible for:


- Models

- Relationships

- Constraints

- Migrations

- Query optimisation

Never change the database structure without approval from the Technical Lead.

- 3. Authentication

Implement:

- Register

- Login

- Logout

- Forgot Password

- Reset Password

- Email Verification

- JWT Authentication

Support the following roles:

- Customer

- Vendor

- Rider

- Admin

Authentication should be centralised so every client uses the same system.

## 4. API Development

Develop REST APIs for:

## Users

- Register

- Login

- Profile


- Update Profile

## Stores

- Create Store

- Edit Store

- Delete Store

- View Store

## Products

- CRUD

- Images

- Inventory

- Search

- Filtering

## Categories

- CRUD

## Cart

- Add Item

- Remove Item

- Update Quantity

- View Cart

## Orders

- Create Order

- Cancel Order

- Order Details

- Order Tracking


## Payments

- Paystack Initialisation

- Verification

- Payment Status

## Wallet

- Balance

- Transactions

- Withdrawals

## Deliveries

- Rider Assignment

- Status Updates

- Delivery Completion

## Chat

- Conversations

- Messages

- Read Receipts

## Notifications

- Push Notifications

- Order Notifications

- Chat Notifications

## Reviews

- Product Reviews

- Vendor Ratings


- Rider Ratings

## Admin

- Users

- Vendors

- Riders

- Orders

- Reports

## 5. Business Logic

The backend owns all business rules.

Examples:

Escrow

Order Validation

↓

Wallet Calculations

↓

Withdrawal Rules

↓

Role Permissions

↓

Review Eligibility

The frontend must never implement these rules.

## 6. Security

Responsible for:

- JWT Security

- Password Hashing


- Input Validation

- Permission Checks

- Rate Limiting

- Secure File Uploads

- API Protection

## 7. API Standards

Every endpoint should follow the same structure.

Example:

{

"success": true,

"message": "Product created successfully.",

"data": {}

}

Errors should follow a consistent format:

{

"success": false,

"message": "Validation failed.",

"errors": {}

}

Consistency makes frontend integration much easier.

## 8. API Documentation

For every endpoint, document:

- Method

- URL

- Authentication required

- Request body

- Response


- Error responses

```
Example:
POST /api/v1/auth/login
Request
{
"email": "",
"password": ""
}
Response
{
"success": true,
"token": "...",
"user": {}
}
```

This documentation should be updated whenever an endpoint changes.

## 9. Collaboration with Frontend

To ensure smooth integration:

## Before building an endpoint

- Review the related Figma screen.

- Understand what data the frontend needs.

## Before changing an API

- Inform the Technical Lead.

- Update the API documentation.

## Never

- Rename response fields without agreement.

- Change endpoint URLs without approval.

- Return inconsistent data structures.

The frontend should be able to consume every endpoint predictably.


## 10. Git Workflow

For every feature:

Create Feature Branch

Develop Feature

↓

Test

↓

Push

↓

Create Pull Request

↓

Technical Review

↓

Merge

Example branch names:

feature/authentication

feature/products

feature/orders

feature/chat

## Coding Standards

- Follow Django best practices.

- Keep apps modular.

- Use meaningful names.

- Separate business logic from views.

- Reuse code where appropriate.

- Handle exceptions consistently.


- Keep code readable and maintainable.

## Testing

Before submitting work:

- Test all endpoints.

- Validate inputs.

- Test authentication.

- Verify permissions.

- Test edge cases.

- Confirm response formats.

## Definition of Done

A backend feature is complete only when:

- Models are complete.

- Migrations run successfully.

- Business logic is implemented.

- Endpoints are tested.

- API documentation is updated.

- Responses follow the agreed standard.

- Code has been reviewed and approved.

## Sprint 1 Deliverables

Week 1:

- Initialise Django project.

- Configure PostgreSQL.

- Set up Django REST Framework.

- Configure JWT authentication.

- Create the project structure.

- Implement authentication.


- Create the initial database models.

- Set up API documentation.

Week 2:

- Build Categories APIs.

- Build Stores APIs.

- Build Products APIs.

- Begin Cart module.

## Working Relationship with the Frontend

The frontend and backend should progress feature by feature, not independently.

Example:

## Feature Ronnie (Frontend) Sammad (Backend)

Login

Register

Home

Product Details Product Screen Product Details API

Cart

Checkout

This ensures that when a frontend screen is complete, the matching backend API is also ready, making integration straightforward.

Design + Build UI Login API

Design + Build UI Register API

Build Homepage Products & Categories API

Cart UI

Cart API

Checkout UI

Order & Payment API
