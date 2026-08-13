# Reports

The `reports` app manages customer reports against marketplace Products and
Vendors and provides the Admin moderation workflow.

## Responsibilities

- Create reports against Products and Vendors
- Track report reasons, descriptions, and status
- Manage the report moderation lifecycle
- Provide customer report history and detail views
- Provide Admin moderation and resolution workflows
- Delegate Product/Vendor moderation actions to their owning services

## Report Lifecycle

```text
PENDING → UNDER_REVIEW → RESOLVED
                     └──→ REJECTED

Reports may also move directly from PENDING to RESOLVED or REJECTED.

RESOLVED — moderation action was taken
REJECTED — no moderation action was warranted
API Endpoints
Method	Endpoint	Access	Purpose
POST	/api/v1/reports/products/{product_id}/	Customer	Report a Product
POST	/api/v1/reports/vendors/{vendor_id}/	Customer	Report a Vendor
GET	/api/v1/reports/mine/	Customer	View own reports
GET	/api/v1/reports/{report_id}/	Customer/Admin	View a report
GET	/api/v1/reports/	Admin	Moderation queue
POST	/api/v1/reports/{report_id}/under-review/	Admin	Mark under review
POST	/api/v1/reports/{report_id}/resolve/	Admin	Resolve a report
POST	/api/v1/reports/{report_id}/reject/	Admin	Reject a report
Architecture

ReportService owns report lifecycle transitions.

When a report is resolved:

Product reports delegate removal to ProductLifecycleService
Vendor reports delegate suspension to VendorSuspensionService

The reports app does not duplicate Product or Vendor moderation logic.

Testing

Run the app tests:

python manage.py test apps.reports
