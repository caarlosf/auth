# Notas — Peticiones CURL

## REGISTRO
```
curl -X 'POST' \
  'http://127.0.0.1:8000/auth/register' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "user@example.com",
  "password": "string",
  "password2": "string"
}'
```



## LOGIN
```
curl -X 'POST' \
  'http://127.0.0.1:8000/auth/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "user@example.com",
  "password": "string"
}'
```



## PASS_REQUEST
```
curl -X 'POST' \
  'http://127.0.0.1:8000/auth/password-reset/request' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "user@example.com"
}'
```



## PASS_CONFIRM
```
curl -X 'POST' \
  'http://127.0.0.1:8000/auth/password-reset/confirm' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "token": "string",
  "password": "string",
  "password2": "string"
}'
```





