# Categories App

The `categories` app owns UniAGORA's product category taxonomy.

It provides a hierarchical category tree with support for root categories and nested subcategories. Category management is admin-controlled, while authenticated customers can browse active categories.

## Responsibility

The app owns only the `Category` model and its related taxonomy logic.

### Responsibilities

* Create categories and subcategories
* Maintain hierarchical parent-child relationships
* Generate unique slugs automatically
* Control category activation/deactivation
* Soft-delete categories
* Prevent deletion while alive child categories exist
* Provide customer-facing category browsing
* Enforce sibling-name uniqueness among alive categories

### Not Responsible For

* Products or product listings
* Universities
* Users
* Vendors or stores
* Reparenting categories
* Reordering categories through the API

Reparenting and explicit category reordering are outside the MVP API surface.

## Model

### `Category`

| Field           | Description                                    |
| --------------- | ---------------------------------------------- |
| `id`            | UUID primary key                               |
| `name`          | Category name                                  |
| `slug`          | Unique auto-generated URL slug                 |
| `parent`        | Optional self-referential parent category      |
| `display_order` | Ordering value within a category level         |
| `is_active`     | Whether the category is available for browsing |
| `is_deleted`    | Soft-delete flag                               |
| `created_at`    | Creation timestamp                             |
| `updated_at`    | Last-update timestamp                          |

Categories use a self-referential foreign key with `PROTECT`, preventing a category from being physically orphaned through parent deletion.

The model also exposes:

* `is_root` — identifies root categories
* `__str__()` — returns the category breadcrumb, e.g. `Electronics > Phones`

## Uniqueness

Alive categories enforce database-level name uniqueness.

### Root categories

Root category names must be unique among alive categories.

```text
Electronics
Electronics  ❌
```

### Child categories

Child names must be unique within their immediate parent.

```text
Electronics
├── Phones
└── Phones  ❌
```

The same name may exist under different parents:

```text
Electronics
└── Phones

Fashion
└── Phones  ✅
```

Soft-deleted categories do not occupy the name namespace and their names may be reused.

## QuerySet

`CategoryQuerySet.visible()` returns categories that are:

* alive
* active

This is the customer-facing category visibility shape.

```python
Category.objects.visible()
```

`alive()` and `dead()` are inherited from the common soft-delete infrastructure.

## Service Layer

Business mutations are handled by `CategoryService`.

### Supported operations

* `create()`
* `update()` — rename only
* `activate()`
* `deactivate()`
* `delete()` — guarded soft-delete

Category creation allows the initial `parent` and `display_order` to be specified.

After creation:

* `name` can be changed
* `parent` cannot be changed through the MVP API
* `display_order` cannot be changed through the MVP API
* `is_active` is controlled through dedicated activate/deactivate actions

### Deletion rule

A category cannot be soft-deleted while it has **any alive child**, whether that child is active or inactive.

Children must first be soft-deleted.

This prevents an alive child from referencing a deleted parent.

## API

Base path:

```text
/api/v1/categories/
```

| Method          | Endpoint                         | Permission             | Purpose                   |
| --------------- | -------------------------------- | ---------------------- | ------------------------- |
| `GET`           | `/categories/`                   | Authenticated customer | List visible categories   |
| `GET`           | `/categories/{slug}/`            | Authenticated customer | Retrieve visible category |
| `POST`          | `/categories/`                   | Admin                  | Create category           |
| `PATCH` / `PUT` | `/categories/{slug}/`            | Admin                  | Rename category           |
| `POST`          | `/categories/{slug}/activate/`   | Admin                  | Activate category         |
| `POST`          | `/categories/{slug}/deactivate/` | Admin                  | Deactivate category       |
| `DELETE`        | `/categories/{slug}/`            | Admin                  | Soft-delete category      |

### Parent filtering

The list endpoint supports:

```text
GET /api/v1/categories/?parent=<slug>
```

and root-category filtering using:

```text
GET /api/v1/categories/?parent=null
```

Only active and alive categories are exposed through customer reads.

## Serializers

### `CategorySerializer`

Read-only response representation.

The parent is represented by its slug.

### `CategoryCreateSerializer`

Accepts:

* `name`
* `parent`
* `display_order`

The slug and activation state are controlled by the backend.

### `CategoryUpdateSerializer`

Only accepts:

* `name`

Duplicate sibling names are rejected while names belonging to soft-deleted siblings may be reused.

## Permissions

Customer reads use:

```python
IsAuthenticatedCustomer
```

Administrative mutations use:

```python
IsAdmin
```

No category management operation is exposed to ordinary customers.

## Soft Delete

Categories use the common soft-delete mechanism.

Calling:

```python
category.delete()
```

marks the category as deleted rather than physically removing the database row.

Deleted categories:

* are excluded from `alive()`
* are excluded from `visible()`
* do not block reuse of category names
* remain available for historical database integrity

## Testing

The app contains focused tests covering:

* model behavior
* hierarchy and breadcrumbs
* root/child uniqueness
* soft-delete behavior
* manager visibility
* service mutations
* activation/deactivation conflicts
* guarded deletion
* serializer validation
* API permissions
* API filtering
* API mutation behavior


## Migration

The initial migration creates:

* `categories_category`
* self-referential `parent` foreign key
* unique slug constraint
* alive root-name constraint
* alive child-name-per-parent constraint
* `(parent, display_order)` index
* `is_active` and `is_deleted` indexes

The app has no dependency on other domain apps.

## Future Scope

The schema intentionally supports capabilities that are not exposed in the MVP API:

* category reparenting
* category sibling reordering
* richer tree-management operations

These should only be introduced when explicitly authorized by the product requirements and architecture.
