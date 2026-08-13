# UniAGORA Reviews

The `reviews` app manages customer reviews for completed marketplace
transactions.

Reviews are tied directly to `Conversation` records and are only permitted
after the vendor has marked the conversation's transaction as completed.

The app owns review creation and editing while keeping transaction eligibility
logic inside the service layer.

---

## Responsibilities

The reviews app is responsible for:

- Creating customer reviews
- Editing existing customer reviews
- Validating review eligibility
- Enforcing one review per conversation
- Validating ratings
- Exposing reviews for vendor stores
- Maintaining the denormalized `store` relationship used for storefront reads

The reviews app does **not** own:

- Conversations or transaction completion
- Messaging
- Vendor identity
- Store management
- Product management
- Report/moderation workflows

Transaction completion is owned by the `chat` app. Review eligibility is
checked against `Conversation.transaction_status`.

---

## Review Eligibility

A customer may create a review only when:

```text
Conversation.transaction_status == COMPLETED

The MVP does not introduce a separate Order or Transaction model.

The conversation's transaction status is the sole transaction-completion anchor
used for review eligibility.

Lifecycle:

Conversation
     │
     │ transaction completed
     ▼
COMPLETED
     │
     │ eligible
     ▼
Review created
     │
     │ customer edits
     ▼
Review updated

A conversation can have at most one review.

Data Model
Review
Field	Description
conversation	One-to-one relationship with the completed conversation
store	Denormalized reference to the vendor's store
rating	Integer rating from 1 to 5
comment	Optional customer comment
edited_at	Timestamp set when the review is edited
created_at	Creation timestamp
updated_at	Last update timestamp
Constraints
One review per conversation
Rating must be between 1 and 5
Conversation is required
Store is required
Comment is optional
Review eligibility is enforced by ReviewService
Review relationships use protected deletion semantics

The store field is intentionally denormalized from:

Review → Conversation → VendorProfile → Store

This provides a direct and indexed path for storefront review queries.

Service Layer

Business logic is centralized in ReviewService.

The service is responsible for:

Checking that the conversation is eligible
Creating reviews
Preventing duplicate reviews
Editing reviews
Updating edited_at
Resolving the store from the conversation when creating a review

Views and serializers should not contain review business rules.

API

All routes are versioned under:

/api/v1/

Responses follow the project-wide API envelope:

{
  "success": true,
  "message": "",
  "data": {}
}

Validation and business-rule failures follow:

{
  "success": false,
  "message": "",
  "errors": {}
}
Review Creation

Customer creates a review for an eligible completed conversation.

POST /api/v1/reviews/

Authentication:

Required

The request contains the review rating and optional comment. The conversation
and store relationships are resolved server-side according to the existing
conversation/vendor/store relationships.

Review Editing

A customer may edit their existing review.

PATCH /api/v1/reviews/{review_id}/

Authentication:

Required

Only the review owner may edit the review.

Store Reviews

Storefront review reads use the denormalized Review.store relationship.

Representative query:

Review.objects.filter(store=store).order_by("-created_at")

The store_id index supports this high-frequency storefront query.

Permissions

The app follows the project's centralized permission architecture.

Customers can:

Create eligible reviews
Edit their own reviews
View reviews according to the exposed API surface

Users cannot create reviews for conversations that they do not own or that
have not reached COMPLETED.

Business-rule authorization and eligibility checks remain in the service
layer.

Validation

The reviews app enforces:

Rating

Valid:

1
2
3
4
5

Invalid:

0
6
negative values
Transaction status

A review cannot be created while the conversation is:

ONGOING

It becomes eligible only when:

COMPLETED
Duplicate reviews

A conversation can have only one review.

The database OneToOneField provides the database-level uniqueness guarantee,
while the service layer provides the appropriate business-rule validation.

Database Indexing

The Review model has indexes supporting the primary read paths:

Review.store_id
Review.conversation_id

conversation_id is unique because each conversation can have at most one
review.

store_id provides efficient storefront review retrieval without requiring
the application to traverse:

Conversation → VendorProfile → Store

for every request.

Testing

The reviews app includes tests covering:

Review creation
Review eligibility
Completed vs. incomplete conversations
Duplicate review prevention
Rating validation
Optional comments
Review editing
Edit timestamps
Ownership and permissions
API response behavior
Store review retrieval

Run the reviews test suite with:

python manage.py test apps.reviews

Run the complete project test suite with:

python manage.py test
Architecture Alignment

The reviews app follows the frozen UniAGORA backend architecture:

Client
  │
  ▼
Reviews API
  │
  ▼
Serializers / Permissions
  │
  ▼
ReviewService
  │
  ├── Conversation eligibility
  │
  ├── Review creation/editing
  │
  └── Store resolution
  │
  ▼
Review

The app does not introduce an Order or Transaction model.

Transaction completion remains owned by chat, with:

Conversation.transaction_status

serving as the eligibility anchor for reviews.

MVP Scope

Included:

Customer reviews
1–5 ratings
Optional comments
Completed-transaction eligibility
One review per conversation
Review editing
Store-linked review retrieval

Not defined for MVP:

Review deletion
Review moderation
Review reporting
Seller responses
Review images
Review voting/helpfulness
Review lifecycle beyond creation and editing
