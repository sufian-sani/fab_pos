# POS Portal API Reference

## Base URL
```
http://localhost:8000/api
```

---

## Authentication Endpoints

### POST `/users/pos_login/`
**Purpose:** POS Terminal Login  
**Access:** Public (AllowAny)  
**Role:** Cashier, Branch Manager

**Request Body:**
```json
{
    "email": "cashier@restaurant.com",
    "password": "password123",
    "device_id": "POS-001"  // Optional
}
```

**Success Response (200):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 5,
        "email": "cashier@restaurant.com",
        "username": "cashier1",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "555-1234",
        "role": "cashier",
        "branch": {
            "id": 1,
            "name": "Main Branch",
            "code": "MB001",
            "city": "New York"
        },
        "tenant": {
            "id": 1,
            "name": "Burger Palace"
        }
    },
    "pos_devices": [
        {
            "id": 1,
            "name": "Counter 1",
            "device_id": "POS-001",
            "device_type": "tablet",
            "branch_name": "Main Branch",
            "status": "online",
            "is_online": true
        }
    ],
    "device_count": 1,
    "message": "Successfully authenticated. 1 POS device(s) available."
}
```

**Error Responses:**

| Status | Scenario | Response |
|--------|----------|----------|
| 401 | Invalid credentials | `{"error": "Invalid credentials"}` |
| 403 | Account disabled | `{"error": "Account is disabled"}` |
| 403 | User is platform owner/tenant admin | `{"error": "This user cannot access POS portal. Use admin interface instead."}` |
| 403 | No POS devices assigned | `{"error": "No POS devices assigned to this user"}` |
| 403 | No active POS devices | `{"error": "No active POS devices available for this user"}` |

---

## POS Portal Menu Endpoints

### Base URL
```
/api/pos/portal/
```

All endpoints require JWT authentication:
```
Authorization: Bearer <ACCESS_TOKEN>
```

---

### GET `/api/pos/portal/`
**Purpose:** Get complete menu (categories with products)  
**Most Used Endpoint for POS Terminals**  
**Role:** Cashier, Branch Manager  
**Response:** 200 OK

**Query Parameters:** None

**Response Body:**
```json
{
    "devices_count": 2,
    "category_count": 3,
    "categories": [
        {
            "category": {
                "id": 1,
                "name": "Appetizers",
                "display_order": 1,
                "is_active": true,
                "product_count": 5
            },
            "products": [
                {
                    "id": 101,
                    "name": "Samosas",
                    "sku": "APP-001",
                    "price": "4.99",
                    "category": "Appetizers",
                    "image": "/media/products/samosa.jpg",
                    "is_available": true
                },
                {
                    "id": 102,
                    "name": "Spring Rolls",
                    "sku": "APP-002",
                    "price": "5.99",
                    "category": "Appetizers",
                    "image": "/media/products/spring_rolls.jpg",
                    "is_available": true
                }
            ],
            "product_count": 2
        },
        {
            "category": {
                "id": 2,
                "name": "Main Course",
                "display_order": 2,
                "is_active": true,
                "product_count": 8
            },
            "products": [
                {
                    "id": 201,
                    "name": "Butter Chicken",
                    "sku": "MC-001",
                    "price": "14.99",
                    "category": "Main Course",
                    "image": "/media/products/butter_chicken.jpg",
                    "is_available": true
                }
            ],
            "product_count": 1
        }
    ]
}
```

---

### GET `/api/pos/portal/categories/`
**Purpose:** Get categories only  
**Role:** Cashier, Branch Manager  
**Response:** 200 OK

**Query Parameters:** None

**Response Body:**
```json
{
    "count": 3,
    "categories": [
        {
            "id": 1,
            "name": "Appetizers",
            "display_order": 1,
            "is_active": true,
            "product_count": 5
        },
        {
            "id": 2,
            "name": "Main Course",
            "display_order": 2,
            "is_active": true,
            "product_count": 8
        },
        {
            "id": 3,
            "name": "Desserts",
            "display_order": 3,
            "is_active": true,
            "product_count": 4
        }
    ]
}
```

---

### GET `/api/pos/portal/products/`
**Purpose:** Get products (with optional filtering)  
**Role:** Cashier, Branch Manager  
**Response:** 200 OK

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category_id` | int | No | Filter by category ID |
| `device_id` | int | No | Filter by POS device (if user has multiple) |

**Examples:**
```
/pos/portal/menu/products/
/pos/portal/menu/products/?category_id=1
/pos/portal/menu/products/?category_id=1&device_id=2
```

**Response Body:**
```json
{
    "count": 8,
    "products": [
        {
            "id": 201,
            "name": "Butter Chicken",
            "sku": "MC-001",
            "price": "14.99",
            "category": "Main Course",
            "image": "/media/products/butter_chicken.jpg",
            "is_available": true
        },
        {
            "id": 202,
            "name": "Tikka Masala",
            "sku": "MC-002",
            "price": "15.99",
            "category": "Main Course",
            "image": "/media/products/tikka_masala.jpg",
            "is_available": true
        }
    ]
}
```

---

### GET `/api/pos/portal/devices/`
**Purpose:** Get user's accessible POS devices  
**Role:** Cashier, Branch Manager  
**Response:** 200 OK

**Query Parameters:** None

**Response Body:**
```json
{
    "count": 2,
    "devices": [
        {
            "id": 1,
            "name": "Counter 1",
            "device_id": "POS-001",
            "device_type": "tablet",
            "branch_name": "Main Branch",
            "status": "online",
            "is_online": true
        },
        {
            "id": 2,
            "name": "Counter 2",
            "device_id": "POS-002",
            "device_type": "desktop",
            "branch_name": "Main Branch",
            "status": "online",
            "is_online": true
        }
    ]
}
```

---

### GET `/api/pos/portal/search/`
**Purpose:** Search products by name or SKU  
**Role:** Cashier, Branch Manager  
**Response:** 200 OK

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (minimum 2 characters) |

**Examples:**
```
/pos/portal/menu/search/?q=butter
/pos/portal/menu/search/?q=APP
/pos/portal/menu/search/?q=chai
```

**Response Body:**
```json
{
    "query": "butter",
    "count": 2,
    "products": [
        {
            "id": 201,
            "name": "Butter Chicken",
            "sku": "MC-001",
            "price": "14.99",
            "category": "Main Course",
            "image": "/media/products/butter_chicken.jpg",
            "is_available": true
        },
        {
            "id": 301,
            "name": "Butter Naan",
            "sku": "BREAD-001",
            "price": "3.99",
            "category": "Bread",
            "image": "/media/products/butter_naan.jpg",
            "is_available": true
        }
    ]
}
```

**Error Response (400):**
```json
{
    "query": "ab",
    "count": 0,
    "products": [],
    "message": "Query must be at least 2 characters"
}
```

---

## Error Handling

### Common HTTP Status Codes

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | Success | Data returned successfully |
| 400 | Bad Request | Invalid query parameters |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | User doesn't have permission |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Internal server error |

### Error Response Format

```json
{
    "error": "Error message describing what went wrong",
    "detail": "Additional details if available"
}
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Invalid credentials" | Email or password wrong | Verify credentials |
| "Account is disabled" | User.is_active = False | Admin must reactivate |
| "No POS devices assigned" | Cashier has no devices | Admin must assign devices |
| "No active POS devices available" | All devices offline | Check device status |
| "Permission denied" | Invalid JWT or expired | Re-login with pos_login |
| "Query must be at least 2 characters" | Search query too short | Use 2+ characters |

---

## HTTP Headers

### Request Headers (All Protected Endpoints)
```
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json
```

### Response Headers
```
Content-Type: application/json
X-Content-Type-Options: nosniff
```

---

## Rate Limiting (Optional Future Enhancement)

Currently not implemented, but recommended for production:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704086400
```

---

## CORS Configuration (If Applicable)

```
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## Pagination (Future Enhancement)

Current implementation returns all results. Future versions may support:

```
/pos/portal/menu/products/?page=1&page_size=20
```

Response would include:
```json
{
    "count": 100,
    "next": ".../?page=2",
    "previous": null,
    "results": [...]
}
```

---

## Filtering Examples

### Get Products by Category
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost:8000/api/pos/portal/products/?category_id=1"
```

### Search for Products
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost:8000/api/pos/portal/search/?q=butter"
```

### Get All Devices
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost:8000/api/pos/portal/devices/"
```

### Get Complete Menu
```bash
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost:8000/api/pos/portal/"
```

---

## JavaScript/TypeScript Example

```javascript
// 1. Login
async function posLogin(email, password) {
    const response = await fetch('/api/users/pos_login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    return data;
}

// 2. Get Menu
async function getMenu() {
    const token = localStorage.getItem('access_token');
    const response = await fetch('/api/pos/portal/', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    return response.json();
}

// 3. Search Products
async function searchProducts(query) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(
        `/api/pos/portal/search/?q=${encodeURIComponent(query)}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
    );
    
    return response.json();
}

// Usage
posLogin('john@restaurant.com', 'password').then(() => {
    getMenu().then(menu => {
        console.log('Menu:', menu);
        // Display menu on POS terminal
    });
});
```

---

## Python Example (Requests Library)

```python
import requests
import json

# Configuration
API_BASE = 'http://localhost:8000/api'

# 1. Login
response = requests.post(
    f'{API_BASE}/users/pos_login/',
    json={
        'email': 'cashier@restaurant.com',
        'password': 'password123'
    }
)

auth_data = response.json()
access_token = auth_data['access']

# 2. Get Menu
headers = {'Authorization': f'Bearer {access_token}'}
response = requests.get(
    f'{API_BASE}/pos/portal/menu/menu/',
    headers=headers
)

menu = response.json()
print(json.dumps(menu, indent=2))

# 3. Search Products
response = requests.get(
    f'{API_BASE}/pos/portal/menu/search/',
    params={'q': 'butter'},
    headers=headers
)

products = response.json()
print(json.dumps(products, indent=2))
```

