# UniAGORA — Universities App

The `universities` app owns the **University** entity used throughout the UniAGORA backend.

A university is the foundational scoping entity for the marketplace. It anchors:

* User university selection
* Vendor university eligibility
* Product university visibility
* Multi-university marketplace separation

The app is intentionally small and focused. It owns the university entity and its lifecycle, while cross-domain university relationships and university-scoped filtering remain owned by their respective apps.

---

## Status

**Implemented · Reviewed · Green**


### Quality Status

* App test suite: **66/66 passing**
* Source coverage: **100%**
* Lint: **clean**
* Migration consistency: **clean**
* Public symbol imports: **verified**
* Full UniAGORA project suite: **871/871 passing** at MVP completion

The implementation test suite covers models, managers, serializers, services, views, permissions, API response envelopes, lifecycle transitions, soft deletion, slug behavior, and logo update semantics.

---

# 1. Responsibilities

The `universities` app owns:

* The `University` model
* University creation
* University updates
* University activation/deactivation
* University read APIs
* Admin write APIs
* University-specific managers/querysets
* Django admin registration

The app deliberately does **not** own:

| Concern                                 | Owner            |
| --------------------------------------- | ---------------- |
| `User.active_university`                | `users`          |
| Vendor university assignment            | `vendors`        |
| Matric-number uniqueness per university | `vendors`        |
| University-scoped marketplace filtering | `core`           |
| Generic response envelopes              | `common`         |
| Generic exceptions                      | `common`         |
| Generic pagination                      | `common`         |
| Authentication/JWT                      | `authentication` |

This preserves the frozen architecture's app-boundary rule. The DDS explicitly defines `universities` as owning only `University` and depending on `common`.

---

# 2. Architecture Position

The implementation follows the approved dependency direction:

```text
                         UniAGORA
                            │
              ┌─────────────┴─────────────┐
              │                           │
           common                       core
              │                           │
              └─────────────┬─────────────┘
                            │
                     universities
                            │
             ┌──────────────┼──────────────┐
             │              │              │
           users         vendors        products
```

`universities` is deliberately independent of the other domain apps.

It does not import or manipulate `User`, `VendorProfile`, `Product`, or other domain entities.

---

# 3. Data Model

## `University`

The model inherits from `common.models.BaseModel`.

Therefore, in addition to its domain fields, it receives the standard:

* `id` — UUID primary key
* `created_at`
* `updated_at`
* `is_deleted`

### Domain fields

| Field        | Type             | Required | Unique | Description                                                                   |
| ------------ | ---------------- | -------: | -----: | ----------------------------------------------------------------------------- |
| `name`       | `CharField(150)` |      Yes |    Yes | Full official university name                                                 |
| `short_name` | `CharField(20)`  |      Yes |    Yes | Short university identifier                                                   |
| `slug`       | `SlugField(160)` |      Yes |    Yes | URL-safe public identifier                                                    |
| `logo`       | Cloudinary field |       No |     No | Optional university branding                                                  |
| `is_active`  | `BooleanField`   |      Yes |     No | Whether the university is currently available for onboarding/public selection |

The DDS defines these fields and explicitly states that inactive universities are hidden from onboarding but are **not deleted**, allowing existing users/vendors to remain intact.

---

# 4. University Lifecycle

There are two independent concepts:

```text
is_active
is_deleted
```

They must not be treated as the same thing.

### Active

```text
is_active = True
is_deleted = False
```

The university is available through public/customer university endpoints.

### Inactive

```text
is_active = False
is_deleted = False
```

The university still exists in the database but is hidden from normal customer-facing university discovery.

### Soft deleted

```text
is_deleted = True
```

The database row remains intact.

Soft deletion is handled through the shared `BaseModel` behavior.

---

# 5. Managers & QuerySets

The app provides university-specific query helpers.

### `.active()`

Returns universities that are:

```text
is_active = True
AND
is_deleted = False
```

This is the queryset used for customer-facing university discovery.

### `.alive()`

Returns universities that are:

```text
is_deleted = False
```

An inactive but non-deleted university is therefore included.

This distinction is intentional:

```text
alive ≠ active
```

### `.dead()`

Returns soft-deleted universities:

```text
is_deleted = True
```

The default manager remains unfiltered to preserve the shared `BaseModel`/soft-delete contract. Explicit queryset methods should be used when a particular visibility state is required.

---

# 6. Slug Behavior

The university slug is generated automatically from the university name.

Example:

```text
name:
University of Ilorin

slug:
university-of-ilorin
```

### Slug rules

* Automatically generated when no explicit slug is supplied.
* Slug is unique.
* Slug remains stable after a university name is changed.
* Slug collisions are automatically deduplicated.

For example:

```text
University of Lagos
→ university-of-lagos

University of Lagos
→ university-of-lagos-2
```

An explicitly supplied slug is preserved rather than being overwritten.

This makes the slug suitable for stable public URLs while allowing university names to change without silently breaking existing routes. The implementation has dedicated tests for generation, immutability, collision handling, and explicit slugs.

---

# 7. Service Layer

Business operations are centralized in:

```text
UniversityService
├── create()
├── update()
├── activate()
└── deactivate()
```

Views do not directly implement university lifecycle business rules.

---

## `create()`

Creates a new university.

Accepted domain input:

```text
name
short_name
logo
```

The following are not client-controlled:

```text
slug
is_active
is_deleted
```

A newly created university is active by default.

---

## `update()`

Updates only explicitly supplied fields.

Supported fields:

```text
name
short_name
logo
```

The service deliberately does not modify:

```text
slug
is_active
is_deleted
```

### Logo semantics

There is an intentional distinction between:

```json
{}
```

and:

```json
{
  "logo": null
}
```

Omitting `logo` means:

> Leave the existing logo unchanged.

Providing:

```json
{
  "logo": null
}
```

means:

> Explicitly remove the existing logo.

This behavior is tested at serializer, service, and end-to-end API levels.

---

## `activate()`

Changes:

```text
is_active = False
```

to:

```text
is_active = True
```

Attempting to activate an already-active university raises the project's `ConflictError`, producing a `409 Conflict`.

---

## `deactivate()`

Changes:

```text
is_active = True
```

to:

```text
is_active = False
```

Attempting to deactivate an already-inactive university raises `ConflictError`.

Deactivation does **not**:

* Soft-delete the university
* Delete the university
* Modify users
* Modify vendors
* Modify products
* Cascade into other apps

This is intentional. The frozen DDS specifies that inactive universities remain intact and does not define a cross-domain deactivation cascade.

---

# 8. API

All API routes are mounted under:

```text
/api/v1/
```

The application follows UniAGORA's standard response envelope.

### Success

```json
{
  "success": true,
  "message": "",
  "data": {}
}
```

### Failure

```json
{
  "success": false,
  "message": "",
  "errors": {}
}
```

---

## 8.1 List Universities

### `GET /api/v1/universities/`

**Authentication:** Authenticated Customer

Returns active, non-deleted universities.

Customer-facing visibility therefore uses:

```text
University.objects.active()
```

Results use the project's standard pagination behavior.

---

## 8.2 Retrieve University

### `GET /api/v1/universities/<slug>/`

**Authentication:** Authenticated Customer

Returns a university by its slug.

Inactive or soft-deleted universities are not exposed through the public route.

Unknown or unavailable slugs return:

```text
404 Not Found
```

---

## 8.3 Create University

### `POST /api/v1/universities/`

**Authentication:** Admin

### Request

```json
{
  "name": "University of Ilorin",
  "short_name": "UNILORIN",
  "logo": null
}
```

`slug`, `is_active`, and `is_deleted` are not accepted as client-controlled fields.

### Response

Returns the created university representation.

---

## 8.4 Update University

### `PATCH /api/v1/universities/<slug>/`

**Authentication:** Admin

### Request

```json
{
  "name": "University of Ilorin",
  "short_name": "UNILORIN"
}
```

Supported writable fields:

```text
name
short_name
logo
```

`slug` and `is_active` cannot be modified through this endpoint.

`PUT` is also supported through the viewset's update behavior.

---

## 8.5 Activate University

### `POST /api/v1/universities/<slug>/activate/`

**Authentication:** Admin

Activates the university.

Attempting to activate an already-active university returns:

```text
409 Conflict
```

---

## 8.6 Deactivate University

### `POST /api/v1/universities/<slug>/deactivate/`

**Authentication:** Admin

Deactivates the university without deleting it.

Attempting to deactivate an already-inactive university returns:

```text
409 Conflict
```

---

## 8.7 Delete University

There is intentionally **no public DELETE endpoint**.

University deletion is not part of the MVP API.

The application instead relies on:

```text
deactivate
```

for removing a university from normal public visibility and the shared soft-delete infrastructure for internal deletion semantics.

This prevents an ordinary API operation from destructively removing the foundational entity referenced by users, vendors, and products.

---

# 9. Serialization

The app uses separate read and write concerns.

## `UniversitySerializer`

Read-only representation.

The documented response fields include:

```text
id
name
short_name
slug
logo
is_active
created_at
updated_at
```

All fields exposed by this serializer are read-only.

---

## `UniversityAdminWriteSerializer`

The only serializer accepting client input.

Writable fields:

```text
name
short_name
logo
```

The serializer deliberately excludes:

```text
id
slug
is_active
is_deleted
created_at
updated_at
```

DRF's generated uniqueness validators protect:

```text
name
short_name
```

before database persistence.

---

# 10. Authorization

| Operation             | Anonymous | Customer | Admin |
| --------------------- | --------: | -------: | ----: |
| List universities     |         — |        ✓ |     ✓ |
| Retrieve university   |         — |        ✓ |     ✓ |
| Create university     |         — |        — |     ✓ |
| Update university     |         — |        — |     ✓ |
| Activate university   |         — |        — |     ✓ |
| Deactivate university |         — |        — |     ✓ |

Superusers satisfy the project's Admin permission path.

The permission boundary follows the overall UniAGORA architecture: customer-facing access is read-oriented while administrative university management is restricted to Admin. The EDD confirms the full permission matrix was tested end-to-end.

---

# 11. Database Constraints

The following database-level uniqueness rules exist:

```text
UNIQUE(name)
UNIQUE(short_name)
UNIQUE(slug)
```

The DDS explicitly defines all three as unique.

The model also indexes:

```text
name
short_name
slug
is_active
```

The UUID primary key and standard timestamps/soft-delete fields come from `BaseModel`.

---

# 12. Django Admin

`University` is registered with Django Admin.

Administrative management can therefore be performed through the Django admin interface in addition to the API.

The app's admin registration is part of the tested implementation and is included in the source coverage verification.

---

# 13. App Structure

The implemented app follows a deliberately lightweight structure:

```text
apps/universities/
├── __init__.py
├── admin.py
├── apps.py
├── managers.py
├── models.py
├── serializers.py
├── services.py
├── urls.py
├── views.py
├── migrations/
│   └── 0001_initial.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_managers.py
    ├── test_serializers.py
    ├── test_services.py
    └── test_views.py
```

There is intentionally no unnecessary service package or additional domain abstraction.

The architecture describes this app as a thin university entity app with a thin administrative service because the university domain has no complex lifecycle.

---

# 14. Testing

The test suite is organized by responsibility.

### `test_models.py`

Covers:

* String representation
* Slug generation
* Slug stability
* Slug collision handling
* Explicit slug behavior
* Default activation state
* Database uniqueness
* Soft deletion
* Restoration
* Default ordering

### `test_managers.py`

Covers:

* `.active()`
* `.alive()`
* `.dead()`
* Interaction between active/inactive/deleted states

### `test_serializers.py`

Covers:

* Read-only response fields
* Valid writes
* Required fields
* Duplicate name/short-name validation
* Protection of server-controlled fields
* Partial-update semantics
* Explicit `logo: null`

### `test_services.py`

Covers:

* Creation
* Updates
* Slug generation
* Logo clearing
* Logo omission behavior
* Activation
* Deactivation
* Conflict handling
* Soft-delete preservation

### `test_views.py`

Covers:

* Authentication
* Customer/admin permissions
* List visibility
* Detail visibility
* Create
* Update
* Activate
* Deactivate
* Response envelope
* Pagination
* 404 behavior
* 409 behavior
* End-to-end activation/deactivation visibility

The implementation has documented full behavioral coverage across these layers.

---

# 15. Quality Gate

The universities app passed its dedicated implementation quality gate.

```text
Universities App
────────────────────────────────
Tests             66 / 66   PASS
Source coverage   100%      PASS
Lint              CLEAN     PASS
Migrations        CLEAN     PASS
Imports           CLEAN     PASS
Architecture      COMPLIANT PASS
────────────────────────────────
STATUS            GREEN
```

The final dedicated run recorded 66 passing tests and 100% source coverage across the app's non-test, non-migration Python files.

At MVP completion, the broader UniAGORA project suite is also green.

---

# 16. Important Engineering Decisions

## `is_active` is not directly writable

The admin write serializer does not expose `is_active`.

Instead:

```text
POST /universities/<slug>/activate/
POST /universities/<slug>/deactivate/
```

are the only API lifecycle operations.

This ensures state transitions pass through `UniversityService` and receive consistent conflict handling.

---

## Deactivation does not cascade

Deactivating a university only changes:

```text
University.is_active
```

It does not automatically suspend:

* Users
* Vendors
* Stores
* Products

No such cascade is defined by the frozen MVP requirements, so none was invented.

---

## University names and slugs are separate concerns

Changing:

```text
name
```

does not automatically change:

```text
slug
```

This preserves stable public URLs.

---

## Soft deletion remains distinct from deactivation

Deactivation means:

> "This university is currently unavailable."

Soft deletion means:

> "This record has been deleted logically."

These states are deliberately represented independently.

---

# 17. Integration With Other Apps

The `universities` app acts as a foundational reference entity.

### Users

```text
User.active_university
        │
        ▼
University
```

Users may select/change their active university through the `users` app.

The `universities` app does not own that assignment logic.

### Vendors

```text
VendorProfile.university
        │
        ▼
University
```

The vendor's university relationship is owned by `vendors`.

### Products

```text
Product.university
        │
        ▼
University
```

The product's university is intentionally denormalized for efficient marketplace scoping.

### Core

`core` provides the `ActiveUniversityFilterBackend` used by university-scoped domain queries.

`universities` provides the entity that those filters reference.

---

# 18. API Usage Examples

## List available universities

```http
GET /api/v1/universities/
Authorization: Bearer <access-token>
```

---

## Get a university

```http
GET /api/v1/universities/university-of-ilorin/
Authorization: Bearer <access-token>
```

---

## Create a university

```http
POST /api/v1/universities/
Authorization: Bearer <admin-access-token>
Content-Type: application/json

{
  "name": "University of Ilorin",
  "short_name": "UNILORIN"
}
```

---

## Update a university

```http
PATCH /api/v1/universities/university-of-ilorin/
Authorization: Bearer <admin-access-token>
Content-Type: application/json

{
  "short_name": "UNILORIN"
}
```

---

## Remove a logo

```http
PATCH /api/v1/universities/university-of-ilorin/
Authorization: Bearer <admin-access-token>
Content-Type: application/json

{
  "logo": null
}
```

---

## Deactivate

```http
POST /api/v1/universities/university-of-ilorin/deactivate/
Authorization: Bearer <admin-access-token>
```

---

## Reactivate

```http
POST /api/v1/universities/university-of-ilorin/activate/
Authorization: Bearer <admin-access-token>
```

---

# 19. Response Contract

A successful university response follows the global UniAGORA envelope:

```json
{
  "success": true,
  "message": "",
  "data": {
    "id": "uuid",
    "name": "University of Ilorin",
    "short_name": "UNILORIN",
    "slug": "university-of-ilorin",
    "logo": null,
    "is_active": true,
    "created_at": "2026-08-15T10:00:00Z",
    "updated_at": "2026-08-15T10:00:00Z"
  }
}
```

The exact `message` content is implementation-controlled by the shared response conventions.

---

# 20. Architecture Compliance

The implementation conforms to the UniAGORA architecture by:

* Owning only the `University` domain entity
* Depending on `common`
* Keeping business operations in `UniversityService`
* Keeping views thin
* Keeping serializers focused on API shape
* Reusing centralized permissions
* Reusing the shared response envelope
* Preserving soft-delete semantics
* Avoiding cross-app business logic
* Avoiding destructive DELETE APIs
* Keeping university activation/deactivation explicit
* Avoiding unsupported deactivation cascades
* Maintaining stable public slugs
* Preserving strict application boundaries



## Final Status

```text
┌─────────────────────────────────────────┐
│       UniAGORA Universities App         │
├─────────────────────────────────────────┤
│ Model                    ✓               │
│ Managers                 ✓               │
│ Serializers              ✓               │
│ Services                 ✓               │
│ API                      ✓               │
│ Permissions              ✓               │
│ Soft Delete              ✓               │
│ Activation Lifecycle     ✓               │
│ Slug Management          ✓               │
│ Tests                    ✓               │
│ Documentation            ✓               │
│ Architecture Compliance  ✓               │
├─────────────────────────────────────────┤
│ STATUS: IMPLEMENTED / GREEN             │
└─────────────────────────────────────────┘
