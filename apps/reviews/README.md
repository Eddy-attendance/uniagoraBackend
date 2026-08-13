# Reviews App

The `reviews` app manages customer reviews for completed marketplace transactions.

Reviews are intentionally tied to the existing `chat.Conversation` transaction lifecycle rather than introducing a separate Order or Transaction model. A customer becomes eligible to review only after the vendor marks the conversation's transaction as completed.

This follows the frozen UniAGORA architecture and MVP product requirements.

## Responsibilities

The reviews app is responsible for:

* Creating customer reviews.
* Validating review eligibility.
* Enforcing one review per conversation.
* Editing existing reviews.
* Validating ratings from 1–5.
* Associating reviews with the relevant store.
* Listing reviews for stores.
* Preventing unauthorized review creation or modification.

The app does **not** own:

* Conversations.
* Transaction completion.
* Vendor verification.
* Store management.
* Moderation/report workflows.
* Notifications.

Those responsibilities remain with their respective domain apps.

## Architecture

The review lifecycle is:

```text
Customer
   │
   ▼
Conversation
   │
   │ transaction_status = COMPLETED
   ▼
ReviewService
   │
   ├── Validate eligibility
   ├── Validate ownership
   ├── Prevent duplicate review
   └── Create Review
          │
          ▼
       Store
```

The `Conversation.transaction_status` field is the sole review-eligibility anchor defined by the frozen architecture.

No separate `Transaction` or `Order` model is introduced for reviews.

## Data Model

### Review

A review contains:

| Field          | Description                                                        |
| -------------- | ------------------------------------------------------------------ |
| `id`           | UUID primary key inherited from `BaseModel`                        |
| `conversation` | One-to-one relationship with the reviewed transaction conversation |
| `store`        | Denormalized reference to the reviewed store                       |
| `rating`       | Integer rating from 1 to 5                                         |
| `comment`      | Optional customer comment                                          |
| `edited_at`    | Timestamp populated when a review is edited                        |
| `created_at`   | Creation timestamp                                                 |
| `updated_at`   | Last modification timestamp                                        |
| `is_deleted`   | Soft-delete flag inherited from `BaseModel`                        |

The `store` relationship is intentionally denormalized from the conversation/vendor/store relationship. This provides an efficient direct query path for storefront review listings.

## Business Rules

### Review Eligibility

A customer may create a review only when:

```text
Conversation.transaction_status == COMPLETED
```

A conversation that is still `ONGOING` is not reviewable.

### One Review Per Transaction

Each conversation can have at most one review.

This is enforced structurally through the one-to-one relationship between `Review` and `Conversation`.

### Rating

Ratings must be within:

```text
1 <= rating <= 5
```

### Comment

Comments are optional.

### Editing

Customers may edit their own reviews.

Editing updates the review content and records the `edited_at` timestamp.

### Ownership

A customer may only modify their own review.

The review service is responsible for enforcing the business rule rather than relying solely on client-provided identifiers or frontend behavior.

## Service Layer

Business logic belongs in the reviews service layer.

Views and serializers should remain responsible for request/response handling and validation presentation rather than implementing review workflows directly.

The service layer handles concerns such as:

* Review creation.
* Transaction-completion eligibility.
* Duplicate-review prevention.
* Review ownership.
* Review editing.
* Store association.

This follows the frozen architecture's service-layer convention that domain operations and multi-step business rules belong in services.

## API

All Reviews API endpoints follow the project-wide `/api/v1/` convention and the standard response envelope.

### Create Review

```http
POST /api/v1/reviews/
```

Requires authentication.

A customer submits a review for an eligible completed conversation.

Example request:

```json
{
  "conversation": "<conversation-uuid>",
  "rating": 5,
  "comment": "Great seller and smooth transaction."
}
```

### List Store Reviews

Reviews can be retrieved through the store review endpoint defined by the implementation.

The store relationship exists directly on `Review` so storefront review queries do not require repeatedly traversing:

```text
Review → Conversation → VendorProfile → Store
```

### Update Review

The review owner may edit their review through the implemented review update endpoint.

The rating and optional comment can be updated subject to the same validation rules.

## Response Format

The Reviews API follows the global UniAGORA response contract.

### Success

```json
{
  "success": true,
  "message": "",
  "data": {}
}
```

### Error

```json
{
  "success": false,
  "message": "",
  "errors": {}
}
```

This is consistent with the API standards defined for the backend.

## Permissions

Review operations require authentication.

The service layer additionally enforces review-specific authorization and eligibility rules.

The important distinction is:

* Authentication determines whether the caller is logged in.
* Permissions determine whether the caller can access the operation.
* Review services determine whether the specific conversation is eligible and whether the caller owns the review.

## Database Considerations

The Reviews model follows the project-wide database conventions:

* UUID primary key.
* Soft deletion through `BaseModel`.
* Foreign-key integrity.
* One-to-one conversation relationship.
* Direct store index for storefront review queries.
* Rating validation at application/database levels where applicable.

The frozen DDS explicitly defines `Review.store` as a deliberate denormalized field for read performance.

## Testing

The Reviews app has been validated through its automated test suite.

The completed implementation has passed all required checks, including the project-level validation performed after implementation.

Coverage areas include:

* Review creation.
* Completed-transaction eligibility.
* Rejection of incomplete transactions.
* Duplicate-review prevention.
* Rating validation.
* Optional comments.
* Review editing.
* Ownership/permission enforcement.
* Store review retrieval.
* API response behavior.
* Edge cases and invalid requests.

## Architectural Compliance

The implementation conforms to the frozen UniAGORA architecture by:

* Keeping review ownership inside `reviews`.
* Using `chat.Conversation.transaction_status` as the review eligibility anchor.
* Avoiding an unnecessary transaction/order model.
* Keeping business logic in the service layer.
* Using the shared API response structure.
* Maintaining the established `/api/v1/` API convention.
* Keeping store review queries efficient through the intentional `Review.store` denormalization.

The architecture identifies `reviews` as the domain responsible for reviews and eligibility checks against the chat transaction flag.

## Status

**Implementation: Complete**

**Validation: Passed**
