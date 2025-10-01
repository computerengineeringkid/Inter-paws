# Security & Tenancy Review

## Overview
This document captures the results of the Milestone 6 security hardening review. The primary goals were to ensure every database interaction is properly scoped to a clinic and that role-based access controls (RBAC) are enforced on all API endpoints.

## Methodology
* Audited each Flask blueprint and supporting service layer.
* Traced every database query to confirm a restrictive `clinic_id` filter is in place, either through direct query filters or via ORM relationships that are already scoped to a clinic entity.
* Verified RBAC rules for administrator-only onboarding endpoints and added explicit authorization guards to the scheduling APIs.
* Added validation for cross-entity references to guarantee all related objects belong to the same clinic before writing to the database.

## Endpoint Findings

| Endpoint | Access Control | Clinic Scoping | Notes |
| --- | --- | --- | --- |
| `POST /api/auth/register` | Public | Clinic assignment comes from payload; no cross-clinic reads. | Accounts stay scoped to the supplied clinic. |
| `POST /api/auth/login` | Public | Queries by unique email only. | No clinic data exposed. |
| `POST /api/clinic/onboarding` | Admins only | All created entities inherit `clinic_id` from the admin with explicit cleanup filters. | RBAC confirmed via `_current_admin`. |
| `GET /api/clinic/onboarding` | Admins only | Uses the authenticated admin's `clinic_id` to load related entities. | No cross-clinic exposure. |
| `POST /api/scheduler/find-slots` | Auth optional; if authenticated must belong to clinic. | Authenticated users are prevented from querying other clinics. | Falls back to clinic from JWT when omitted. |
| `POST /api/scheduler/book` | Authenticated users | Validates clinic membership and that referenced entities all belong to the clinic. | Blocks cross-clinic bookings and enforces referential integrity. |

## Additional Changes
* Updated booking logic to validate referenced entities (`pet`, `doctor`, `room`, `constraint`, and `owner`) against the target clinic before persisting appointments or feedback events.
* Added authorization guardrails for clinic-aware scheduling operations.

These safeguards ensure that data remains isolated per clinic and that only properly authorized users can interact with sensitive onboarding and scheduling functionality.
