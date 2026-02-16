# Wallet Service API (Django + DRF + Celery)

A wallet backend built with **Django REST Framework** and **Celery**. It supports:

- Creating wallets
- Retrieving wallet balances
- Depositing funds (immediate)
- Scheduling withdrawals for a future time (processed asynchronously)
- Concurrency-safe balance updates using DB row locks
- Reliable withdrawal execution with retries + refund-on-final-failure

---

## What’s implemented

### 1) Core models

#### Wallet
- `uuid` unique identifier
- `balance` stored as an integer (`BigIntegerField`)
- `deposit()` uses `transaction.atomic()` + `select_for_update()` for safe concurrent updates

#### Transaction
Represents wallet activity.

- Types: `DEPOSIT`, `WITHDRAW`
- Statuses: `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`
- Withdrawal-specific fields:
  - `execute_at` (scheduled execution timestamp)
  - `retry_count`, `is_dead` (dead-letter style handling)
  - `idempotency_key` (safe third-party retries)

---

### 2) REST API endpoints (DRF)

Endpoints implemented:

- `POST /` — create wallet
- `GET /<uuid:uuid>/` — retrieve wallet
- `POST /deposit/` — deposit immediately (atomic + transaction recorded)
- `POST /withdraw/` — schedule a withdrawal for a future `execute_at`

---

### 3) Scheduled withdrawal processing (Celery)

A Celery task processes withdrawals when they become due:

- Finds due withdrawals (`execute_at <= now`)
- Locks the transaction row and wallet row to prevent duplicate processing
- Validates wallet balance at execution time
- Reserves funds (deducts balance once) and moves status to `PROCESSING`
- Calls the third-party payout service (with `idempotency_key`)
- Marks `SUCCESS` on success
- Retries on transient errors
- On max retries reached: marks `FAILED`, sets `is_dead=True`, and refunds reserved funds

Celery Beat triggers the processor periodically.

---

### 4) Third-party request utility

A helper function exists for making the third-party/bank request. It is used during withdrawal execution to perform the payout call.

---

## Tech Stack

- Python / Django
- Django REST Framework (DRF)
- Celery (worker + beat)
- Redis (Celery broker)
- Postgres (database)
- Docker Compose (local environment)

---

## API Reference

> Routes are defined in the wallets app.

### Create wallet
`POST /`

**Response (example)**
```json
{
  "uuid": "9b07d7f2-1b0f-4bd0-9e63-7b84e7d30c34",
  "balance": 0
}
```

---

### Retrieve wallet
`GET /<uuid:uuid>/`

**Response (example)**
```json
{
  "uuid": "9b07d7f2-1b0f-4bd0-9e63-7b84e7d30c34",
  "balance": 1000
}
```

---

### Deposit
`POST /deposit/`

Deposits funds immediately and records a successful `DEPOSIT` transaction.

**Request**
```json
{
  "wallet_id": "9b07d7f2-1b0f-4bd0-9e63-7b84e7d30c34",
  "amount": 1000
}
```

**Response**
```json
{
  "balance": 1000
}
```

Validation:
- `wallet_id` required
- `amount` required and must be `> 0`

---

### Schedule withdrawal
`POST /withdraw/`

Schedules a withdrawal for future execution by creating a `WITHDRAW` transaction in `PENDING` status.

**Request**
```json
{
  "wallet_id": "9b07d7f2-1b0f-4bd0-9e63-7b84e7d30c34",
  "amount": 250,
  "execute_at": "2026-02-16T16:10:42Z"
}
```

**Response**
```json
{
  "transaction_id": "c7c3e48a-8ed2-41d4-8ff2-9e0d8d3a0b0a"
}
```

Validation:
- `wallet_id`, `amount`, `execute_at` required
- `execute_at` must be a valid ISO-8601 datetime (UTC recommended)
- `execute_at` must be in the future

Behavior note:
- Balance is validated at **execution time**, not at scheduling time.

---

## Withdrawal Execution Flow

Withdrawals are executed asynchronously and validated at execution time:

1. **Discovery**: find withdrawals that are due (`execute_at <= now`) and not dead.
2. **Locking**: lock the transaction row and wallet row to ensure only one worker processes it.
3. **Validation**:
   - If wallet balance is insufficient → mark withdrawal `FAILED` (and/or dead depending on retry rules).
4. **Reservation**:
   - If valid and still `PENDING`, deduct the amount and mark as `PROCESSING`.
5. **Third-party call**:
   - Perform payout request outside the DB transaction using an idempotency key.
6. **Finalize**:
   - On success → `SUCCESS`
   - On failure → retry
   - On max retries → refund reserved funds, mark `FAILED`, set `is_dead=True`

---

## Running Locally (Docker)

### Prerequisites
- Docker
- Docker Compose

### Start the stack
```bash
docker compose up --build
```

This starts:
- Django API server
- Postgres DB
- Redis broker
- Celery worker
- Celery beat scheduler

---

## Configuration Notes

Typical services (as per `docker-compose.yml`):
- `wallet` (Django app)
- `db` (Postgres)
- `redis` (broker)
- `worker` (Celery worker)
- `beat` (Celery beat)

---

