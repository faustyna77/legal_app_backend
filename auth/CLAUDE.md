# Auth Service — Architektura i przepływ rejestracji/logowania

## Dwie oddzielne bazy danych

Projekt używa **dwóch niezależnych baz PostgreSQL**:

| Baza | Port | Przeznaczenie |
|------|------|---------------|
| `judgments` (backend) | 5432 (domyślny) | Orzeczenia sądowe, embeddingi, wyszukiwanie |
| `users` (auth) | 5433 | Użytkownicy, tokeny, foldery, historia |

Każdy serwis łączy się tylko ze swoją bazą — nie ma żadnego wspólnego połączenia między nimi. Komunikacja odbywa się przez JWT (token niesie dane użytkownika, więc backend nie musi pytać bazy użytkowników).

---

## Serwis Auth (`auth/`)

### Połączenie z bazą użytkowników

`auth/database.py` — buduje URL na podstawie zmiennych środowiskowych:

```
DB_USERS_HOST=localhost
DB_USERS_PORT=5433        ← inny port niż baza orzeczeń
DB_USERS_USER=postgres
DB_USERS_PASSWORD=postgres
DB_USERS_NAME=users
```

Każde zapytanie otwiera nowe połączenie przez `asyncpg.connect()` i zamyka je w bloku `finally`. Nie ma connection poola w auth serwisie.

### Schemat bazy użytkowników (`auth/schema.sql`)

```
users               — konta: id, email, password_hash, name, is_active
refresh_tokens      — przechowywanie refresh tokenów z datą wygaśnięcia
user_folders        — foldery zapisanych orzeczeń
user_folder_judgments — orzeczenia w folderach (judgment_id to ID z bazy orzeczeń!)
user_search_history — historia wyszukiwań
user_chat_history   — historia czatu z orzeczeniami
```

Kluczowe: `user_folder_judgments.judgment_id` oraz `user_chat_history.judgment_id` to **referencje do bazy orzeczeń**, ale bez klucza obcego (różne bazy!) — integralność jest po stronie logiki aplikacji.

---

## Rejestracja (`POST /auth/register`)

Plik: `auth/routers/auth.py`, linia 23

**Przepływ krok po kroku:**

1. Walidacja danych wejściowych przez Pydantic (`UserRegister`: email, password, name opcjonalny)
2. Sprawdzenie czy email już istnieje w tabeli `users`
3. Hashowanie hasła algorytmem **PBKDF2-SHA256** (via `passlib`) — `auth/utils/security.py`
4. `INSERT` do tabeli `users` → zwraca `id` i `email`
5. Generowanie **access tokena JWT** (ważny 30 min) z payload: `{user_id, email, type: "access"}`
6. Generowanie **refresh tokena JWT** (ważny 7 dni) z payload: `{user_id, type: "refresh"}`
7. `INSERT` refresh tokena do tabeli `refresh_tokens` z datą wygaśnięcia
8. Zwrot obu tokenów jako `TokenResponse`

---

## Logowanie (`POST /auth/login`)

Plik: `auth/routers/auth.py`, linia 57

**Przepływ krok po kroku:**

1. Walidacja danych (`UserLogin`: email, password)
2. Pobranie użytkownika z bazy po emailu (SELECT z `password_hash` i `is_active`)
3. Weryfikacja hasła przez `passlib.verify()` — porównuje plain z hashem
4. Sprawdzenie flagi `is_active` (konto może być zablokowane)
5. Generowanie nowego access i refresh tokena (tak samo jak przy rejestracji)
6. Zapis refresh tokena do bazy
7. Zwrot tokenów

---

## Tokeny JWT — szczegóły

Plik: `auth/utils/jwt.py`

- Biblioteka: `python-jose`
- Algorytm: HS256 (symetryczny, jeden `SECRET_KEY`)
- Access token payload: `{user_id, email, exp, type: "access"}`
- Refresh token payload: `{user_id, exp, type: "refresh"}`

**Weryfikacja tożsamości** w chronionych endpointach (`get_current_user`):
```python
authorization: str = Header(...)  # "Bearer <token>"
token = authorization.split(" ")[1]
payload = verify_token(token)     # decode JWT
# sprawdza: czy payload istnieje i czy type == "access"
```

---

## Odświeżanie tokena (`POST /auth/refresh`)

Linia 87 w `auth/routers/auth.py`

**Rotacja tokenów (rotation pattern):**
1. Weryfikuj refresh token (JWT + sprawdź w bazie + sprawdź `expires_at`)
2. Usuń stary refresh token z bazy (`DELETE`)
3. Wygeneruj nowy access + refresh token
4. Zapisz nowy refresh token do bazy
5. Zwróć nową parę tokenów

Refresh token jest **jednorazowy** — po użyciu jest niszczony i tworzony nowy.

---

## Backend serwis (`backend/`) — integracja

### Połączenie z bazą orzeczeń

`backend/app/db.py` — łączy się z bazą orzeczeń przez zmienną `DATABASE_URL` (port 5432).

### Opcjonalna autoryzacja JWT

`backend/app/dependencies.py` — backend nie ma własnego systemu logowania. Zamiast tego:

```python
async def get_optional_user(authorization: str = Header(None)) -> dict | None:
    # Dekoduje JWT używając tego samego SECRET_KEY co auth serwis
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    # Zwraca None jeśli brak tokena — endpoint działa dla niezalogowanych
```

Backend używa **tego samego `SECRET_KEY`** co serwis auth — dzięki temu może samodzielnie weryfikować tokeny bez zapytania do auth serwisu. Token niesie `user_id` i `email` w payload, więc backend wie kto wysyła zapytanie.

### Wewnętrzna autoryzacja między serwisami

Backend dodatkowo chroni endpointy nagłówkiem `x-internal-key` (stały klucz API), który używa frontend lub inne serwisy wewnętrzne.

---

## Diagram przepływu

```
Frontend
  |
  |-- POST /auth/register ──> Auth Serwis ──> Baza users (port 5433)
  |                              |
  |<─── {access_token, refresh_token} ──────────────────────────────
  |
  |-- GET /search?q=... ─────> Backend Serwis ──> Baza orzeczeń (port 5432)
       Authorization: Bearer <access_token>
       x-internal-key: <klucz>pobranich z nsa 
              |
              | weryfikuje JWT lokalnie (ten sam SECRET_KEY)
              | NIE odpytuje auth serwisu
```

---

## Kluczowe zależności (auth serwis)

```
fastapi, uvicorn       — serwer HTTP
asyncpg                — async połączenie z PostgreSQL
python-jose[cryptography] — JWT
passlib[bcrypt]        — hashowanie haseł (używa pbkdf2_sha256)
pydantic[email]        — walidacja danych wejściowych
python-dotenv          — zmienne środowiskowe
```