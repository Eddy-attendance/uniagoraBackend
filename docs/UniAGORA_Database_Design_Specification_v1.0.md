# UniAGORA — Database Design Specification (DDS)

**Version:** 1.0
**Status:** Draft — pending CTO architecture review
**Derived from:** UniAGORA PRD v1.0 (MVP) + UniAGORA Backend Architecture v2.0 FINAL (frozen)

---

## 1. Overview

### 1.1 Purpose

This document is the Phase 2 deliverable of the UniAGORA backend engineering engagement. It translates the **frozen** Backend Architecture (v2.0) into a complete, implementation-ready **Database Design Specification**. It is the single blueprint engineers use to write models, migrations, serializers, services, and APIs — no architectural decisions are re-litigated here.

### 1.2 Scope

In scope: every persisted entity required by the MVP as defined in the PRD and confirmed product decisions, organized by the eleven domain-owning Django apps (`universities`, `authentication`, `users`, `vendors`, `stores`, `categories`, `products`, `chat`, `reviews`, `reports`, `notifications`) plus the two infrastructure apps (`common`, `core`) and the model-less `admin_dashboard` facade.

Out of scope (unchanged from architecture): Cart, Order, Payment, Wallet, Delivery, Rider, Escrow, Service Marketplace, Hostel Listings, Event Tickets, Coupons, AI Recommendations, Multi-Campus Logistics. No table, field, or enum value in this document services any of these.

### 1.3 Relationship to the Frozen Architecture

This DDS does not alter app boundaries, dependency rules, design patterns, or the eleven-app build order established in the architecture document. Every model listed here maps to the app that owns it per the architecture's "Final App Boundaries" table. Where the architecture specified a decision (e.g., matric uniqueness scope, `Product.status` as an enum, `Conversation.transaction_status` as the review-eligibility anchor), that decision is reproduced verbatim and expanded into field-level detail — never changed.

### 1.4 Guiding Principles

- **UUID primary keys** throughout, via `BaseModel`.
- **Soft deletion by default** (`is_deleted` on `BaseModel`) — hard deletes reserved for genuinely dependent rows explicitly noted below.
- **One migration-safe source of truth per fact** — denormalized fields are documented and justified individually, never silent.
- **Service-layer enforced invariants are backed by DB-level constraints wherever PostgreSQL can express them** ("service-enforced + DB backstop"), so data integrity never depends solely on application code being bug-free.
- **Every nullable relationship, cascade choice, and index has a stated reason** — nothing is nullable or indexed "just in case."

---

## 2. Entity Relationship Diagram (ERD)

```
                         ┌───────────────┐
                         │  University   │
                         └───────┬───────┘
                                 │ 1
                    ┌────────────┼─────────────────┐
                    │ N                             │ N (locked at application)
             ┌──────▼──────┐                 ┌──────▼────────┐
             │    User     │                 │ VendorProfile │
             │(active_univ │◄──1:1───────────┤               │
             │  nullable)  │                 └──────┬────────┘
             └──────┬──────┘                        │ 1:1
                     │                        ┌──────▼──────┐
                     │                        │    Store     │
                     │                        └──────┬───────┘
                     │                               │ 1:N
                     │                        ┌──────▼───────┐        ┌────────────┐
                     │                        │   Product    │──N:M──►│  Category  │
                     │                        │ (university  │  via   │ (self-FK   │
                     │                        │ denormalized)│ Product │  parent)  │
                     │                        └──────┬───────┘Category└────────────┘
                     │                               │ 1:N
                     │                        ┌──────▼───────┐
                     │                        │ ProductImage │
                     │                        └──────────────┘
                     │
                     │        ┌────────────────────┐
                     ├───1:N─►│    VendorDocument   │◄──N:1── VendorProfile
                     │        └────────────────────┘
                     │
                     │  (customer)          (vendor)
                     │      N                  N
             ┌───────▼──────────────────────────▼────────┐
             │                Conversation                 │
             │   FK product (nullable) │ transaction_status│
             └───────┬─────────────────────────┬──────────┘
                      │ 1:N                     │ 1:1 (unique)
               ┌──────▼──────┐           ┌──────▼──────┐
               │   Message   │           │   Review    │
               └──────┬──────┘           │ (store FK   │
                      │ 1:1              │ denormalized)│
             ┌────────▼─────────┐        └─────────────┘
             │ MessageAttachment│
             │ (schema-ready,   │
             │  unused in MVP)  │
             └──────────────────┘

             ┌────────────┐        exactly one of the two FKs
   User ──1:N│   Report   │N:1── Product (nullable)
             │            │N:1── VendorProfile (nullable)
             │resolved_by │N:1── User (nullable, admin)
             └────────────┘

   User ──1:N── Notification
   User ──1:N── DeviceToken
```

**Relationship summary:**

| Relationship | Cardinality | Nullable? | Through / Notes |
|---|---|---|---|
| University → User (active_university) | 1:N | Yes (nullable until onboarding) | Direct FK on `User` |
| University → VendorProfile | 1:N | No (locked at application time) | Direct FK |
| User → VendorProfile | 1:1 | N/A | `OneToOneField` |
| VendorProfile → Store | 1:1 | N/A | `OneToOneField` |
| VendorProfile → VendorDocument | 1:N | N/A | Direct FK |
| Store → Product | 1:N | No | Direct FK |
| Product → Category | N:M | N/A | Through table `ProductCategory` |
| Category → Category (parent) | 1:N (self) | Yes (root categories) | Self-referential FK |
| Product → ProductImage | 1:N | N/A | Direct FK |
| Product → University | N:1 (denormalized) | No | Set once at creation |
| User (customer) → Conversation | 1:N | No | Direct FK |
| VendorProfile → Conversation | 1:N | No | Direct FK |
| Product → Conversation | 1:N | Yes | Direct FK, conversation may be store-level |
| Conversation → Message | 1:N | N/A | Direct FK |
| Message → MessageAttachment | 1:1 | N/A (row itself optional) | `OneToOneField`, unused in MVP |
| Conversation → Review | 1:1 (unique) | N/A | `OneToOneField`, eligibility-gated |
| Store → Review | N:1 (denormalized) | No | Set once at creation |
| User → Report | 1:N | N/A | Direct FK (`reporter`) |
| Product → Report | N:1 | Yes | Exactly one of Product/VendorProfile set |
| VendorProfile → Report | N:1 | Yes | Exactly one of Product/VendorProfile set |
| User (admin) → Report (resolved_by) | N:1 | Yes | Set only on resolution |
| User → Notification | 1:N | No | Direct FK (`recipient`) |
| User → DeviceToken | 1:N | No | Direct FK |

---

## 3. Applications and Owned Models

| App | Owned Models | Responsibilities | Depends On |
|---|---|---|---|
| `common` | *(none — abstract only)* `BaseModel` (abstract) | UUID PK, timestamps, soft-delete, response envelope, pagination, generic Cloudinary field | Nothing domain-specific |
| `core` | *(none)* | Domain-aware permission classes, `ActiveUniversityFilterBackend` | `users`, `vendors`, `universities` (models only, read-only import) |
| `universities` | `University` | University entity, active/inactive status | `common` |
| `authentication` | *(none persisted — see §13 Assumptions)* | Register/login/logout, JWT issuance, password reset flow | `users` |
| `users` | `User` | Identity, credentials, `active_university` selection | `common`, `universities` |
| `vendors` | `VendorProfile`, `VendorDocument` | Vendor identity, verification lifecycle, proof-of-studentship/business docs | `common`, `users`, `universities` |
| `stores` | `Store` | Public storefront profile (1:1 with Vendor) | `common`, `vendors` |
| `categories` | `Category` | Hierarchical category tree | `common` |
| `products` | `Product`, `ProductImage`, `ProductCategory` | Listings, images, inventory, lifecycle/expiry, search composition | `common`, `stores`, `categories`, `universities` |
| `chat` | `Conversation`, `Message`, `MessageAttachment` | Customer→Vendor messaging, transaction-completion flag | `common`, `users`, `vendors`, `products` |
| `reviews` | `Review` | Reviews gated on completed transactions | `common`, `chat`, `stores` |
| `reports` | `Report` | Product/vendor report lifecycle | `common`, `users`, `products`, `vendors` |
| `notifications` | `Notification`, `DeviceToken` | Notification records, device tokens, dispatch abstraction | `common`, `users` |
| `admin_dashboard` | *(none)* | Read/aggregation facade over other apps' services | All domain apps (read-only) |

---

## 4. Model Specifications

> Every model below implicitly inherits from `BaseModel` (`common.models.BaseModel`), which supplies: `id` (UUIDField, primary_key, default=uuid4, editable=False), `created_at` (DateTimeField, auto_now_add), `updated_at` (DateTimeField, auto_now), `is_deleted` (BooleanField, default=False, indexed). These four fields are **not repeated** in the field tables below unless a model needs non-default behavior on one of them.

### 4.1 `University` (app: `universities`)

**Purpose:** Represents a supported university/campus. Anchors user scoping, vendor eligibility, and product visibility boundaries per the "strict university scoping" product decision.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `name` | CharField(150) | No | No | Yes | — | Yes | Full official name, e.g. "University of Ibadan" |
| `short_name` | CharField(20) | No | No | Yes | — | Yes | e.g. "UI" — used in UI chips/badges |
| `slug` | SlugField(160) | No | No | Yes | auto from `name` | Yes | URL-safe identifier |
| `logo` | Cloudinary field (via `common.fields`) | Yes | Yes | No | None | No | Optional branding asset |
| `is_active` | BooleanField | No | No | No | True | Yes | Inactive universities are hidden from onboarding but never deleted (existing users/vendors remain intact) |

**Relationships:** None outbound. Inbound: `User.active_university`, `VendorProfile.university`, `Product.university` (denormalized).

**Constraints:** `UNIQUE(name)`, `UNIQUE(short_name)`, `UNIQUE(slug)`.

**Model Methods:** `__str__` returns `short_name`. No business-logic methods — university activation/deactivation is an admin service concern.

---

### 4.2 `User` (app: `users`)

**Purpose:** The single identity record for every account (Customer by default; Vendor and Admin are role extensions, not separate tables). Custom user model to support UUID PK and email-based auth.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Validation |
|---|---|---|---|---|---|---|---|
| `email` | EmailField | No | No | Yes | — | Yes | Django email validator; case-insensitively unique via `CIEmailField` or a normalized-lowercase save hook |
| `password` | CharField (inherited from `AbstractBaseUser`) | No | No | No | — | No | Hashed via Django's password hashers |
| `full_name` | CharField(150) | No | No | No | — | No | Display name |
| `phone_number` | CharField(20) | Yes | Yes | No | None | No | E.164-ish format validated at serializer level |
| `active_university` | FK → `University` | Yes | Yes | No | None | Yes | Nullable until onboarding completes; changeable anytime per product decision |
| `is_active` | BooleanField | No | No | No | True | No | Django auth framework field — account enabled/disabled |
| `is_staff` | BooleanField | No | No | No | False | No | Django admin-site access only, not the platform "Admin" role |
| `date_joined` | DateTimeField | No | No | No | now | No | Kept alongside `created_at` for Django auth compatibility |

**Relationships:** `active_university` → `University` (`on_delete=PROTECT`, `related_name="users"`). Inbound 1:1 with `VendorProfile`; inbound 1:N as `Conversation.customer`, `Report.reporter`, `Review` (via conversation), `Notification.recipient`, `DeviceToken.user`.

**Role Determination (not stored):** `is_vendor` and `is_admin` are **computed properties**, not columns — `is_vendor = hasattr(self, "vendor_profile")`, `is_admin` derived from a dedicated `Group`/`is_staff`+role check per the architecture's "never a redundant/denormalized flag" rule.

**Constraints:** `UNIQUE(email)` (case-insensitive).

**Model Methods:** `__str__` returns email; `is_vendor` / `is_admin` properties (read-only, no side effects — legitimate model-level computed properties, not business workflows).

---

### 4.3 `VendorProfile` (app: `vendors`)

**Purpose:** Represents a Customer's upgrade to Vendor status. Holds identity/eligibility data and verification lifecycle. Split from `Store` because this data (matric number, business address, documents) is sensitive/administrative, while `Store` is the public-facing profile.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `user` | OneToOneField → `User` | No | No | Yes | — | Yes (implicit via unique) | One vendor profile per account |
| `university` | FK → `University` | No | No | No | — | Yes (composite, see §6) | Locked at application time — not synced with `User.active_university` afterward |
| `vendor_type` | CharField(20), choices=`VendorType` | No | No | No | — | Yes | `STUDENT` / `BUSINESS` |
| `store_name` | CharField(150) | No | No | No | — | No | Required for both vendor types |
| `phone_number` | CharField(20) | No | No | No | — | No | Required for both vendor types |
| `matric_number` | CharField(30) | Yes | Yes | No (composite unique, see Constraints) | None | Yes (composite) | Required & validated only when `vendor_type=STUDENT` |
| `department` | CharField(100) | Yes | Yes | No | None | No | Student vendors only |
| `level` | CharField(10) | Yes | Yes | No | None | No | Student vendors only, e.g. "300" |
| `business_name` | CharField(150) | Yes | Yes | No | None | No | Business vendors only |
| `business_address` | CharField(255) | Yes | Yes | No | None | No | Business vendors only |
| `business_logo` | Cloudinary field | Yes | Yes | No | None | No | Business vendors only, optional per PRD |
| `status` | CharField(20), choices=`VendorStatus` | No | No | No | `PENDING` | Yes | Verification lifecycle state |
| `submitted_at` | DateTimeField | No | No | No | auto_now_add | No | Application submission timestamp |
| `reviewed_at` | DateTimeField | Yes | Yes | No | None | No | Set when status transitions out of `PENDING` (auto-set in MVP since auto-approval) |
| `reviewed_by` | FK → `User` | Yes | Yes | No | None | No | Null in MVP (auto-approval); populated once manual review ships |

**Relationships:** `user` (`on_delete=PROTECT`, `related_name="vendor_profile"`) — protecting rather than cascading because a vendor's history (products, conversations, reviews) must never silently vanish via a user deletion path; account deactivation is handled via `User.is_active`, not row deletion. `university` (`on_delete=PROTECT`, `related_name="vendor_profiles"`). `reviewed_by` (`on_delete=SET_NULL`, `related_name="vendor_reviews"`).

**Constraints:**
- `UNIQUE(university_id, matric_number)` — enforced as a **partial unique index** `WHERE matric_number IS NOT NULL` (business vendors have no matric number and must not collide on NULL).
- `CheckConstraint`: `vendor_type=STUDENT` requires `matric_number`, `department`, `level` non-null; `vendor_type=BUSINESS` requires `business_name`, `business_address` non-null. (Modeled as a DB `CHECK` where PostgreSQL syntax allows; primary enforcement is service-layer, DB is the backstop.)

**Model Methods:** `__str__` returns `store_name`. `is_verified` property (`status == VERIFIED`). No transition methods — verification transitions belong to `VendorVerificationService`.

---

### 4.4 `VendorDocument` (app: `vendors`)

**Purpose:** Stores the single proof-of-studentship (or future business document) submitted with a vendor application. Modeled as its own table — not a field on `VendorProfile` — so multi-document/resubmission support is additive later without a schema change.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `vendor_profile` | FK → `VendorProfile` | No | No | No | — | Yes | |
| `document_type` | CharField(30), choices=`VendorDocumentType` | No | No | No | — | No | Admission Letter / Student ID / Course Reg Slip / School Fee Receipt (student); reserved values for future business docs |
| `file` | Cloudinary field | No | No | No | — | No | The uploaded proof document |
| `status` | CharField(20), choices=`VendorDocumentStatus` | No | No | No | `PENDING` | Yes | Independent of `VendorProfile.status` to allow future per-document review |
| `uploaded_at` | DateTimeField | No | No | No | auto_now_add | No | |
| `reviewed_at` | DateTimeField | Yes | Yes | No | None | No | Unused in MVP (auto-approval), schema-ready |
| `reviewed_by` | FK → `User` | Yes | Yes | No | None | No | Unused in MVP, schema-ready |

**Relationships:** `vendor_profile` (`on_delete=CASCADE`, `related_name="documents"`) — genuinely dependent child row, deleting the vendor profile legitimately removes its documents. `reviewed_by` (`on_delete=SET_NULL`, `related_name="document_reviews"`).

**Constraints:** None beyond FK integrity. (MVP allows exactly one document per vendor in practice, enforced at the service layer per the architecture's "one document per vendor in MVP flow" note — no DB uniqueness constraint, to keep multi-document support purely additive.)

**Model Methods:** `__str__` returns `f"{vendor_profile.store_name} — {document_type}"`.

---

### 4.5 `Store` (app: `stores`)

**Purpose:** The public-facing storefront a Customer sees — separated from `VendorProfile` because it has a different read audience (public) and different write sensitivity (vendor-editable, not verification-locked).

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `vendor_profile` | OneToOneField → `VendorProfile` | No | No | Yes | — | Yes | One store per vendor |
| `display_name` | CharField(150) | No | No | No | — | No | May diverge from `VendorProfile.store_name` if renamed post-verification |
| `slug` | SlugField(170) | No | No | Yes | auto from `display_name` | Yes | Public storefront URL |
| `description` | TextField | Yes | Yes | No | None | No | Optional storefront bio |
| `contact_phone` | CharField(20) | Yes | Yes | No | None | No | Defaults to vendor's phone at creation, independently editable |
| `is_active` | BooleanField | No | No | No | True | Yes | Mirrors vendor's active/suspended state; maintained by `VendorSuspensionService`, not user-editable |

**Relationships:** `vendor_profile` (`on_delete=CASCADE`, `related_name="store"`) — a store has no independent meaning without its vendor; deleting the vendor profile legitimately removes the store row (note: MVP has no user-facing vendor-profile deletion flow — this is a data-integrity safeguard, not an exposed action).

**Constraints:** `UNIQUE(slug)`.

**Model Methods:** `__str__` returns `display_name`. No lifecycle methods — `is_active` toggling belongs to `VendorSuspensionService`.

---

### 4.6 `Category` (app: `categories`)

**Purpose:** Hierarchical taxonomy for products. Self-referential to support arbitrary depth per product decision (PRD shows 2 levels, schema is unrestricted).

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `name` | CharField(100) | No | No | No | — | No | Unique **per parent**, not globally (see Constraints) |
| `slug` | SlugField(120) | No | No | Yes | auto from `name` | Yes | Globally unique for clean URLs |
| `parent` | FK → `self` | Yes | Yes | No | None | Yes (composite) | Null = root category |
| `display_order` | PositiveIntegerField | No | No | No | 0 | No | Ordering among siblings; admin-reorderable post-MVP |
| `is_active` | BooleanField | No | No | No | True | Yes | Inactive categories hidden from browse/filter, never deleted |

**Relationships:** `parent` (`on_delete=PROTECT`, `related_name="children"`) — protected so a category with descendants cannot be silently orphaned; deletion (soft, via `is_deleted`) requires children to be reparented or deactivated first (service-layer rule).

**Constraints:** `UNIQUE(parent_id, name)` (composite, allows same name under different parents e.g. "Books" under both "Faculty of Arts" and "Faculty of Science" if ever needed). `UNIQUE(slug)` globally.

**Model Methods:** `__str__` returns full breadcrumb path (e.g. `"Electronics > Phones"`). `is_root` property (`parent_id is None`). No tree-mutation methods — reparenting/reordering belongs to a future `CategoryService` (not MVP-exposed per PRD, but schema is ready).

---

### 4.7 `Product` (app: `products`)

**Purpose:** The core listing entity. Owned by exactly one `Store`, may belong to many `Category` rows via `ProductCategory`.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `store` | FK → `Store` | No | No | No | — | Yes | |
| `university` | FK → `University` | No | No | No | — | Yes (composite) | **Denormalized**, copied from `store.vendor_profile.university` at creation for query performance; never a sole source of truth |
| `name` | CharField(200) | No | No | No | — | No | |
| `slug` | SlugField(220) | No | No | Yes | auto from `name` + short suffix | Yes | Public detail-page lookup |
| `description` | TextField | No | Yes | No | — | No | |
| `price` | DecimalField(10,2) | No | No | No | — | Yes | Validated ≥ 0 |
| `condition` | CharField(10), choices=`ProductCondition` | No | No | No | — | No | `NEW` / `USED` |
| `quantity` | PositiveIntegerField | No | No | No | 1 | No | Drives auto out-of-stock behavior |
| `campus_location` | CharField(150) | Yes | Yes | No | None | No | Free-text pickup/meeting context, distinct from `university` |
| `status` | CharField(25), choices=`ProductStatus` | No | No | No | `ACTIVE` | Yes (composite + standalone) | See §5 for full lifecycle enum |
| `views_count` | PositiveIntegerField | No | No | No | 0 | No | Incremented synchronously at MVP scale; future-ready for debounced/cached counters |
| `listed_at` | DateTimeField | No | No | No | auto_now_add | Yes | Drives "Newest" sort; conceptually distinct from `created_at` should re-listing ever reset it |
| `expires_at` | DateTimeField | No | No | No | `listed_at + 30 days`, set at creation | Yes | Drives the expiry sweep |
| `search_vector` | `SearchVectorField` (django.contrib.postgres) | Yes | Yes | No | None | Yes (GIN) | Maintained via DB trigger or signal over `name` + `description` |

**Relationships:** `store` (`on_delete=PROTECT`, `related_name="products"`) — a store is never deleted while it owns products; store deactivation goes through `is_active`, not deletion. `university` (`on_delete=PROTECT`, `related_name="products"`).

**Constraints:** `UNIQUE(slug)`. `CheckConstraint`: `price >= 0`. `CheckConstraint`: `quantity >= 0`.

**Model Methods:** `__str__` returns `name`. `is_out_of_stock` property (`quantity == 0`) — **derived, not a stored status value**; a product can be `ACTIVE` and simultaneously out-of-stock, which the serializer surfaces as an `availability` computed field rather than conflating it with the visibility-oriented `status` enum. `primary_image` property (returns the `ProductImage` with `is_primary=True`). No lifecycle-transition methods — those belong to `ProductLifecycleService`.

---

### 4.8 `ProductImage` (app: `products`)

**Purpose:** Up to eight images per product; exactly one marked primary.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `product` | FK → `Product` | No | No | No | — | Yes | |
| `image` | Cloudinary field | No | No | No | — | No | |
| `is_primary` | BooleanField | No | No | No | False | Yes (partial) | Exactly one `True` per product |
| `display_order` | PositiveIntegerField | No | No | No | 0 | No | Ordering among the up-to-seven additional images |

**Relationships:** `product` (`on_delete=CASCADE`, `related_name="images"`) — genuinely dependent child row; deleting a product legitimately removes its images.

**Constraints:**
- Partial unique index: `UNIQUE(product_id) WHERE is_primary = TRUE` — DB backstop for "exactly one primary image."
- Max-8-per-product is **service-layer enforced only** (not practically expressible as a portable DB constraint); documented here as a business invariant, see §7.

**Model Methods:** `__str__` returns `f"{product.name} image #{display_order}"`.

---

### 4.9 `ProductCategory` (app: `products`) — Through Table

**Purpose:** Explicit many-to-many join between `Product` and `Category`, modeled explicitly (not an implicit Django M2M) to support a composite index and potential future per-assignment metadata.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `product` | FK → `Product` | No | No | No | — | Yes (composite) | |
| `category` | FK → `Category` | No | No | No | — | Yes (composite) | |

**Relationships:** `product` (`on_delete=CASCADE`, `related_name="category_links"`); `category` (`on_delete=PROTECT`, `related_name="product_links"`) — protected so a category in active use cannot be deleted out from under listings; must be deactivated (`is_active=False`) instead.

**Constraints:** `UNIQUE(product_id, category_id)` — prevents duplicate assignment.

**Model Methods:** None — pure join row.

---

### 4.10 `Conversation` (app: `chat`)

**Purpose:** A Customer-initiated thread with a Vendor, optionally scoped to a Product. Also the sole anchor for review eligibility via `transaction_status`.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `customer` | FK → `User` | No | No | No | — | Yes (composite) | Must be a Customer role; enforced at service layer ("Vendors cannot initiate") |
| `vendor` | FK → `VendorProfile` | No | No | No | — | Yes (composite) | |
| `product` | FK → `Product` | Yes | Yes | No | None | No | Nullable — a conversation may be store-level, not tied to one listing |
| `transaction_status` | CharField(15), choices=`TransactionStatus` | No | No | No | `ONGOING` | No | `ONGOING` / `COMPLETED` — the sole review-eligibility anchor |
| `completed_at` | DateTimeField | Yes | Yes | No | None | No | Set when vendor marks transaction completed |

**Relationships:** `customer` (`on_delete=PROTECT`, `related_name="conversations_as_customer"`); `vendor` (`on_delete=PROTECT`, `related_name="conversations"`); `product` (`on_delete=SET_NULL`, `related_name="conversations"`) — a product being removed/expired should not destroy chat history, only detach the reference.

**Constraints:** `UNIQUE(customer_id, vendor_id, product_id)` — duplicate-thread prevention. (Note: since `product_id` can be NULL, PostgreSQL's default NULL-distinct behavior means multiple store-level [product-less] conversations between the same pair would *not* collide — this is intentional at the DB level but the service layer additionally enforces "at most one open store-level conversation per pair" as a business rule, not a schema-level one.)

**Model Methods:** `__str__` returns `f"{customer} ↔ {vendor.store_name}"`. `is_completed` property. No transition methods — completion belongs to `ConversationService`.

---

### 4.11 `Message` (app: `chat`)

**Purpose:** An individual message within a `Conversation`.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `conversation` | FK → `Conversation` | No | No | No | — | Yes (composite) | |
| `sender` | FK → `User` | No | No | No | — | No | Either the customer or the vendor's user account |
| `content_type` | CharField(10), choices=`MessageType` | No | No | No | `TEXT` | No | Only `TEXT` created in MVP; `IMAGE` schema-ready |
| `body` | TextField | Yes | Blank allowed only if attachment present | No | None | No | Required when `content_type=TEXT` (service/serializer validated) |
| `read_at` | DateTimeField | Yes | Yes | No | None | Yes (partial) | Null = unread |

**Relationships:** `conversation` (`on_delete=CASCADE`, `related_name="messages"`) — messages have no meaning without their thread. `sender` (`on_delete=PROTECT`, `related_name="sent_messages"`) — chat history must survive even if a user account is later deactivated.

**Constraints:** None beyond FK integrity.

**Model Methods:** `__str__` truncates `body` to 50 chars. `is_read` property.

---

### 4.12 `MessageAttachment` (app: `chat`)

**Purpose:** Schema-ready, unused-in-MVP support for image attachments, so the future feature ships without a breaking migration.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `message` | OneToOneField → `Message` | No | No | Yes | — | Yes (implicit) | |
| `file` | Cloudinary field | No | No | No | — | No | |
| `attachment_type` | CharField(10), choices=`AttachmentType` | No | No | No | `IMAGE` | No | Only value in use; enum ready for future types |

**Relationships:** `message` (`on_delete=CASCADE`, `related_name="attachment"`) — genuinely dependent child row.

**Constraints:** None beyond the implicit 1:1 uniqueness.

**Model Methods:** `__str__` returns `f"Attachment for message {message_id}"`.

---

### 4.13 `Review` (app: `reviews`)

**Purpose:** A Customer's rating/comment on a completed transaction. Gated entirely on `Conversation.transaction_status == COMPLETED`.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `conversation` | OneToOneField → `Conversation` | No | No | Yes | — | Yes | One review per completed transaction thread |
| `store` | FK → `Store` | No | No | No | — | Yes | **Denormalized**, copied from `conversation.vendor.store` at creation, avoids a multi-hop join on every storefront read |
| `rating` | PositiveSmallIntegerField | No | No | No | — | No | 1–5, validated via `MinValueValidator(1)` / `MaxValueValidator(5)` |
| `comment` | TextField | Yes | Yes | No | None | No | Optional per PRD |
| `edited_at` | DateTimeField | Yes | Yes | No | None | No | Set on customer edit; null if never edited |

**Relationships:** `conversation` (`on_delete=PROTECT`, `related_name="review"`) — a review must never be silently orphaned by conversation deletion (conversations are not deletable in MVP by design, this is a safeguard). `store` (`on_delete=PROTECT`, `related_name="reviews"`).

**Constraints:** `CheckConstraint`: `rating BETWEEN 1 AND 5`. Implicit one-review-per-conversation via `OneToOneField`.

**Model Methods:** `__str__` returns `f"{rating}★ for {store.display_name}"`. `is_edited` property (`edited_at is not None`). No creation/edit-eligibility logic — that is `ReviewService`'s job (checks `conversation.transaction_status`).

---

### 4.14 `Report` (app: `reports`)

**Purpose:** A Customer's report of a Product or a Vendor, for Admin moderation.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `reporter` | FK → `User` | No | No | No | — | No | |
| `product` | FK → `Product` | Yes | Yes | No | None | Yes | Exactly one of `product` / `vendor_profile` set |
| `vendor_profile` | FK → `VendorProfile` | Yes | Yes | No | None | Yes | |
| `reason` | CharField(30), choices=`ReportReason` | No | No | No | — | No | |
| `description` | TextField | Yes | Yes | No | None | No | Free-text elaboration |
| `status` | CharField(20), choices=`ReportStatus` | No | No | No | `PENDING` | Yes | `PENDING → UNDER_REVIEW → RESOLVED / REJECTED` |
| `resolved_by` | FK → `User` | Yes | Yes | No | None | No | Admin who closed the report |
| `resolved_at` | DateTimeField | Yes | Yes | No | None | No | |
| `resolution_notes` | TextField | Yes | Yes | No | None | No | Internal admin notes |

**Relationships:** `reporter` (`on_delete=PROTECT`, `related_name="reports_filed"`); `product` (`on_delete=CASCADE`, `related_name="reports"`) — if a product is truly hard-deleted (rare/admin-only), its reports lose meaning and may go with it; `vendor_profile` (`on_delete=CASCADE`, `related_name="reports"`) similarly; `resolved_by` (`on_delete=SET_NULL`, `related_name="reports_resolved"`).

**Constraints:** `CheckConstraint` — exactly one of `product_id`, `vendor_profile_id` is non-null (`(product_id IS NOT NULL) != (vendor_profile_id IS NOT NULL)` expressed as a PostgreSQL boolean XOR via `CHECK (num_nonnulls(product_id, vendor_profile_id) = 1)`).

**Model Methods:** `__str__` returns target description + status. `target` property returns whichever of `product`/`vendor_profile` is set. No moderation-action methods — resolving a report and cascading into suspension/removal belongs to `ReportService`, which calls into `vendors`/`products` services per the architecture's app-boundary table.

---

### 4.15 `Notification` (app: `notifications`)

**Purpose:** A persisted notification record for a user, decoupled from delivery mechanism.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `recipient` | FK → `User` | No | No | No | — | Yes (composite) | |
| `notification_type` | CharField(30), choices=`NotificationType` | No | No | No | — | No | New Message / Verification Update / Moderation Update / New Review / Announcement |
| `title` | CharField(150) | No | No | No | — | No | |
| `body` | TextField | No | Yes | No | — | No | |
| `data` | JSONField | Yes | Yes | No | dict (empty) | No | Structured payload for client-side deep-linking |
| `read_at` | DateTimeField | Yes | Yes | No | None | Yes (partial) | Null = unread, drives unread badge |

**Relationships:** `recipient` (`on_delete=CASCADE`, `related_name="notifications"`) — notifications are meaningless without their owning user and are legitimately purged with the account.

**Constraints:** None beyond FK integrity.

**Model Methods:** `__str__` returns `title`. `is_read` property. No dispatch logic — that lives behind the `NotificationDispatcher` strategy interface in the service layer, not on the model.

---

### 4.16 `DeviceToken` (app: `notifications`)

**Purpose:** Registered push-notification device tokens, ready for FCM activation without further schema change.

**Fields:**

| Field | Type | Null | Blank | Unique | Default | Indexed | Notes |
|---|---|---|---|---|---|---|---|
| `user` | FK → `User` | No | No | No | — | Yes (composite) | A user may have multiple devices |
| `token` | CharField(255) | No | No | Yes | — | Yes | The FCM registration token |
| `platform` | CharField(10), choices=`DevicePlatform` | No | No | No | — | No | `IOS` / `ANDROID` / `WEB` |
| `is_active` | BooleanField | No | No | No | True | Yes (composite) | Deactivated rather than deleted on token invalidation, for audit trail |
| `last_used_at` | DateTimeField | No | No | No | auto_now | No | Refreshed on each successful dispatch/registration ping |

**Relationships:** `user` (`on_delete=CASCADE`, `related_name="device_tokens"`).

**Constraints:** `UNIQUE(token)`.

**Model Methods:** `__str__` returns `f"{platform} token for {user}"`.

---

## 5. Enumerations

### `VendorType` (`VendorProfile.vendor_type`)
| Value | Meaning |
|---|---|
| `STUDENT` | Student Vendor — requires matric number, department, level, one proof-of-studentship document |
| `BUSINESS` | Business Vendor — requires business name & address, optional logo |

### `VendorStatus` (`VendorProfile.status`)
| Value | Meaning |
|---|---|
| `PENDING` | Application submitted, awaiting (auto-)approval |
| `VERIFIED` | Approved; public verification badge shown |
| `REJECTED` | Application denied; vendor may reapply (service-defined flow) |
| `SUSPENDED` | Previously verified, now suspended by Admin; products auto-hidden |

### `VendorDocumentType` (`VendorDocument.document_type`)
| Value | Meaning |
|---|---|
| `ADMISSION_LETTER` | Proof of studentship |
| `STUDENT_ID_CARD` | Proof of studentship |
| `COURSE_REGISTRATION_SLIP` | Proof of studentship |
| `SCHOOL_FEE_RECEIPT` | Proof of studentship |
| `BUSINESS_DOCUMENT` | Reserved — post-MVP business-vendor supporting documents |

### `VendorDocumentStatus` (`VendorDocument.status`)
| Value | Meaning |
|---|---|
| `PENDING` | Uploaded, not yet reviewed (auto-approved alongside profile in MVP) |
| `APPROVED` | Reviewed and accepted (future manual-review flow) |
| `REJECTED` | Reviewed and rejected (future manual-review flow) |

### `ProductCondition` (`Product.condition`)
| Value | Meaning |
|---|---|
| `NEW` | Unused |
| `USED` | Previously used |

### `ProductStatus` (`Product.status`)
| Value | Meaning |
|---|---|
| `ACTIVE` | Visible in marketplace, browsable and searchable |
| `EXPIRED` | 30-day expiry reached; hidden, not deleted; vendor may renew |
| `HIDDEN_BY_SUSPENSION` | Vendor suspended by Admin; hidden pending reinstatement |
| `REMOVED_BY_ADMIN` | Admin moderation removal; hidden, distinct from expiry/suspension for audit clarity |

> Note: "Out of Stock" is **not** a `ProductStatus` value. It is a derived condition (`quantity == 0`) surfaced as a computed `availability` flag alongside `status`, since a product can be simultaneously `ACTIVE` (visible) and out-of-stock (not purchasable) — conflating the two into one enum would make the visibility semantics ambiguous.

### `TransactionStatus` (`Conversation.transaction_status`)
| Value | Meaning |
|---|---|
| `ONGOING` | Conversation active, transaction not yet marked complete |
| `COMPLETED` | Vendor has marked the transaction complete; unlocks review eligibility |

### `MessageType` (`Message.content_type`)
| Value | Meaning |
|---|---|
| `TEXT` | Plain text message — the only value created in MVP |
| `IMAGE` | Image-attached message — schema-ready, not created in MVP |

### `AttachmentType` (`MessageAttachment.attachment_type`)
| Value | Meaning |
|---|---|
| `IMAGE` | Only attachment type currently modeled |

### `ReportReason` (`Report.reason`)
| Value | Meaning |
|---|---|
| `PROHIBITED_ITEM` | Listing violates platform rules |
| `MISLEADING_LISTING` | Product misrepresented |
| `SCAM_OR_FRAUD` | Suspected fraudulent activity |
| `INAPPROPRIATE_BEHAVIOR` | Vendor conduct complaint |
| `FAKE_VENDOR` | Suspected impersonation/fake identity |
| `OTHER` | Free-text elaboration required in `description` |

### `ReportStatus` (`Report.status`)
| Value | Meaning |
|---|---|
| `PENDING` | Filed, not yet triaged |
| `UNDER_REVIEW` | Admin actively investigating |
| `RESOLVED` | Action taken (may cascade into `products`/`vendors` service calls) |
| `REJECTED` | No action warranted |

### `NotificationType` (`Notification.notification_type`)
| Value | Meaning |
|---|---|
| `NEW_MESSAGE` | New chat message received |
| `VENDOR_VERIFICATION_UPDATE` | Vendor application status changed |
| `PRODUCT_MODERATION_UPDATE` | Listing removed/restored by Admin |
| `NEW_REVIEW` | A new review was left on the vendor's store |
| `PLATFORM_ANNOUNCEMENT` | General platform-wide notice |

### `NotificationChannel` (conceptual — dispatch abstraction, not a stored field in MVP)
| Value | Meaning |
|---|---|
| `PUSH` | Delivered via `NotificationDispatcher` (currently `NoOpDispatcher`, future `FCMDispatcher`) |
| `IN_APP` | Always recorded via the `Notification` row regardless of push delivery |

### `DevicePlatform` (`DeviceToken.platform`)
| Value | Meaning |
|---|---|
| `IOS` | Apple push registration |
| `ANDROID` | FCM Android registration |
| `WEB` | Web push registration |

---

## 6. Database Indexing

| Model | Index | Type | Query Pattern Supported | Performance Rationale |
|---|---|---|---|---|
| `Product` | `(university_id, status)` | Composite B-tree | Primary marketplace browse: "active products in my university" | Most-hit query in the app; composite avoids a filter+sort double pass |
| `Product` | `status` | B-tree | Admin moderation queue, expiry sweep job | Sweep job scans by status independent of university |
| `Product` | `price` | B-tree | Price-range filters, price-ascending/descending sort | Range queries and ORDER BY both benefit |
| `Product` | `listed_at` | B-tree | "Newest" sort | Direct ORDER BY support |
| `Product` | `expires_at` | B-tree | Nightly/periodic expiry sweep (`expires_at <= now()`) | Range scan on a monotonic column |
| `Product` | `slug` (unique) | B-tree (unique) | Public product detail page lookup | O(log n) exact-match lookup, also enforces uniqueness |
| `Product` | `search_vector` | **GIN** | PostgreSQL full-text search (`@@` operator) | GIN is the standard/required index type for `tsvector` columns |
| `ProductCategory` | `(category_id, product_id)` | Composite B-tree | Category-filtered browse ("all products in Category X") | Composite ordered for category-first filtering, product as tiebreaker |
| `VendorProfile` | `status` | B-tree | Verification queue, suspension logic scans | Small-cardinality but heavily filtered column |
| `VendorProfile` | `(university_id, matric_number)` **partial**, `WHERE matric_number IS NOT NULL` | Unique composite | Per-university matric uniqueness check on application submit | Partial to avoid NULL-collision issues for business vendors |
| `Conversation` | `customer_id` | B-tree | "My conversations" list (customer view) | Direct FK filter, high frequency |
| `Conversation` | `vendor_id` | B-tree | Vendor inbox | Direct FK filter, high frequency |
| `Conversation` | `(customer_id, vendor_id, product_id)` | Unique composite | Duplicate-thread prevention on conversation creation | Enforces the business uniqueness rule at the DB level |
| `Message` | `(conversation_id, created_at)` | Composite B-tree | Ordered thread pagination | Supports both filter and ORDER BY in one index |
| `Message` | `read_at` **partial**, `WHERE read_at IS NULL` | Partial B-tree | Unread-count queries per conversation/user | Index only covers unread rows — much smaller than a full index, cheap to maintain |
| `Review` | `store_id` | B-tree | Storefront review listing (denormalized FK avoids multi-hop join) | Direct filter on the most common read path |
| `Review` | `conversation_id` (unique, implicit) | B-tree (unique) | Eligibility/audit lookup, "does this conversation already have a review" | Also enforces the 1:1 business rule |
| `Report` | `status` | B-tree | Admin moderation queue | Small-cardinality, heavily filtered |
| `Report` | `product_id`, `vendor_profile_id` (each, nullable) | B-tree (two separate indexes) | "All reports against this product/vendor" lookup | Independent lookups, not typically queried together |
| `Notification` | `(recipient_id, read_at)` **partial**, `WHERE read_at IS NULL` | Composite partial | Unread badge/count per user | Partial index keeps it small as notifications accumulate |
| `DeviceToken` | `(user_id, is_active)` | Composite B-tree | Active-token lookup at dispatch time | Composite matches the dispatcher's exact query shape |
| `Category` | `(parent_id, display_order)` | Composite B-tree | Ordered children within a parent (tree rendering) | Supports filter + ORDER BY together |
| `University` | `name`, `short_name`, `slug` (each unique) | B-tree (unique) | Lookup by any of the three identifiers; onboarding dropdown | Small table, indexes mainly for uniqueness enforcement + fast exact match |
| `User` | `email` (unique) | B-tree (unique) | Login lookup | Every authentication request hits this |
| `User` | `active_university_id` | B-tree | "All users currently at university X" (admin analytics) | Supports admin dashboard aggregation |
| `ProductImage` | `product_id` (implicit via FK) | B-tree | Fetching all images for a product detail page | Standard FK index |
| `ProductImage` | `product_id` **partial**, `WHERE is_primary = TRUE` | Unique partial | Enforces/looks up the single primary image fast | Backstops the one-primary-image invariant |

---

## 7. Validation Rules

Rules are grouped by the layer that owns them, per the architecture's service-layer-first philosophy.

### 7.1 Model-Level Validation (DB constraints + `clean()`/field validators)
- `Product.price >= 0`, `Product.quantity >= 0` — `CheckConstraint`.
- `Review.rating` between 1 and 5 — `CheckConstraint` + `MinValueValidator`/`MaxValueValidator`.
- `Report`: exactly one of `product`/`vendor_profile` set — `CheckConstraint`.
- `VendorProfile`: `(university, matric_number)` uniqueness — partial unique index.
- `ProductImage`: at most one `is_primary=True` per product — partial unique index (backstop only; the "exactly one, always" invariant and "max 8 total" cap are service-layer).
- `Conversation`: `(customer, vendor, product)` uniqueness — unique composite index.
- `User.email` uniqueness — unique index, normalized lowercase on save.

### 7.2 Serializer-Level Validation
- Input shape/type checking (e.g., `phone_number` format, `price` decimal precision).
- Conditional-required fields: `VendorProfile` student fields required only when `vendor_type=STUDENT`; business fields only when `BUSINESS` (mirrors the DB `CheckConstraint` but gives a friendly per-field error before it would ever hit the DB).
- File validation for uploads (size/type) before they reach Cloudinary, via `common/fields.py` generic upload validators.
- `Message.body` required when `content_type=TEXT`.

### 7.3 Service-Layer Validation (Business Invariants)
- **Vendor eligibility:** one vendor profile per account — enforced by `OneToOneField` at DB level, but the *application flow* ("customer must not already be mid-application") is a service check.
- **Product image cap:** maximum 8 images (1 primary + 7 additional) — enforced in `ProductService`/`ProductImageService` before insert; DB has no portable "count ≤ 8" constraint.
- **Conversation initiation:** only Customers may initiate; Vendors cannot start conversations with Customers — enforced in `ConversationService`, not expressible as a static DB/permission-class rule since it depends on *who is acting on which side* of the same `User`/`VendorProfile` relationship.
- **Review eligibility:** a review may only be created when `conversation.transaction_status == COMPLETED` — `ReviewService` check against `chat`'s model, per the app-boundary table ("reviews owns eligibility checks against chat's transaction flag").
- **Review edit:** allowed any time after creation by the reviewing customer only — ownership + no additional gating, enforced in `ReviewService`.
- **Vendor suspension cascade:** suspending a `VendorProfile` synchronously hides all currently-`ACTIVE` products to `HIDDEN_BY_SUSPENSION` — `VendorSuspensionService`, transactional.
- **Vendor reinstatement:** restores `HIDDEN_BY_SUSPENSION` products to `ACTIVE`, **except** any whose `expires_at` has passed while hidden, which become `EXPIRED` instead — `VendorSuspensionService.reinstate()`.
- **Out-of-stock auto-transition:** when `Product.quantity` reaches 0 via `InventoryService`, availability is recomputed (not a status transition, since `status` remains `ACTIVE`) — see §5 note.
- **Listing expiry:** `ProductLifecycleService` (via scheduled sweep) transitions `ACTIVE` products past `expires_at` to `EXPIRED`.
- **Listing renewal:** vendor-triggered; resets `expires_at` to `now() + 30 days` and `status` back to `ACTIVE` — only valid from `EXPIRED`, not from `HIDDEN_BY_SUSPENSION` or `REMOVED_BY_ADMIN` (service-enforced state-machine rule, see §9).
- **Report target resolution:** `ReportService.resolve()` may itself trigger `VendorSuspensionService` or `ProductLifecycleService` calls, per the architecture's explicit note that `reports` "does NOT own" suspension/removal actions themselves.
- **University scoping:** all product browse/search queries are automatically filtered by the requesting user's `active_university` via `core.filters.ActiveUniversityFilterBackend` — a cross-cutting service/filter concern, not a per-model validation rule.

---

## 8. Cascade Rules

| Relationship | `on_delete` | Rationale |
|---|---|---|
| `User.active_university` → `University` | `PROTECT` | A university with active user references must not be deletable out from under them; deactivate (`is_active=False`) instead |
| `VendorProfile.user` → `User` | `PROTECT` | A vendor's entire history (products, conversations, reviews) must never vanish via account deletion; account disablement uses `User.is_active` |
| `VendorProfile.university` → `University` | `PROTECT` | Same rationale as above — vendor eligibility history is preserved |
| `VendorProfile.reviewed_by` → `User` | `SET_NULL` | Losing the reviewing admin's account shouldn't destroy the vendor's verification record, only the attribution |
| `VendorDocument.vendor_profile` → `VendorProfile` | `CASCADE` | Genuinely dependent child row — a document has no meaning without its vendor profile |
| `VendorDocument.reviewed_by` → `User` | `SET_NULL` | Same rationale as `VendorProfile.reviewed_by` |
| `Store.vendor_profile` → `VendorProfile` | `CASCADE` | A store has no independent meaning without its vendor profile |
| `Category.parent` → `Category` (self) | `PROTECT` | A category with children/descendants cannot be silently orphaned; reparent or deactivate first |
| `Product.store` → `Store` | `PROTECT` | A store is never hard-deleted while it owns listings; store deactivation uses `is_active` |
| `Product.university` → `University` | `PROTECT` | Preserves denormalized historical accuracy; universities aren't deleted while products reference them |
| `ProductImage.product` → `Product` | `CASCADE` | Genuinely dependent child row |
| `ProductCategory.product` → `Product` | `CASCADE` | Join row has no meaning without the product |
| `ProductCategory.category` → `Category` | `PROTECT` | A category in active use cannot be deleted from under listings; deactivate instead |
| `Conversation.customer` → `User` | `PROTECT` | Chat history must survive account-level changes |
| `Conversation.vendor` → `VendorProfile` | `PROTECT` | Same rationale |
| `Conversation.product` → `Product` | `SET_NULL` | A product being removed/expired should not destroy the conversation thread, only detach the reference |
| `Message.conversation` → `Conversation` | `CASCADE` | Messages have no meaning without their thread |
| `Message.sender` → `User` | `PROTECT` | Chat history integrity must survive sender account changes |
| `MessageAttachment.message` → `Message` | `CASCADE` | Genuinely dependent child row |
| `Review.conversation` → `Conversation` | `PROTECT` | A review must never be silently orphaned; conversations are not deletable in MVP by design |
| `Review.store` → `Store` | `PROTECT` | Same integrity rationale for the denormalized FK |
| `Report.reporter` → `User` | `PROTECT` | Report provenance/audit trail must be preserved |
| `Report.product` → `Product` | `CASCADE` | If a product is genuinely hard-deleted (rare, admin-only path), its reports lose independent meaning |
| `Report.vendor_profile` → `VendorProfile` | `CASCADE` | Same rationale |
| `Report.resolved_by` → `User` | `SET_NULL` | Losing the resolving admin's account shouldn't destroy the report record |
| `Notification.recipient` → `User` | `CASCADE` | Notifications are meaningless without, and legitimately purged with, their owning user |
| `DeviceToken.user` → `User` | `CASCADE` | Same rationale |

**No `DO_NOTHING` relationships exist in this schema** — every FK has an explicit, deliberate integrity behavior; `DO_NOTHING` would silently defer integrity to application code with no DB backstop, which conflicts with the "secure by default" principle.

---

## 9. Lifecycle Rules

### 9.1 `User`
`(created, unverified email — future release)` → **active**. No hard delete in MVP; deactivation via `is_active=False` (service/admin action, not modeled as a formal state machine — a simple boolean toggle).

### 9.2 `VendorProfile` (verification lifecycle)
```
PENDING ──(auto-approve, MVP)──► VERIFIED
PENDING ──(future manual review)──► REJECTED
VERIFIED ──(admin action)──► SUSPENDED
SUSPENDED ──(admin action)──► VERIFIED   [reinstatement — see Product cascade below]
```
- `PENDING → VERIFIED`: automatic in MVP at submission time (`reviewed_at` set, `reviewed_by` remains null).
- `VERIFIED → SUSPENDED`: triggers `VendorSuspensionService` — cascades to `Store.is_active=False` and all `ACTIVE` products → `HIDDEN_BY_SUSPENSION`.
- `SUSPENDED → VERIFIED` (reinstatement): cascades to `Store.is_active=True`; each `HIDDEN_BY_SUSPENSION` product individually checked — if `expires_at` has passed, becomes `EXPIRED`; otherwise becomes `ACTIVE`.
- `REJECTED` is terminal in MVP scope (no PRD-defined reapplication flow — flagged as an open question in §13).

### 9.3 `Store`
Mirrors vendor suspension state (`is_active` toggled by `VendorSuspensionService`), otherwise stable for the account's lifetime. No independent lifecycle.

### 9.4 `Product`
```
                     ┌──────────────────────────────┐
                     │                               │
    (created) ──► ACTIVE ──(30 days elapse)──► EXPIRED
                     │  ▲                          │
                     │  │  (vendor renews)──────────┘
   (vendor suspended)│  │(vendor reinstated,
                     │  │ not yet expired)
                     ▼  │
           HIDDEN_BY_SUSPENSION
                     │
        (admin moderation action, any state)
                     ▼
             REMOVED_BY_ADMIN  [terminal in MVP]
```
- `ACTIVE → EXPIRED`: automatic, sweep-driven (`expires_at <= now()`).
- `EXPIRED → ACTIVE`: vendor-triggered renewal only; resets `expires_at`.
- `ACTIVE ↔ HIDDEN_BY_SUSPENSION`: driven entirely by the owning vendor's suspension/reinstatement, never a direct vendor or customer action.
- `HIDDEN_BY_SUSPENSION → EXPIRED` (on reinstatement, if already past due): see §9.2.
- `* → REMOVED_BY_ADMIN`: admin moderation action from any non-removed state; **no PRD-defined path back** in MVP (flagged in §13).
- Quantity reaching 0 does **not** change `status`; it only affects the derived `is_out_of_stock`/`availability` computation.

### 9.5 `Conversation`
```
(created by customer) ──► ONGOING ──(vendor marks complete)──► COMPLETED
```
Terminal at `COMPLETED` in MVP — no PRD-defined path to reopen a completed conversation.

### 9.6 `Review`
```
(created, only if conversation.transaction_status == COMPLETED) ──► exists
exists ──(customer edits)──► exists (edited_at updated)
```
No deletion or moderation lifecycle defined in MVP PRD (reviews are not in the `reports` reportable-target list — only Products and Vendors are reportable per §13 of the PRD).

### 9.7 `Report`
```
PENDING ──► UNDER_REVIEW ──► RESOLVED
                          └─► REJECTED
```
`PENDING → RESOLVED` directly is also permitted (small-scale admin team may resolve without an explicit "under review" step) — service layer allows both paths; `UNDER_REVIEW` is not mandatory transit.

### 9.8 `Notification`
```
(created, unread) ──(recipient views)──► read (read_at set)
```
No further lifecycle; notifications are not deleted in MVP (future retention policy is an operational, not schema, concern).

### 9.9 `DeviceToken`
```
(registered, is_active=True) ──(token invalidated/app uninstalled)──► is_active=False
```
Deactivated rather than deleted, preserving a dispatch audit trail.

---

## 10. Service Ownership

| Model | Owning Service(s) | Notes |
|---|---|---|
| `University` | `UniversityService` (admin CRUD only; thin) | No complex lifecycle |
| `User` | `UserService`, `AuthService` (registration/credentials) | `active_university` changes go through `UserService.set_active_university()` |
| `VendorProfile` | `VendorApplicationService`, `VendorVerificationService`, `VendorSuspensionService` | Application intake vs. status transitions vs. suspension cascade are deliberately separate service concerns |
| `VendorDocument` | `VendorDocumentService` | Upload + (future) review actions |
| `Store` | `StoreService` | Profile edits; `is_active` is *set by* `VendorSuspensionService`, not `StoreService` directly |
| `Category` | `CategoryService` | Tree management (admin-only, most of it post-MVP per PRD) |
| `Product` | `ProductService`, `InventoryService`, `ProductLifecycleService` | Creation/edit vs. quantity/stock vs. expiry/suspension/removal state — three distinct responsibilities per the architecture's file layout |
| `ProductImage` | `ProductImageService` (or a method-set within `ProductService`) | Enforces primary-image and 8-image-cap invariants |
| `ProductCategory` | `ProductService` (as part of product create/update) | Not independently service-owned |
| `Conversation` | `ConversationService` | Initiation rule, transaction-completion marking |
| `Message` | `MessageService` | Persistence-first, then broadcast via Channels consumer |
| `MessageAttachment` | `MessageService` (future) | Dormant in MVP |
| `Review` | `ReviewService` | Eligibility check against `Conversation`, create/edit |
| `Report` | `ReportService` | Lifecycle transitions; calls into `VendorSuspensionService`/`ProductLifecycleService` on resolution, never mutates those models directly |
| `Notification` | `NotificationService` | Record creation; dispatch delegated to `NotificationDispatcher` strategy |
| `DeviceToken` | `NotificationService` (device registration sub-concern) | Registration/deactivation |

---

## 11. Query Patterns

| Use Case | Representative Query Shape | Supporting Index(es) |
|---|---|---|
| Browse products (default marketplace view) | `Product.objects.filter(university=u, status=ACTIVE).order_by('-listed_at')` | `(university_id, status)` composite, `listed_at` |
| Product keyword search | `Product.objects.filter(university=u, status=ACTIVE).annotate(rank=...).filter(search_vector=SearchQuery(q))` | `(university_id, status)`, GIN on `search_vector` |
| Category-filtered browse | Join through `ProductCategory` filtered by `category_id`, further filtered by university/status | `(category_id, product_id)` on `ProductCategory`, `(university_id, status)` on `Product` |
| Price-range filter / price sort | `.filter(price__gte=lo, price__lte=hi).order_by('price')` | `price` |
| Vendor storefront page | `Store` by slug → `Product.objects.filter(store=store, status=ACTIVE)` + `Review.objects.filter(store=store)` | `Product.store` FK index, `Review.store_id` |
| "My conversations" (customer) | `Conversation.objects.filter(customer=u).order_by('-updated_at')` | `customer_id` |
| Vendor inbox | `Conversation.objects.filter(vendor=vp).order_by('-updated_at')` | `vendor_id` |
| Chat history (ordered thread) | `Message.objects.filter(conversation=c).order_by('created_at')` | `(conversation_id, created_at)` composite |
| Unread message count | `Message.objects.filter(conversation__in=..., read_at__isnull=True).count()` | Partial index `read_at IS NULL` |
| Review listing (storefront) | `Review.objects.filter(store=store).order_by('-created_at')` | `store_id` |
| Vendor verification queue (admin) | `VendorProfile.objects.filter(status=PENDING)` | `status` |
| Expiry sweep (scheduled job) | `Product.objects.filter(status=ACTIVE, expires_at__lte=now())` | `status`, `expires_at` |
| Report moderation queue (admin) | `Report.objects.filter(status=PENDING).order_by('created_at')` | `status` |
| Unread notifications badge | `Notification.objects.filter(recipient=u, read_at__isnull=True).count()` | Partial composite `(recipient_id, read_at) WHERE read_at IS NULL` |
| Active push targets for a user | `DeviceToken.objects.filter(user=u, is_active=True)` | `(user_id, is_active)` composite |
| Category tree rendering | `Category.objects.filter(parent=p, is_active=True).order_by('display_order')` | `(parent_id, display_order)` composite |
| Matric-number uniqueness check on application | `VendorProfile.objects.filter(university=u, matric_number=m).exists()` | Partial unique composite `(university_id, matric_number)` |

---

## 12. Future Extensibility

| Field / Model | Present Now | Dormant Until | Activation Path |
|---|---|---|---|
| `MessageAttachment` + `Message.content_type=IMAGE` | Schema exists, unused | Chat image attachments ship | `chat` service enables `IMAGE` path + upload validation; no migration needed |
| `Notification` + `DeviceToken` + `NotificationDispatcher` | Records + strategy interface exist, `NoOpDispatcher` bound | Real push delivery ships | Implement `FCMDispatcher`, swap the settings binding — no model change |
| `VendorDocument.status/reviewed_at/reviewed_by` | Fields exist, unused (MVP auto-approves) | Manual document review ships | Admin action calling a (future) `VendorDocumentService.review()` |
| `Product.views_count` | Incremented synchronously today | Traffic outgrows synchronous writes | Move to a debounced/cached counter (e.g., Redis + periodic flush) — same column, different write path |
| `products/search/` (folded-in module) | Postgres FTS today | An external search engine (Elasticsearch/OpenSearch) is introduced, or search-specific persisted concerns (e.g. `SearchLog`) are needed | Extract into a standalone `search` app per the architecture's documented trigger condition |
| `Category.display_order` | Exists from day one, default 0 | Admin reordering UI ships | `admin_dashboard` exposes a reordering endpoint; no schema change |
| `VendorDocumentType.BUSINESS_DOCUMENT` (enum value) | Reserved, unused | Post-MVP business-vendor supporting documents ship | No migration — enum value already valid, just starts being written |
| `VendorProfile.reviewed_by` / `reviewed_at` | Present, null in MVP (auto-approval) | Manual verification review ships | Admin action populates these fields; no schema change |
| `Product.created_by` | **Deliberately absent** — see Assumptions | Multi-staff-per-store concept is introduced | Additive nullable FK, since single-owner-per-store is universally true today (`Store → VendorProfile → User` fully derives current ownership) |

---

## 13. Assumptions

Documented explicitly per the "no hidden assumptions" requirement.

1. **`authentication` app owns no persisted models.** JWT issuance is handled statelessly (e.g., via `djangorestframework-simplejwt`); password reset uses Django's signed-token mechanism rather than a persisted `PasswordResetToken` table. If refresh-token blacklisting or reset-token audit logging is required, this introduces a small additive model later — flagged as an open question for the CTO review rather than pre-built speculatively.
2. **`User` is a custom model** extending `AbstractBaseUser` + `PermissionsMixin`, using `email` as `USERNAME_FIELD`, combined with `BaseModel`'s UUID PK/timestamp pattern (i.e., `BaseModel` is treated as compatible with Django's auth base classes via multiple inheritance, with `id` overriding the default auto-incrementing PK).
3. **Case-insensitive email uniqueness** is assumed as the correct behavior (industry standard) even though the PRD doesn't state it explicitly; implemented via lowercase-normalization on save plus a standard unique index (not `CITEXT`, to avoid an extra PostgreSQL extension dependency unless later deemed necessary).
4. **`Store.display_name`** is allowed to diverge from `VendorProfile.store_name` post-creation (vendor can rebrand their public storefront name without re-triggering verification) — the PRD does not explicitly forbid this, and splitting the fields preserves the verification record's integrity while allowing public flexibility. If the intent was for these to always stay in lockstep, this should be flagged and the field removed from `Store` in favor of always reading `VendorProfile.store_name`.
5. **`Product.campus_location`** is modeled as free text, not a structured/foreign-keyed location entity — the PRD lists "Campus / Location" as a single listing field with no indication of a controlled vocabulary, and no location-management feature appears anywhere else in the PRD.
6. **`REJECTED` (vendor) and `REMOVED_BY_ADMIN` (product) are treated as terminal states in MVP** — the PRD does not define a reapplication or restoration flow for either, so none is modeled. This should be explicitly confirmed; it is the single largest open lifecycle question in this DDS.
7. **One open store-level (product-less) conversation per customer-vendor pair** is treated as a business rule enforced in the service layer, not the database, because PostgreSQL's default NULL-distinct unique-index behavior cannot enforce it directly without a partial index keyed on `product_id IS NULL` — which is understood to be an acceptable, documented gap rather than a silent one.
8. **Reviews are not independently reportable** — the PRD's Reports section (§13) lists only Products and Vendors as reportable targets; `Report` has no `review` FK by design, not by oversight.
9. **`VendorDocument` "one document per vendor in MVP flow"** is enforced at the service layer only (no DB uniqueness constraint), per the architecture's explicit note — intentionally leaves room for multi-document support to be purely additive.
10. **Full-text search covers `Product.name` and `Product.description` only** (not category names, vendor/store names) — matches the architecture's explicit MVP search-strategy statement; broadening scope is a future decision, not assumed here.
11. **Soft-delete (`is_deleted`) is the default deletion behavior application-wide**; the `CASCADE`/`PROTECT`/`SET_NULL` choices documented in §8 govern *hard*-delete/FK-integrity behavior for the rare paths where a hard delete is legitimately triggered (e.g., admin hard-removal of clearly fraudulent data), not everyday user-facing "delete" actions, which should route through `is_deleted` toggling in the relevant service.
12. **`Message.body` max length** is left unbounded (`TextField`) rather than capped, consistent with typical chat UX; no PRD guidance either way.
13. **Notification retention/pruning** has no defined policy in MVP — records accumulate indefinitely; treated as an operational (not schema) concern for this phase.

---

*End of Database Design Specification v1.0. This document is ready for independent CTO architecture review. No implementation (models, serializers, services, migrations, or APIs) has been generated, per the stated completion criteria.*
