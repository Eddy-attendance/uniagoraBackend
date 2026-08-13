# Chat App

The `chat` app provides UniAGORA's buyer–vendor messaging system.

It supports:

- Customer-initiated conversations
- Vendor/customer participation enforcement
- Optional product association
- REST-based messaging
- Paginated message history
- Conversation completion
- Read-state management
- Unread message counts
- Real-time WebSocket messaging
- JWT-authenticated WebSocket connections
- Soft-deleted conversation/message handling

The implementation follows the frozen UniAGORA PRD, Backend Architecture, DDS, and approved chat engineering decisions.

---

## 1. Responsibilities

The chat app owns:

- `Conversation`
- `Message`
- Conversation lifecycle
- Message persistence
- Conversation participant authorization
- Message read state
- Conversation completion
- REST chat endpoints
- WebSocket message delivery

The app delegates business operations to services rather than embedding business logic inside views or consumers.

---

## 2. Domain Model

### Conversation

Represents a messaging thread between:

- One customer
- One vendor

A conversation may optionally reference a product.

Important fields include:

- `id`
- `customer`
- `vendor`
- `product`
- `transaction_status`
- `completed_at`
- `created_at`
- `updated_at`
- soft-delete fields

### Message

Represents an individual message within a conversation.

Important fields include:

- `id`
- `conversation`
- `sender`
- `content_type`
- `body`
- `read_at`
- `created_at`
- soft-delete fields

MVP messages are text-only.

---

## 3. Conversation Rules

### Initiation

Only customers initiate conversations.

The customer is always derived from the authenticated user.

Clients cannot submit or override the customer field.

A conversation may optionally reference a product.

If a product is supplied, it must belong to the selected vendor.

### Vendor eligibility

Conversation initiation requires a valid vendor profile.

Vendor verification eligibility is enforced by the service layer rather than duplicated in serializer validation.

This keeps business-rule failures consistent and allows the service layer to return the appropriate conflict response.

### Idempotency

Creating the same customer/vendor/product conversation repeatedly does not create duplicate conversations.

The API returns:

- `201 Created` when a new conversation is created
- `200 OK` when an existing conversation is resolved

---

## 4. REST API

Base URL:

```text
/api/v1/conversations/
```

### Create conversation

```http
POST /api/v1/conversations/
```

Request:

```json
{
    "vendor": "vendor-uuid",
    "product": "product-uuid"
}
```

`product` is optional.

The customer is derived from the authenticated user.

---

### List conversations

```http
GET /api/v1/conversations/
```

Returns conversations in which the authenticated user participates.

Both sides of a conversation are supported:

- Customer
- Vendor

Conversations are ordered by most recently updated.

The endpoint uses standard project pagination.

---

### Retrieve conversation

```http
GET /api/v1/conversations/{conversation_id}/
```

Only conversation participants may retrieve the conversation.

---

### Send message

```http
POST /api/v1/conversations/{conversation_id}/messages/
```

Request:

```json
{
    "body": "Is this product still available?"
}
```

The sender and conversation are derived server-side.

---

### List messages

```http
GET /api/v1/conversations/{conversation_id}/messages/
```

Messages are paginated and returned oldest-first.

Example response data:

```json
{
    "count": 2,
    "total_pages": 1,
    "current_page": 1,
    "page_size": 20,
    "next": null,
    "previous": null,
    "results": []
}
```

---

### Mark conversation as read

```http
POST /api/v1/conversations/{conversation_id}/read/
```

Marks unread messages from the other participant as read.

Example:

```json
{
    "marked_read": 3
}
```

Returns `200 OK`.

---

### Complete conversation

```http
POST /api/v1/conversations/{conversation_id}/complete/
```

Only the vendor may mark a transaction as completed.

Repeated completion attempts return a conflict.

---

## 5. API Response Format

Chat follows the global UniAGORA response envelope.

Successful responses:

```json
{
    "success": true,
    "message": "Message sent.",
    "data": {}
}
```

Failure responses follow the project's global error contract:

```json
{
    "success": false,
    "message": "...",
    "errors": {}
}
```

The shared response helpers and global renderer enforce this contract.

---

## 6. Conversation Representation

A conversation response contains fields including:

```json
{
    "id": "conversation-uuid",
    "customer": "user-uuid",
    "vendor": "vendor-uuid",
    "vendor_store_name": "Example Store",
    "product": "product-uuid",
    "product_name": "Example Product",
    "transaction_status": "ONGOING",
    "completed_at": null,
    "unread_count": 2,
    "created_at": "...",
    "updated_at": "..."
}
```

`unread_count` is calculated at the queryset level for list/retrieve operations to avoid an N+1 query pattern.

---

## 7. Message Representation

Example:

```json
{
    "id": "message-uuid",
    "conversation": "conversation-uuid",
    "sender": "user-uuid",
    "content_type": "TEXT",
    "body": "Hello, is this still available?",
    "read_at": null,
    "is_own": true,
    "created_at": "..."
}
```

`is_own` is calculated from the authenticated request user.

---

## 8. WebSocket API

Chat also supports real-time messaging through Django Channels.

WebSocket route:

```text
ws/chat/{conversation_id}/
```

Example:

```text
ws://localhost:8000/ws/chat/<conversation_id>/?token=<access_token>
```

JWT authentication is performed by the chat WebSocket authentication middleware.

---

## 9. WebSocket Authentication

A valid JWT access token must be supplied through the WebSocket connection.

Example:

```text
/ws/chat/<conversation_id>/?token=<access_token>
```

Unauthenticated connections are rejected.

A user may only connect to a conversation if they are:

- The customer
- The user associated with the vendor

Non-participants cannot join the conversation's channel group.

---

## 10. WebSocket Message Sending

Once connected, clients can send:

```json
{
    "body": "Is this still available?"
}
```

The consumer delegates message creation to:

```text
MessageService.send()
```

The WebSocket consumer does not duplicate message validation or persistence rules already implemented by the service layer.

---

## 11. WebSocket Broadcasting

Messages are persisted through the service layer before being broadcast.

The channel group is:

```text
conversation_{conversation_id}
```

After successful persistence, the message is broadcast to connected participants.

WebSockets are therefore treated as a delivery mechanism, not the system of record.

The database remains the source of truth for messages.

---

## 12. WebSocket Error Handling

Expected application errors are returned using a client-safe error message.

Example:

```json
{
    "error": "Message body is required."
}
```

Unexpected exceptions are logged server-side.

Internal exception details are never exposed to the WebSocket client.

Unexpected failures return:

```json
{
    "error": "Unable to send message."
}
```

This prevents database errors, stack traces, and internal implementation details from leaking through the real-time transport.

---

## 13. Layering

The chat app follows the project's application-layer separation.

### Serializers

Responsible for:

- Input validation
- Output serialization

They do not contain business workflows.

### Views

Responsible for:

- HTTP request handling
- Authentication/permission integration
- Serializer orchestration
- Delegating mutations to services
- Returning API responses

### Services

Responsible for:

- Conversation initiation
- Message creation
- Conversation completion
- Read-state updates
- Business-rule enforcement

### Consumer

Responsible for:

- WebSocket connection lifecycle
- Authentication state
- Conversation authorization
- Channel-group membership
- Receiving messages
- Delegating persistence to services
- Broadcasting persisted messages

---

## 14. Permissions

Conversation access is participant-restricted.

A participant is either:

```text
Conversation.customer
```

or:

```text
Conversation.vendor.user
```

Operations such as:

- Retrieve conversation
- View messages
- Send messages
- Mark messages read
- Complete conversation

are protected according to their respective business rules.

Vendor completion is restricted to the vendor side of the conversation.

---

## 15. Pagination

Chat uses the shared:

```text
StandardResultsSetPagination
```

Configuration:

```text
Default page size: 20
Maximum page size: 100
Query parameter: page_size
```

Pagination metadata is nested inside the global `data` envelope.

---

## 16. URL Structure

REST endpoints are mounted at:

```text
/api/v1/conversations/
```

The project-level URL configuration includes:

```python
path("api/v1/chat/", include("apps.chat.urls")),
```

The chat app's router registers:

```text
conversations/
```

Therefore the effective REST API is:

```text
/api/v1/chat/conversations/
```

> **Important:** The current project-level URL configuration prefixes the chat router with `/api/v1/chat/`. If the intended frozen API contract is `/api/v1/conversations/`, the project-level include must be adjusted accordingly. The chat router itself does not add the `chat/` prefix.

WebSocket routing is independent of the REST prefix:

```text
/ws/chat/{conversation_id}/
```

---

## 17. Testing

The chat app contains tests covering:

### Serializers

- Valid conversation creation
- Product/vendor ownership validation
- Vendor eligibility
- Blank message validation
- Read-only fields
- Unread count behavior
- Message ownership representation

### Views

- Authentication requirements
- Conversation creation
- Idempotent conversation creation
- Vendor initiation rejection
- Product association
- Conversation listing
- Vendor-side conversation listing
- Participant retrieval
- Non-participant access rejection
- Message sending
- Message listing
- Pagination
- Message ordering
- Conversation completion
- Completion conflicts
- Read-state updates
- Non-participant read rejection
- Response envelope structure

### WebSockets

- Unauthenticated connection rejection
- Non-participant connection rejection
- Customer connection
- Vendor connection
- Message persistence
- Message broadcasting
- Blank message rejection
- Generic unexpected-error handling

Run the app test suite with:

```bash
python manage.py test apps.chat
```

Current verified result:

```text
Ran 76 tests
OK
```

---

## 18. Important Engineering Decisions

### Service-layer business rules

Business rules are centralized in services rather than duplicated across REST and WebSocket transports.

This ensures REST and WebSocket messaging behave consistently.

### SQL-level unread counts

Unread counts are annotated in the conversation queryset rather than calculated individually in the serializer.

This prevents an N+1 query pattern when listing conversations.

### Participant authorization

Authorization is enforced before users are allowed to retrieve conversations or join WebSocket groups.

### Client-safe WebSocket errors

Unexpected exceptions are logged internally while clients receive only a generic error.

### Explicit response envelopes

Chat uses the project's shared `success_response()` helper and global response renderer.

### Conversation ordering

Conversation querysets are explicitly ordered by:

```python
.order_by("-updated_at")
```

This avoids Django's `UnorderedObjectListWarning` when paginating conversations and ensures the most recently active conversations appear first.

---

## 19. Files

Typical chat app structure:

```text
apps/chat/
├── __init__.py
├── admin.py
├── apps.py
├── consumers.py
├── models.py
├── permissions.py
├── routing.py
├── serializers.py
├── urls.py
├── views.py
├── services/
│   ├── __init__.py
│   ├── conversation_service.py
│   ├── message_service.py
│   └── broadcast.py
└── tests/
    ├── __init__.py
    ├── helpers.py
    ├── test_consumers.py
    ├── test_models.py
    ├── test_serializers.py
    ├── test_services.py
    └── test_views.py
```

---

## 20. Status

**Implementation status: Complete**

Latest verification:

```text
python manage.py test apps.chat

76 tests
76 passed
0 failures
```

The chat app is ready for project-wide integration testing and frontend consumption.
