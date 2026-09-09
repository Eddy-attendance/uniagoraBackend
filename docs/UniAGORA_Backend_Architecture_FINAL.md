# UniAGORA Backend Architecture — FINAL (Frozen)

Version: 2.0 (Frozen)
Status: Approved — all future implementation must conform to this document.
Stack: Python 3.13+, Django 5+, DRF, PostgreSQL, JWT, Django Channels, Cloudinary, FCM (future)
Supersedes: v1.0 draft architecture

---

## 1. Final Project Structure

```
backend/
├── config/                        # settings (base/dev/prod), root urls, asgi.py, wsgi.py
├── apps/
│   ├── common/                    # Pure generic infra — zero domain knowledge
│   │   ├── models.py              #   BaseModel (UUID pk, created_at, updated_at, is_deleted)
│   │   ├── response.py            #   success_response() / error_response() envelope helpers
│   │   ├── exceptions.py          #   custom DRF exception handler
│   │   ├── pagination.py          #   standard page-number pagination class
│   │   ├── fields.py              #   generic Cloudinary field / upload validators
│   │   └── mixins.py              #   generic, domain-agnostic mixins
│   │
│   ├── core/                      # Domain-aware cross-cutting concerns
│   │   ├── permissions.py         #   IsAuthenticatedCustomer, IsVerifiedVendor,
│   │   │                          #   IsOwnerVendor, IsAdmin
│   │   └── filters.py             #   ActiveUniversityFilterBackend
│   │
│   ├── authentication/            # Register, login, logout, password reset, JWT issuance
│   ├── users/                     # User model, active_university selection
│   ├── universities/              # University entity
│   ├── vendors/                   # VendorProfile, VendorDocument, verification lifecycle
│   ├── stores/                    # Store entity (1:1 with Vendor)
│   ├── categories/                # Hierarchical category tree
│   ├── products/                  # Listings, images, inventory, lifecycle/expiry
│   │   ├── models.py
│   │   ├── services/
│   │   │   ├── product_service.py
│   │   │   ├── inventory_service.py
│   │   │   └── lifecycle_service.py    # expiry, suspension hide/reinstate
│   │   └── search/                     # (folded in — see Section 11)
│   │       ├── filters.py              # category/price/condition composition
│   │       └── queries.py              # Postgres FTS SearchVector/SearchQuery
│   │
│   ├── chat/                      # Conversations, messages, (future) attachments
│   ├── reviews/                   # Reviews tied to completed transactions
│   ├── reports/                   # Product/Vendor reports + moderation lifecycle
│   ├── notifications/             # Notification records + FCM delivery abstraction
│   └── admin_dashboard/           # Admin-only aggregation + action endpoints
```

**Dependency rule**: `common` imports nothing domain-specific and is importable by everything. `core` may import domain models (`User`, `VendorProfile`, `University`) but nothing imports `core` circularly — it sits directly above domain apps, below nothing except `common`.

---

## 2. Final App Boundaries

| App | Owns | Does NOT own |
|---|---|---|
| `common` | Generic infra: envelope, pagination, base model, generic fields | Any domain model or business rule |
| `core` | Domain-aware permissions, university-scoping filter backend | Models, migrations |
| `authentication` | Register/login/logout/password reset, JWT issuance | User profile data, roles |
| `users` | `User` model, `active_university` | Vendor identity, store data |
| `universities` | `University` entity | User-university assignment logic (lives in `users`) |
| `vendors` | `VendorProfile`, `VendorDocument`, verification status/lifecycle | Storefront presentation (→ `stores`) |
| `stores` | `Store` (1:1 Vendor), public storefront profile | Verification/document data |
| `categories` | Category tree | Product-category assignment logic (→ `products`) |
| `products` | Products, images, inventory, lifecycle/expiry, search composition | Vendor identity, store profile |
| `chat` | Conversations, messages, transaction-completion flag | Reviews, notifications delivery |
| `reviews` | Reviews, eligibility checks against chat's transaction flag | Chat, moderation |
| `reports` | Report lifecycle (Pending → Under Review → Resolved/Rejected) | Product/vendor suspension actions themselves (calls into `vendors`/`products` services) |
| `notifications` | Notification records, device tokens, dispatch abstraction | The events that trigger notifications (each domain app calls into `notifications`, not the reverse) |
| `admin_dashboard` | Aggregation/read endpoints, admin-gated calls into other apps' services | Any of its own persisted domain models |

No app owns Cart, Orders, Payments, Wallet, Delivery, or Rider concepts — confirmed out of MVP scope.

---

## 3. Domain Model Relationships

```
University ──< User >── (active_university, nullable until onboarding)
User ──1:1── VendorProfile ──1:1── Store
VendorProfile ──< VendorDocument
VendorProfile }── University   (locked at application time; matric unique per (university, matric_number))

Store ──< Product >── Category   (via ProductCategory through-table)
Product ──< ProductImage
Product }── University          (denormalized copy, set at creation, for query performance)

User (customer) ──< Conversation >── VendorProfile
Conversation }── Product (nullable)
Conversation ──< Message ──1:1── MessageAttachment (schema-ready, unused in MVP)
Conversation: transaction_status (ONGOING / COMPLETED) — anchor for review eligibility

Conversation ──< Review          (eligibility: conversation.transaction_status == COMPLETED)
Review }── Store                 (denormalized FK — see Section 4)

User ──< Report >── {Product | Vendor}   (exactly one of two nullable FKs set, check constraint)
Report }── resolved_by (User, admin, nullable)

User ──< Notification
User ──< DeviceToken
```

Key relationship decisions carried from the approved draft, unchanged:
- Vendor identity (`vendors`) and storefront presentation (`stores`) remain split — different read/write surfaces, different sensitivity (documents vs. public profile).
- No `Order`/`Transaction` model exists; `Conversation.transaction_status` is the sole, minimal anchor for review eligibility.

---

## 4. Database Indexing Strategy

| Model | Index | Purpose |
|---|---|---|
| `Product` | composite `(university, status)` | Primary browse query: active listings in the user's active university |
| `Product` | `status` | Moderation/admin queries, lifecycle jobs (expiry sweep) |
| `Product` | `price` | Price-range filters, lowest/highest-price sort |
| `Product` | `listed_at` (created_at) | "Newest" sort |
| `Product` | `expires_at` | Expiry sweep job (`expires_at <= now() AND status = ACTIVE`) |
| `Product` | `slug` (unique) | Public detail-page lookup by slug |
| `Product` | `GinIndex` on `search_vector` (FTS) | Postgres full-text search |
| `ProductCategory` | composite `(category, product)` | Category-filtered browse |
| `VendorProfile` | `status` | Verification queue, suspension-hide logic |
| `VendorProfile` | unique composite `(university, matric_number)` | Per-university matric uniqueness (doubles as index) |
| `Conversation` | `customer` | "My conversations" list |
| `Conversation` | `vendor` | Vendor inbox |
| `Conversation` | unique composite `(customer, vendor, product)` | Duplicate-thread prevention (doubles as index) |
| `Message` | composite `(conversation, created_at)` | Ordered thread pagination |
| `Message` | partial index `read_at IS NULL` | Unread-count queries |
| `Review` | `store` (denormalized FK — see below) | "All reviews for this store" without joining through Conversation → Vendor → Store |
| `Review` | `conversation` | Eligibility/audit lookups |
| `Report` | `status` | Admin moderation queue |
| `Report` | `product`, `vendor_profile` (each, nullable) | Lookup reports against a given target |
| `Notification` | composite `(recipient, read_at)` (partial on `read_at IS NULL`) | Unread notification badge/count |
| `DeviceToken` | composite `(user, is_active)` | Active token lookup for dispatch |
| `Category` | composite `(parent, display_order)` | Ordered children within a parent |

**Design addition arising from indexing review**: `Review` gains a denormalized `store` FK (set once at creation from `conversation.vendor.store`, immutable thereafter). Without it, "show all reviews for Store X" requires joining `Review → Conversation → VendorProfile → Store` on every storefront page load — a join that's avoidable with a small, intentional denormalization. This is the same pattern already used for `Product.university` and is justified for the same reason: a read path that executes on effectively every page view deserves a direct index, not a multi-hop join.

---

## 5. Constraints

- `VendorProfile`: `UNIQUE(university_id, matric_number)` — matric numbers unique per university, not globally.
- `VendorProfile`: `OneToOneField(User)` — one vendor profile per account.
- `Store`: `OneToOneField(VendorProfile)` — one store per vendor.
- `Conversation`: `UNIQUE(customer_id, vendor_id, product_id)` — one thread per customer/vendor/product context.
- `Report`: `CHECK` — exactly one of `product_id` / `vendor_profile_id` is non-null.
- `ProductImage`: enforced at service layer (not DB) — exactly one `is_primary=True` per product, max 8 images per product. (Left as a service-layer invariant rather than a DB constraint since "exactly one primary" across a mutable ordered set is awkward to express as a pure SQL constraint without a partial unique index trick; a partial unique index on `(product_id) WHERE is_primary` is used as a belt-and-suspenders DB-level backstop.)
- `MessageAttachment`: `OneToOneField(Message)` — at most one attachment per message (schema-ready, unused in MVP).
- All FKs use `on_delete=PROTECT` or `SET_NULL` per domain meaning (e.g. deleting a `Category` should not cascade-delete `Product` rows — `ProductCategory` rows are removed, products remain); hard `CASCADE` is reserved for genuinely dependent child rows (`ProductImage`, `VendorDocument`, `Message` → `MessageAttachment`).

---

## 6. Design Patterns Used

- **Service Layer pattern** — all business logic in `services.py`/`services/` per app; views and serializers never contain business rules.
- **Strategy pattern** — `NotificationDispatcher` interface with swappable implementations (`NoOpDispatcher` now, `FCMDispatcher` later) behind one settings-driven binding.
- **Repository-lite via querysets/managers** — custom model managers (e.g. `Product.objects.visible()`, `Product.objects.for_university(u)`) centralize common query shapes instead of repeating `.filter()` chains across views.
- **Template Method-ish lifecycle service** — `ProductLifecycleService` centralizes the three distinct "not visible" transitions (expired, suspension-hidden, admin-removed) and their respective reactivation rules, rather than scattering conditional visibility logic across views.
- **Denormalization-for-read-performance** — deliberate, documented, limited to fields set once at creation and never a source of truth on their own (`Product.university`, `Review.store`).
- **Facade** — `admin_dashboard` app has no models of its own; it's a thin facade over other apps' services, gated by `IsAdmin`, guaranteeing one code path per business action regardless of which role triggers it.

---

## 7. Service Layer Conventions

- Every domain app with mutating business logic has a `services.py` (or `services/` package if it splits by concern, e.g. `products/services/`).
- **Views call services; services never import from `views.py` or `serializers.py`** — one-directional dependency, keeps services independently testable without DRF request/response objects.
- Services are plain functions or thin stateless classes (`XService.method(...)`), not model methods, when the operation spans more than one model or has side effects (e.g. `VendorSuspensionService.suspend()` touches both `VendorProfile` and `Product`). Single-model, no-side-effect logic (e.g. `Product.is_out_of_stock`) can remain a model property.
- Services are the transaction boundary: any operation touching multiple rows/models wraps in `transaction.atomic()` inside the service, not in the view.
- Services raise domain-specific exceptions (e.g. `VendorNotVerifiedError`, `ReviewNotEligibleError`), caught once by the shared `common/exceptions.py` handler and translated into the standard error envelope — views never need their own try/except blocks for expected business-rule failures.

---

## 8. Permission Architecture

- Defined once in `core/permissions.py`, composed (not reimplemented) per view:
  - `IsAuthenticatedCustomer` — base authenticated-user check (every logged-in user is a Customer).
  - `IsVerifiedVendor` — authenticated + has a `VendorProfile` with `status == VERIFIED`.
  - `IsOwnerVendor` — object-level; the request user's own `VendorProfile`/`Store` owns the target object. Never trusts a vendor/store ID from the request body.
  - `IsAdmin` — `is_staff`/`is_superuser`.
- Role state is **computed from relations, not stored as a redundant field** (`user.is_vendor`, `user.is_admin` as properties) — avoids a denormalized role flag drifting from the actual `VendorProfile`/`is_staff` state.
- Business-rule-level authorization (e.g. "only a Customer, not a Vendor, may *initiate* a conversation") is enforced in the **service layer**, not only via permission classes — this is a rule about role-in-this-interaction, not blanket resource access, and permission classes alone can't express it cleanly.

---

## 9. API Conventions

- All routes under `/api/v1/`.
- Every response — success, validation failure, or unhandled exception — conforms to:
  ```
  Success: {"success": true, "message": "", "data": {}}
  Failure: {"success": false, "message": "", "errors": {}}
  ```
  enforced globally via a shared renderer + `common/exceptions.py` custom exception handler, so no individual view can break the contract.
- Standard page-number pagination (`common/pagination.py`), pagination metadata nested inside `data`.
- Endpoint/field naming and URL structure changes require sign-off per the Backend Responsibility doc's "Never rename response fields / change URLs without agreement" rule — documentation (method, URL, auth requirement, request/response/error shapes) is updated in lockstep with any change.

---

## 10. Media Strategy

- One reusable Cloudinary-backed field/upload path in `common/fields.py`, used identically by: product images, vendor documents, business logos, and (future) chat attachments — one validation code path (file type/size checks, signed upload where applicable) rather than per-model reimplementation.
- `ProductImage`: max 8 per product, exactly one `is_primary` (service-enforced + DB partial-unique backstop, see Section 5).
- `VendorDocument`: one document per vendor in MVP submission flow, modeled as its own table so multiple/resubmission support is additive later, not a breaking change.

---

## 11. Search Strategy

- **No standalone `search` app.** Search composition lives inside `products/search/` (`filters.py` for category/price/condition composition, `queries.py` for Postgres FTS). This keeps a single source of truth for "what counts as a visible, queryable product" — the same visibility rules (status, university scope) apply whether the request is a plain browse or a keyword search, with no risk of the two diverging across separate apps.
- MVP implementation: `django.contrib.postgres.search` `SearchVector`/`SearchQuery` over `Product.name` + `Product.description`, backed by a `GinIndex` on a stored `search_vector` field.
- Extraction trigger for a future standalone `search` app: adoption of an external search engine (Elasticsearch/OpenSearch) requiring its own sync pipeline/models, or addition of search-specific persisted concerns (e.g. a `SearchLog` for analytics). Until then, a separate app would own no models and violate the same principle that folded it in.

---

## 12. Real-Time Architecture

- Django Channels (ASGI, alongside WSGI/DRF), Redis-backed channel layer for multi-process broadcast.
- One consumer group per conversation (`conversation_{id}`); JWT-authenticated at socket handshake using the same auth backend as REST.
- **Messages are always persisted via the REST/service layer first, then broadcast** — the websocket layer is never the system of record. This keeps chat history consistent and testable independent of the socket connection, and means a dropped socket connection never risks losing a message.
- Scope limited to chat delivery in MVP. Push notifications (FCM) are a separate, unrelated delivery path (device push, not a websocket) — intentionally not conflated with the Channels layer.

---

## 13. Future Extensibility Decisions (built in now, inactive until needed)

| Concern | What's in place now | What activates it later, without a breaking change |
|---|---|---|
| Chat image attachments | `MessageAttachment` model + `Message.content_type` enum exist; only `TEXT` is ever created | Enable `IMAGE` creation path + upload validation in `chat` services |
| Push notifications | `Notification`, `DeviceToken` models; `NotificationDispatcher` interface with `NoOpDispatcher` | Implement `FCMDispatcher`, swap the settings binding |
| Vendor document review | `VendorDocument.status/uploaded_at/reviewed_at/reviewed_by` fields exist even though MVP auto-approves | Add manual-review admin action calling `VendorDocumentService.review()` |
| Multi-staff stores | Not modeled (`created_by` deliberately omitted — see feedback response) | Add nullable `Product.created_by` FK if/when multi-user store management becomes a requirement |
| Product view analytics | `views_count` field exists, incremented synchronously at MVP scale | Move increment to a debounced/cached counter if traffic makes it a contention point |
| Standalone search app | Lives inside `products/search/` | Extract to its own app if an external search engine or search-specific models are introduced |
| Category ordering | `display_order` field exists from day one | Admin dashboard exposes reordering UI/endpoint whenever prioritized |

---

## 14. Explicitly Out of Scope (unchanged)

No `Order`, `Cart`, `CartItem`, `Payment`, `WalletTransaction`, `Delivery`, `RiderProfile`, or `Escrow` models exist anywhere in this schema. `Conversation.transaction_status` remains the sole, intentionally minimal concession to "a transaction happened."

---

This document is now frozen as the backend architecture baseline for UniAGORA. Implementation should proceed in the previously agreed build order (`common` + `core` → `universities` → `authentication`/`users` → `vendors`/`stores` → `categories` → `products` → `chat` → `reviews` → `reports` → `notifications` → `admin_dashboard`), with any deviation requiring the same explicit sign-off process used for this refinement round.
