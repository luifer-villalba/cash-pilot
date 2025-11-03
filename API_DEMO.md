# CashPilot API Demo

Complete walkthrough of CashPilot API endpoints with real, runnable cURL commands.

**Prerequisites:**
- CashPilot running: `make run`
- Server available at `http://localhost:8000`
- `jq` installed for pretty JSON output (optional: `brew install jq` or `apt-get install jq`)

---

## 1. Health Check

Verify the API is healthy and database is connected.

```bash
curl -s http://localhost:8000/health | jq .
```

**Expected response:**
```json
{
  "status": "ok",
  "uptime_seconds": 42,
  "checks": {
    "database": {
      "status": "ok",
      "response_time_ms": 3
    }
  }
}
```

---

## 2. Create a Business (Pharmacy Location)

Create your first pharmacy location.

```bash
BUSINESS_RESPONSE=$(curl -s -X POST http://localhost:8000/businesses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Farmacia Central",
    "address": "Av. Mariscal López 1234, Asunción",
    "phone": "+595 21 123-4567"
  }')

echo $BUSINESS_RESPONSE | jq .

# Extract business_id for next steps
BUSINESS_ID=$(echo $BUSINESS_RESPONSE | jq -r '.id')
echo "Business ID: $BUSINESS_ID"
```

**Expected response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Farmacia Central",
  "address": "Av. Mariscal López 1234, Asunción",
  "phone": "+595 21 123-4567",
  "is_active": true,
  "created_at": "2025-11-03T14:30:00",
  "updated_at": "2025-11-03T14:30:00"
}
```

---

## 3. Get Business Details

Retrieve the business you just created.

```bash
curl -s http://localhost:8000/businesses/$BUSINESS_ID | jq .
```

**Expected response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Farmacia Central",
  "address": "Av. Mariscal López 1234, Asunción",
  "phone": "+595 21 123-4567",
  "is_active": true,
  "created_at": "2025-11-03T14:30:00",
  "updated_at": "2025-11-03T14:30:00"
}
```

---

## 4. List All Businesses

Get all active businesses with pagination.

```bash
curl -s "http://localhost:8000/businesses?skip=0&limit=10&is_active=true" | jq .
```

**Expected response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Farmacia Central",
    "address": "Av. Mariscal López 1234, Asunción",
    "phone": "+595 21 123-4567",
    "is_active": true,
    "created_at": "2025-11-03T14:30:00",
    "updated_at": "2025-11-03T14:30:00"
  }
]
```

---

## 5. Open a Cash Session (Start Shift)

Open a new cash session for the pharmacy. This marks the beginning of a cashier's shift.

```bash
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/cash-sessions \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "'$BUSINESS_ID'",
    "cashier_name": "María López",
    "initial_cash": 500000.00,
    "shift_hours": "08:00-16:00"
  }')

echo $SESSION_RESPONSE | jq .

# Extract session_id for next steps
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.id')
echo "Session ID: $SESSION_ID"
```

**Expected response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "business_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "OPEN",
  "cashier_name": "María López",
  "shift_hours": "08:00-16:00",
  "opened_at": "2025-11-03T08:00:00",
  "closed_at": null,
  "initial_cash": "500000.00",
  "final_cash": null,
  "envelope_amount": "0.00",
  "credit_card_total": "0.00",
  "debit_card_total": "0.00",
  "bank_transfer_total": "0.00",
  "closing_ticket": null,
  "notes": null
}
```

---

## 6. Get Session Details

Check the current state of an open session.

```bash
curl -s http://localhost:8000/cash-sessions/$SESSION_ID | jq .
```

**Expected response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "business_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "OPEN",
  "cashier_name": "María López",
  "shift_hours": "08:00-16:00",
  "opened_at": "2025-11-03T08:00:00",
  "closed_at": null,
  "initial_cash": "500000.00",
  "final_cash": null,
  "envelope_amount": "0.00",
  "credit_card_total": "0.00",
  "debit_card_total": "0.00",
  "bank_transfer_total": "0.00",
  "closing_ticket": null,
  "notes": null
}
```

---

## 7. List Sessions for a Business

Get all sessions (open and closed) for a specific pharmacy.

```bash
curl -s "http://localhost:8000/cash-sessions?business_id=$BUSINESS_ID&skip=0&limit=50" | jq .
```

**Expected response:**
```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "business_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "OPEN",
    "cashier_name": "María López",
    "shift_hours": "08:00-16:00",
    "opened_at": "2025-11-03T08:00:00",
    "closed_at": null,
    "initial_cash": "500000.00",
    "final_cash": null,
    "envelope_amount": "0.00",
    "credit_card_total": "0.00",
    "debit_card_total": "0.00",
    "bank_transfer_total": "0.00",
    "closing_ticket": null,
    "notes": null
  }
]
```

---

## 8. Close a Cash Session (End Shift)

Close the session and record final cash amounts. This completes the shift reconciliation.

```bash
CLOSE_RESPONSE=$(curl -s -X PUT http://localhost:8000/cash-sessions/$SESSION_ID \
  -H "Content-Type: application/json" \
  -d '{
    "final_cash": 750000.00,
    "envelope_amount": 200000.00,
    "credit_card_total": 1500000.00,
    "debit_card_total": 800000.00,
    "bank_transfer_total": 500000.00,
    "closing_ticket": "T-20251103-001",
    "notes": "Normal shift, all reconciliation items verified"
  }')

echo $CLOSE_RESPONSE | jq .
```

**Expected response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "business_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "CLOSED",
  "cashier_name": "María López",
  "shift_hours": "08:00-16:00",
  "opened_at": "2025-11-03T08:00:00",
  "closed_at": "2025-11-03T16:15:00",
  "initial_cash": "500000.00",
  "final_cash": "750000.00",
  "envelope_amount": "200000.00",
  "credit_card_total": "1500000.00",
  "debit_card_total": "800000.00",
  "bank_transfer_total": "500000.00",
  "closing_ticket": "T-20251103-001",
  "notes": "Normal shift, all reconciliation items verified"
}
```

**Key calculation:**
- `cash_sales` = `(final_cash + envelope_amount) - initial_cash`
- `cash_sales` = `(750000 + 200000) - 500000` = **₲450,000**

---

## 9. Update Business Details

Modify business information (e.g., phone number, address).

```bash
curl -s -X PUT http://localhost:8000/businesses/$BUSINESS_ID \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+595 21 999-8888"
  }' | jq .
```

**Expected response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Farmacia Central",
  "address": "Av. Mariscal López 1234, Asunción",
  "phone": "+595 21 999-8888",
  "is_active": true,
  "created_at": "2025-11-03T14:30:00",
  "updated_at": "2025-11-03T14:35:00"
}
```

---

## 10. Soft-Delete a Business

Mark a business as inactive (soft delete).

```bash
curl -s -X DELETE http://localhost:8000/businesses/$BUSINESS_ID
```

**Expected response:** HTTP 204 (No Content)

Verify it's inactive:

```bash
curl -s http://localhost:8000/businesses/$BUSINESS_ID | jq '.is_active'
```

**Expected response:**
```json
false
```

---

## Error Scenarios

### Attempt to open duplicate session

Try opening a second session for the same business while one is already open:

```bash
curl -s -X POST http://localhost:8000/cash-sessions \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "'$BUSINESS_ID'",
    "cashier_name": "Juan Pérez",
    "initial_cash": 400000.00,
    "shift_hours": "16:00-23:00"
  }' | jq .
```

**Expected response (409 Conflict):**
```json
{
  "detail": "Session already open for this business"
}
```

### Get non-existent business

```bash
curl -s http://localhost:8000/businesses/00000000-0000-0000-0000-000000000000 | jq .
```

**Expected response (404 Not Found):**
```json
{
  "code": "NOT_FOUND",
  "message": "Business with ID 00000000-0000-0000-0000-000000000000 not found",
  "details": {
    "resource": "Business",
    "resource_id": "00000000-0000-0000-0000-000000000000"
  }
}
```

---

## Interactive API Documentation

Instead of cURL, you can explore the API interactively:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Both auto-generated from OpenAPI spec. Try the "Try it out" button in Swagger to test endpoints without cURL.

---

## Complete Workflow Script

Copy-paste this entire script to run the full demo:

```bash
#!/bin/bash
set -e

echo "🚀 CashPilot API Demo"
echo "===================="
echo ""

# 1. Health check
echo "1️⃣  Health check..."
curl -s http://localhost:8000/health | jq .
echo ""

# 2. Create business
echo "2️⃣  Creating business..."
BUSINESS=$(curl -s -X POST http://localhost:8000/businesses \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Farmacia Demo",
    "address": "Demo Street 123",
    "phone": "+595 21 000-0000"
  }')
BUSINESS_ID=$(echo $BUSINESS | jq -r '.id')
echo $BUSINESS | jq .
echo "Business ID: $BUSINESS_ID"
echo ""

# 3. Open session
echo "3️⃣  Opening cash session..."
SESSION=$(curl -s -X POST http://localhost:8000/cash-sessions \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "'$BUSINESS_ID'",
    "cashier_name": "Demo Cashier",
    "initial_cash": 500000.00,
    "shift_hours": "08:00-16:00"
  }')
SESSION_ID=$(echo $SESSION | jq -r '.id')
echo $SESSION | jq .
echo "Session ID: $SESSION_ID"
echo ""

# 4. Close session
echo "4️⃣  Closing cash session..."
curl -s -X PUT http://localhost:8000/cash-sessions/$SESSION_ID \
  -H "Content-Type: application/json" \
  -d '{
    "final_cash": 750000.00,
    "envelope_amount": 150000.00,
    "closing_ticket": "DEMO-001"
  }' | jq .
echo ""

echo "✅ Demo complete!"
```

Save as `demo.sh`, then run:

```bash
chmod +x demo.sh
./demo.sh
```

---

## Testing with Postman

Prefer a GUI? Import this into Postman:

1. Open Postman
2. Click **Import** → **Raw text**
3. Paste the OpenAPI spec from: `http://localhost:8000/openapi.json`
4. All endpoints auto-generate with documentation

---

**Questions?** Check the main [README.md](README.md) for architecture details or run `make test` to verify everything works.