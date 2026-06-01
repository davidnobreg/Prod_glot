# Arquitetura GLOT

## Tipo

Monólito Modular

## Backend

Django

## Banco

PostgreSQL

## Cache

Redis

## Filas

Celery + RabbitMQ

---

## Apps

accounts
clientes
empreendimentos
vendas
documentos
cobranca
dashboard

---

## Fluxo

Usuário
 ↓
View
 ↓
Service
 ↓
Model
 ↓
Banco