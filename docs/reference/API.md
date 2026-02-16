# API Reference — CashPilot

> 📚 Reference Document  
> This document provides API endpoint documentation for developers.  
> For architecture decisions, see [ARCHITECTURE.md](../architecture/ARCHITECTURE.md).

## Purpose

Document the HTTP API endpoints available in CashPilot for both frontend routes (HTML) and JSON API endpoints. This serves as a reference for developers implementing features or debugging issues.

---

## Authentication

All API endpoints require authentication via session-based auth (cookies). Users must log in via `/login` before accessing protected endpoints.

**Session Expiry:**
- Admins: 2 hours
- Cashiers: 10 hours

---

## API Endpoints

### Authentication

#### `POST /login`
**Purpose:** Authenticate user and create session  
**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Response:** Redirects to `/` on success, returns error on failure  
**RBAC:** Public (unauthenticated)

#### `POST /logout`
**Purpose:** Destroy session and log out user  
**Response:** Redirects to `/login`  
**RBAC:** Authenticated users only

---

### Cash Sessions

#### `GET /api/sessions`
**Purpose:** List cash sessions with filters  
**Query Parameters:**
- `business_id` (optional): Filter by business UUID
- `cashier_id` (optional): Filter by cashier UUID
- `status` (optional): Filter by status (open/closed)
- `start_date` (optional): Filter by start date (YYYY-MM-DD)
- `end_date` (optional): Filter by end date (YYYY-MM-DD)
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20)

**Response:**
```json
{
  "sessions": [
    {
      "id": "uuid",
      "business_id": "uuid",
      "cashier_id": "uuid",
      "status": "open",
      "opened_at": "2026-02-15T10:00:00-04:00",
      "initial_cash": "500000.00",
      "final_cash": null,
      "is_deleted": false
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```
**RBAC:**
- Admin: View all sessions across all businesses
- Cashier: View only own sessions in assigned businesses

#### `POST /api/sessions`
**Purpose:** Create a new cash session  
**Request Body:**
```json
{
  "business_id": "uuid",
  "initial_cash": "500000.00",
  "expenses": "0.00",
  "expense_items": [
    {
      "description": "Office supplies",
      "amount": "50000.00"
    }
  ]
}
```
**Response:** Returns created session object  
**RBAC:**
- Admin: Can create for any business
- Cashier: Can create only for assigned businesses

#### `PUT /api/sessions/{id}/close`
**Purpose:** Close an open cash session with reconciliation  
**Request Body:**
```json
{
  "final_cash": "450000.00",
  "card_sales": "200000.00",
  "credit_sales": "150000.00",
  "bank_transfers": "100000.00",
  "envelope": "0.00",
  "transfer_items": [
    {
      "description": "Wire transfer",
      "amount": "100000.00"
    }
  ]
}
```
**Response:** Returns updated session with calculated totals  
**RBAC:**
- Admin: Can close any session
- Cashier: Can close only own sessions

#### `GET /api/sessions/{id}`
**Purpose:** Get details of a specific session  
**Response:** Returns full session object with related data  
**RBAC:**
- Admin: Can view any session
- Cashier: Can view only own sessions in assigned businesses

#### `PUT /api/sessions/{id}`
**Purpose:** Edit a cash session (within time window or admin)  
**Request Body:** Same as create/close endpoints (fields vary by status)  
**Response:** Returns updated session  
**RBAC:**
- Admin: Can edit any session anytime
- Cashier: Can edit own open sessions; closed sessions within 12 hours only

#### `DELETE /api/sessions/{id}`
**Purpose:** Soft delete a cash session  
**Response:** Success message  
**RBAC:** Admin only

#### `POST /api/sessions/{id}/restore`
**Purpose:** Restore a soft-deleted session  
**Response:** Returns restored session  
**RBAC:** Admin only

---

### Businesses

#### `GET /api/businesses`
**Purpose:** List all businesses  
**Response:**
```json
{
  "businesses": [
    {
      "id": "uuid",
      "name": "Store Name",
      "address": "Address",
      "phone": "Phone",
      "is_active": true
    }
  ]
}
```
**RBAC:**
- Admin: View all businesses
- Cashier: View only assigned businesses

#### `POST /api/businesses`
**Purpose:** Create a new business  
**Request Body:**
```json
{
  "name": "New Store",
  "address": "123 Main St",
  "phone": "+595 21 123 4567"
}
```
**Response:** Returns created business  
**RBAC:** Admin only

#### `PUT /api/businesses/{id}`
**Purpose:** Update business details  
**Response:** Returns updated business  
**RBAC:** Admin only

#### `DELETE /api/businesses/{id}`
**Purpose:** Soft delete (deactivate) a business  
**Response:** Success message  
**RBAC:** Admin only

---

### Users

#### `GET /api/users`
**Purpose:** List all users  
**Response:**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "role": "CASHIER",
      "is_active": true,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```
**RBAC:** Admin only

#### `POST /api/users`
**Purpose:** Create a new user (auto-generates password)  
**Request Body:**
```json
{
  "email": "newuser@example.com",
  "role": "CASHIER",
  "first_name": "John",
  "last_name": "Doe"
}
```
**Response:** Returns created user with auto-generated password (shown once)  
**RBAC:** Admin only

#### `PUT /api/users/{id}`
**Purpose:** Update user details  
**Request Body:** Fields to update (email, role, is_active, etc.)  
**Response:** Returns updated user  
**RBAC:** Admin only

#### `POST /api/users/{id}/reset-password`
**Purpose:** Reset user password (generates new random password)  
**Response:** Returns new password (shown once)  
**RBAC:** Admin only

#### `POST /api/users/{user_id}/businesses/{business_id}`
**Purpose:** Assign a user to a business  
**Response:** Success message  
**RBAC:** Admin only

#### `DELETE /api/users/{user_id}/businesses/{business_id}`
**Purpose:** Remove user's access to a business  
**Response:** Success message  
**RBAC:** Admin only

---

### Reports

#### `GET /api/reports/weekly-trend`
**Purpose:** Get weekly revenue trend report  
**Query Parameters:**
- `business_id` (optional): Filter by business
- `week_offset` (optional): Weeks back from current (0 = current week, 1 = last week, etc.)

**Response:**
```json
{
  "current_week": {
    "start_date": "2026-02-10",
    "end_date": "2026-02-16",
    "daily_totals": [
      {
        "date": "2026-02-10",
        "total_sales": "1500000.00",
        "session_count": 3
      }
    ],
    "week_total": "9500000.00"
  },
  "comparison_weeks": [
    {
      "week_label": "1 week ago",
      "week_total": "8700000.00"
    }
  ]
}
```
**RBAC:** Admin only

#### `GET /api/reports/weekly-trend/pdf`
**Purpose:** Export weekly trend report as PDF  
**Query Parameters:** Same as weekly-trend endpoint  
**Response:** PDF file download  
**RBAC:** Admin only

#### `GET /api/reports/daily-reconciliation`
**Purpose:** View daily reconciliation comparison (system vs manual entry)  
**Query Parameters:**
- `business_id`: Required business UUID
- `date`: Required date (YYYY-MM-DD)

**Response:**
```json
{
  "business": {
    "id": "uuid",
    "name": "Store Name"
  },
  "date": "2026-02-15",
  "system_totals": {
    "cash_sales": "1000000.00",
    "card_sales": "500000.00",
    "total_sales": "1500000.00",
    "session_count": 5
  },
  "manual_entry": {
    "cash_sales": "1000000.00",
    "card_sales": "500000.00",
    "total_sales": "1500000.00"
  },
  "discrepancy": {
    "cash_sales": "0.00",
    "card_sales": "0.00",
    "total_sales": "0.00"
  }
}
```
**RBAC:** Admin only

---

### Audit

#### `POST /api/sessions/{id}/flag`
**Purpose:** Flag a session for review  
**Request Body:**
```json
{
  "reason": "Large discrepancy detected"
}
```
**Response:** Success message  
**RBAC:** Admin only

#### `DELETE /api/sessions/{id}/flag`
**Purpose:** Remove flag from a session  
**Response:** Success message  
**RBAC:** Admin only

#### `GET /api/sessions/{id}/audit`
**Purpose:** View audit log for a session  
**Response:**
```json
{
  "audit_logs": [
    {
      "id": "uuid",
      "timestamp": "2026-02-15T14:30:00-04:00",
      "user_email": "admin@example.com",
      "action": "EDIT",
      "old_value": "500000.00",
      "new_value": "550000.00",
      "field": "final_cash",
      "reason": "Correction after recount"
    }
  ]
}
```
**RBAC:** Admin only

---

## Frontend Routes (HTML)

These routes return HTML pages (Jinja2 templates) for the web interface.

### Public Routes

- `GET /login` - Login page

### Dashboard & Navigation

- `GET /` - Dashboard (session list with filters)
- `GET /settings` - User settings page

### Cash Session Management

- `GET /sessions/new` - New session form
- `GET /sessions/{id}` - Session detail view
- `GET /sessions/{id}/edit` - Edit session form
- `GET /sessions/{id}/close` - Close session form

### Business Management (Admin Only)

- `GET /businesses` - Business list page
- `GET /businesses/new` - New business form
- `GET /businesses/{id}/edit` - Edit business form

### User Management (Admin Only)

- `GET /admin/users` - User list page
- `GET /admin/users/new` - New user form
- `GET /admin/users/{id}/edit` - Edit user form
- `GET /admin/users/{id}/assign-businesses` - Assign businesses to user

### Reports (Admin Only)

- `GET /reports/weekly-trend` - Weekly trend report page
- `GET /reports/business-stats` - Business statistics page
- `GET /admin/reconciliation/{business_id}/{date}` - Daily reconciliation comparison

---

## Error Responses

All API endpoints return standard error responses:

```json
{
  "error": "Error message",
  "detail": "Detailed error information (if available)"
}
```

**HTTP Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (not logged in)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Unprocessable Entity (validation error)
- `500` - Internal Server Error

---

## Data Formats

### Dates
All dates use ISO 8601 format with timezone: `YYYY-MM-DDTHH:MM:SS±HH:MM`

**Example:** `2026-02-15T14:30:00-04:00` (Paraguay timezone UTC-4)

### Currency
All monetary values are strings representing Guaraníes with 2 decimal places.

**Example:** `"1500000.00"` = ₲1.500.000

### UUIDs
All entity IDs use UUID v4 format.

**Example:** `"a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"`

---

## Rate Limiting

Currently no rate limiting is enforced. This may be added in future releases.

---

## Versioning

The API is currently unversioned. Breaking changes will be documented in release notes.

---

## Related Documentation

- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) - System architecture
- [CODE_MAP.md](../architecture/CODE_MAP.md) - Code organization
- [ACCEPTANCE_CRITERIA.md](../product/ACCEPTANCE_CRITERIA.md) - Feature requirements
