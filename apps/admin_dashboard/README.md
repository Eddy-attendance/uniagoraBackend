# `admin_dashboard` App

**Project:** UniAGORA Backend
**App:** `apps.admin_dashboard`
**Build order position:** (`common` → `core` → `universities` →
`users`/`authentication` → `vendors` → `stores` → `categories` → `products` →
`chat` → `reviews` → `reports` → **`admin_dashboard`**)


---

## Purpose

`admin_dashboard` is the model-less, admin-only facade completing the
MVP build order. Backend Architecture §2 defines it directly: *"Aggregation/
read endpoints, admin-gated calls into other apps' services... Does NOT
own: Any of its own persisted domain models."*

It supplies the two things no other app owns — cross-cutting dashboard
counts, and `User` activation/deactivation orchestration (the actual
mutation lives in `users`, see below) — and consolidates several
already-existing admin actions from `vendors`, `products`, `categories`,
and `reports` under a single `/api/v1/admin/` surface, without changing
any of those apps' own existing endpoint contracts.

## Responsibilities

| Domain | admin_dashboard provides | Mutation performed by |
|---|---|---|
| Dashboard / Analytics | `GET /admin/dashboard/` — cross-app counts | Read-only; no mutation |
| User Management | List/retrieve/activate/deactivate | `apps.users.services.UserService` |
| Vendor Management | List/retrieve/suspend/reinstate | `apps.vendors.services.VendorSuspensionService` |
| Product Moderation | List/retrieve/remove | `apps.products.services.lifecycle_service.ProductLifecycleService` |
| Category Management | List/retrieve/create/update/delete/activate/deactivate | `apps.categories.services.CategoryService` |
| Report Management | List/retrieve/mark-under-review/resolve/reject | `apps.reports.services.ReportService` |
| Platform Settings | **Not implemented** — see "Deferred / Not Implemented" below | N/A |

**No business rule is reimplemented anywhere in this app.** Every
mutating method in `services.py` either raises `NotFoundError` for a
missing target (a presentation-layer concern) or is a direct call into
the owning app's own service. See `services.py`'s module docstring for
the full boundary statement.

## Endpoints

All routes are mounted under `/api/v1/admin/` (see `urls.py`). Every
endpoint is gated by `core.permissions.IsAdmin` and nothing else — no
second permission/role system exists anywhere in this app.

```
GET    /admin/dashboard/

GET    /admin/users/
GET    /admin/users/{id}/
POST   /admin/users/{id}/activate/
POST   /admin/users/{id}/deactivate/

GET    /admin/vendors/
GET    /admin/vendors/{id}/
POST   /admin/vendors/{id}/suspend/
POST   /admin/vendors/{id}/reinstate/

GET    /admin/products/
GET    /admin/products/{id}/
POST   /admin/products/{id}/remove/

GET    /admin/categories/
POST   /admin/categories/
GET    /admin/categories/{slug}/
PATCH  /admin/categories/{slug}/
DELETE /admin/categories/{slug}/
POST   /admin/categories/{slug}/activate/
POST   /admin/categories/{slug}/deactivate/

GET    /admin/reports/
GET    /admin/reports/{id}/
POST   /admin/reports/{id}/under-review/
POST   /admin/reports/{id}/resolve/
POST   /admin/reports/{id}/reject/
```

Every response uses the project's standard envelope:

```json
// success
{"success": true, "message": "", "data": {}}
// failure
{"success": false, "message": "", "errors": {}}
```

## Authorization

- `core.permissions.IsAdmin` (`is_staff`/`is_superuser`) gates every
  view in this app. No `Admin` model, no `is_admin` database field, no
  second role system — per the task brief's explicit constraint.
- Unauthenticated and non-admin requests are rejected on every endpoint
  (see the permission-matrix tests in each `tests/test_*.py` file).
- Protected fields are never client-writable: `reporter`, report/product/
  vendor target identifiers, `status`, `resolved_by`, `resolved_at`, and
  internal resolution metadata are all either read-only in the response
  serializers or resolved server-side (URL path, `request.user`) — never
  accepted from request bodies. See `serializers.py`'s per-class
  docstrings.
- Target objects are always resolved server-side from a URL path
  parameter via each `*Service.get(...)`'s own `.alive()` queryset —
  never trusted from a request body, matching `core.IsOwnerVendor`'s own
  "never trust a client-supplied identifier" precedent.

## Service / Facade Boundary

```text
Admin Request
     ↓
admin_dashboard (this app — orchestration/presentation only)
     ↓
Owning Domain Service (UserService / VendorSuspensionService /
                        ProductLifecycleService / CategoryService /
                        ReportService)
     ↓
Domain Models / Business Rules
```

`admin_dashboard` performs target resolution (`*Service.get(...)`) and
read-only aggregation (`DashboardService.get_summary()`) directly against
`.alive()` querysets, because those are presentation/orchestration
concerns, not business mutations. **Every state-changing action is a
one-line delegation into the owning app's existing service** — see
`services.py` for the full mapping. This app introduces no second
business-logic layer for any model it touches.
