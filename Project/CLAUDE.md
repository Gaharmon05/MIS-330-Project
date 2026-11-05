# CLAUDE.md — StyleHub Project Context

## What this project is
MIS 330 class project: a Python-based, **one-page** web app that demonstrates our understanding of:
- ERD relationships (PK/FK, one-to-many, many-to-many via junction tables)
- SQL (DDL, DML, joins, aggregates, constraints)
- How a database/SQL connects to application code (Python front end talking to MySQL)

## Which project
**Project #5: StyleHub — Clothing Retail and Alteration Management System**

Business scenario: StyleHub is a locally owned clothing store that sells men's, women's, and children's clothing, shoes, and fashion accessories. In addition to selling products, the store provides alteration services such as hemming, sleeve adjustments, and waist alterations. StyleHub wants a database system to manage its customers, products, sales, alteration orders, employees, and inventory.

## Source of truth (read these first)
- **Project Five requirements:** the `project requirements` folder. Always check Project Five's requirements before changing the schema or adding features. If anything here conflicts with that folder, the requirements folder wins.
- **Class reference material:** follow its structure/patterns when connecting the SQL to the Python front end.

## Known schema correction (alteration orders)
The AlterationOrder entity was originally modeled as an alteration of a *product order* (it pointed at a sale/order). Per the instructor's requirements it must instead model a **customer ordering an alteration to a piece of clothing**, independent of what they purchased.
- An alteration order belongs to a **customer** and an **employee (tailor)**, and describes the **garment** being altered plus the **alteration service** (hemming, sleeve adjustment, waist alteration, etc.).
- It must **not** require a foreign key to a sales order / order line.
- Everything else in the SQL is considered correct. Do not make other schema changes unless asked.

## Payment table (added at the user's request, 2026-11-05)
"Payment recording" is a required function, so a `Payment` table was added: one row per order
(`OrderID` UNIQUE), PaymentMethod ENUM, CardLastFour (cards only, enforced by a CHECK), Amount,
PaymentDate. db.place_order() inserts it in the same transaction as the order.
Updated diagrams live beside the originals: `Project Reference Materials/ERD v2.png` and
`Relational Schema v2.png` (originals kept unchanged).

## Folder layout
```
/Project Requirements        Project Five requirements (read-only reference)
/Project Reference Materials ERD, relational schema, business requirements doc
/Class Reference Material    class examples for SQL + Python connection patterns
/Files/DATABASE              01_schema.sql, 02_sample_data.sql, 03_reports.sql (MySQL)
/Files/WEBAPP
    /Python_Version          Flask server-rendered: app.py, ui.py, db.py, queries.py, templates/ (index.html + tabs/*.html)
    /JavaScript_Version      index.html + Client_Resources/Scripts/index.js (vanilla JS, fetch) + Styles/index.css
/Files/API                   api.py (Flask JSON API used by the JavaScript version) + db.py + queries.py
README.md                    how to run everything (paste into GitHub)
```
Kept in sync by hand -- change BOTH copies:
- db.py and queries.py: Python_Version/ and API/ are identical.
- index.css: Python_Version/ and JavaScript_Version/ are identical (shared design system).
(Files/WEBAPP/Client_Resources/ holds the team's original empty starter files; unused.)

## Two website versions (team will pick one)
1. **Python version** -- Flask renders each tab on the server (Jinja templates). One route "/" with ?tab=...
2. **JavaScript version** -- single-page vanilla JS (hash routing, fetch) calling the Python JSON API.

Both versions must expose the same features, use the same database and SQL, and look the same.
Design: navy sidebar, blue (#1d4ed8 / #2563eb) + teal (#0d9488 / #14b8a6) theme, Plus Jakarta Sans.

## Requirements for the app
- **One-page application** (single page, sections or tabs rather than separate pages).
- **Looks good, stays simple and functional.** Clean, readable layout; no need to be fancy, but not ugly.
- **Code must be easy to read** — students must be able to explain it. Clear names, short functions, comments on the SQL-to-Python connection points.
- Use parameterized queries (never build SQL with string concatenation).
- Keep SQL in one clearly labeled place so it's easy to point at during the presentation.

## Conventions
- Language: Python 3. Database: MySQL.
- Tables/columns: consistent naming, singular entity names, `<table>_id` primary keys.
- Prefer simple over clever. If there are two ways to do it, pick the one that's easier to explain in class.
- Don't add dependencies without a reason; list any in `requirements.txt`.

## Presentation notes
Be ready to explain: the ERD and each relationship, why each foreign key exists, one example join query, and the path of one request: browser → Python route → SQL query → MySQL → back to the page.
