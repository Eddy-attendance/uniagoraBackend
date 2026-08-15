# Core App

The **`core`** app contains **domain-aware, cross-cutting concerns** shared across the UniAGORA backend.

Unlike the `common` app, which provides generic infrastructure, `core` contains logic that understands the application's business domain while remaining independent of any specific feature module.

The app owns **permission classes** and the **university-scoping filter backend**, ensuring authorization and data isolation remain consistent across the platform.

---

## Responsibilities

The `core` app is responsible for:

- Domain-aware permission classes
- University-scoping queryset filtering
- Shared authorization logic
- Cross-cutting business-aware utilities

The app **does not own**:

- Models
- Database migrations
- API endpoints
- Business services
- Serializers
- Views

---

## Architecture Position

```
common
   │
   ▼
core
   │
   ├──────────────┐
   ▼              ▼
authentication   universities
users           vendors
stores          products
chat            reviews
reports         notifications
```

`common` provides generic infrastructure.

`core` builds on that infrastructure with business-aware components that can be reused throughout every domain app.

---

## Directory Structure

```
core/
├── apps.py
├── permissions.py
├── filters.py
└── tests/
```

---

# Permissions

## IsAuthenticatedCustomer

Allows access to any authenticated user.

Within UniAGORA every registered account is automatically a Customer, therefore no additional role check is required.

Used as the base permission for authenticated endpoints.

---

## IsVerifiedVendor

Allows access only to authenticated users with a verified vendor profile.

Checks the documented vendor interface rather than importing vendor models directly.

This keeps the app independent of future domain implementations.

---

## IsOwnerVendor

Object-level permission that ensures a vendor only manages resources they own.

Ownership is derived from:

- the authenticated user
- the object's owner

Client-supplied vendor identifiers are never trusted.

Currently supports ownership resolution for:

- Store
- Product

The ownership resolver is intentionally extensible for future vendor-owned resources.

---

## IsAdmin

Allows access to platform administrators.

Authorization is based on Django's built-in:

- `is_staff`
- `is_superuser`

No additional platform-specific admin flag is introduced.

---

# Filter Backend

## ActiveUniversityFilterBackend

Automatically scopes querysets to the authenticated user's active university.

This enforces UniAGORA's strict university isolation without requiring individual views to repeat filtering logic.

By default the backend filters using:

```
university
```

Views may override the lookup field when required.

Example:

```python
class ProductViewSet(ModelViewSet):
    filter_backends = [ActiveUniversityFilterBackend]
```

---

# Design Principles

The implementation follows the frozen Backend Architecture and DDS.

Key principles include:

- No domain models are imported.
- No circular dependencies are introduced.
- Authorization is centralized.
- Ownership is derived from authenticated state.
- University scoping is enforced consistently.
- Security defaults to least privilege.

---

# Security Considerations

## Ownership Verification

Ownership is determined from the authenticated user.

The permission classes never trust:

- request body IDs
- query parameters
- URL identifiers

when determining ownership.

---

## University Isolation

Queries are automatically restricted to the requesting user's active university.

If no active university is available, the backend returns an empty queryset rather than exposing data from other universities.

This fail-closed behaviour prevents accidental cross-university data leakage.

---

# Dependencies

The app depends only on:

- Django
- Django REST Framework

It intentionally avoids importing application models from later apps in the build order.

---

# Testing

The app includes comprehensive unit tests covering:

- Authentication permissions
- Vendor verification
- Ownership checks
- Admin authorization
- University filtering
- Edge cases
- Security scenarios

# Future Extensibility

The app is designed to accommodate future growth without architectural changes.

Potential future additions include:

- Additional permission classes
- Additional cross-cutting filter backends
- Shared authorization helpers
- Domain-aware reusable components

These additions should continue to respect the established application boundaries and avoid introducing domain ownership into the `core` app.

---

# Status

**Status:** Complete ✅
