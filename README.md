# Payroll Management System (PMS) - Prototype

CEN4021 RVC 1268 - Deliverable 5 (UX Design, Prototyping & Testing)
Team: Andry Valdes, Jeffrey Deliscar, Omar Miller, Jayvee Vergara

## Run
    php -S 127.0.0.1:8080 -t public public/router.php
Open http://127.0.0.1:8080 (PHP 8 + SQLite; DB is created and seeded on first request).

## Accounts
| User | Password | Role |
|---|---|---|
| padmin | Payroll123! | Payroll Administrator |
| fin1 | Finance123! | Finance (second approver) |
| sysadmin | SysAdmin123! | System Administrator |
| maria / james | Employee123! | Employee |

## Layout (maps to Deliverable 4 IDs)
- `public/router.php` - MW-1 REST layer; `public/index.html` - UI-1..UI-13
- `src/mw/` - MW-2 security, MW-3 authz, MW-4 validation, MW-5 data access, MW-7 audit, MW-8 documents
- `src/fc/` - FC-1..FC-10 functional components
- `tests/run_tests.py` - Playwright suite (52 equivalence-class + 22 functional cases); `tests/results.json`, `shots/`

## Branching
`main` is stable. Work happens on `feature/*` or `docs/*` branches and is merged with `--no-ff` via pull request.
