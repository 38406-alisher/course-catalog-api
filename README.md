## Breakage Journal (Lab 5)

### Breakage 1: Removed CORS completely
- What I did: Commented out `app.add_middleware(CORSMiddleware, ...)` in `main.py`.
- Console: Access to fetch at 'http://localhost:8000/courses' has been blocked by CORS policy.
- Network: `/courses` request red (CORS error), POST preflight gets 405 Method Not Allowed.
- Cause: FastAPI did not return Access-Control-Allow-Origin headers.
- How I found it: Algorithm step 2 & 4.

### Breakage 2: Trailing slash in allow_origins
- What I did: Set `allow_origins=["http://localhost:3000/"]`.
- Console: Response to preflight request doesn't pass access control check.
- Network: OPTIONS request returned status 400.
- Cause: Origin matching requires exact scheme + host + port without trailing slash.
- How I found it: Algorithm step 3.

### Breakage 3: Removed allow_methods
- What I did: Removed `allow_methods=["*"]`.
- Console: Response to preflight request doesn't pass access control check: It does not have HTTP ok status.
- Network: OPTIONS preflight returned 400 (Disallowed CORS method).
- Cause: Only GET is allowed by default; POST was rejected during preflight.
- How I found it: Algorithm step 4.

### Breakage 4: Origin mismatch (127.0.0.1 vs localhost)
- What I did: Accessed frontend via `http://127.0.0.1:3000/filter`.
- Console: Blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present.
- Network: Request red (CORS error).
- Cause: Browser treats `127.0.0.1` and `localhost` as distinct origins.
- How I found it: Algorithm step 3.

### Breakage 5: Python KeyError in backend
- What I did: Replaced `p["offset"]` with `p["ofset"]` in `main.py`.
- Console: No 'Access-Control-Allow-Origin' header is present on the requested resource.
- Network: Status 500 Internal Server Error in backend logs.
- Cause: Unhandled Python exceptions result in HTTP 500 without CORS headers attached.
- How I found it: Algorithm step 5 (Checking backend terminal logs).



course-catalog-api

Backend of the course catalog: FastAPI, SQLAlchemy 2.1, PostgreSQL 18, and Alembic migrations (Labs 4–7).

1. How to run

Python 3.11+ and PostgreSQL 16+ (tested on PostgreSQL 18, port 5434) are required.

Once, as the postgres superuser (or via pgAdmin 4), create the role and database:

CREATE ROLE catalog_app LOGIN PASSWORD 'change-me';
CREATE DATABASE course_catalog OWNER catalog_app;

Set up the virtual environment, apply migrations, seed initial data, and start the development server:

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# Ensure .env contains:
# DATABASE_URL=postgresql+psycopg://catalog_app:change-me@127.0.0.1:5434/course_catalog
# SQL_ECHO=true

alembic upgrade head
psql "postgresql://catalog_app:change-me@127.0.0.1:5434/course_catalog" -v ON_ERROR_STOP=1 -f seed.sql
fastapi dev main.py

Interactive API documentation (Swagger UI) is available at http://127.0.0.1:8000/docs.

2. API changes (Lab 7)

Data storage has been migrated from in-memory Python lists (data.py) to PostgreSQL 18 using SQLAlchemy 2.1 ORM and Alembic migrations:

- Persistent storage & session management: Every HTTP request receives an isolated Session via Depends(get_db) with automatic cleanup after request completion.
- Course filtering & schema updates:
  - Added the required level field (beginner / intermediate) to the Course ORM model and CourseOut Pydantic schema.
  - GET /courses now supports query filtering by ?level=<value> alongside ?is_elective=, ?sort=, ?limit=, and ?offset=.
- New endpoints for students, enrollments, and statistics:
  - GET /students, POST /students, DELETE /students/{student_id}
  - GET /enrollments, POST /enrollments, DELETE /enrollments/{enrollment_id}
  - GET /stats — aggregated course and student enrollment metrics computed via SQL.
- Database constraint error mapping: PostgreSQL IntegrityError exceptions are intercepted via err.orig.diag.constraint_name and translated into semantic HTTP responses (404, 409, 422) instead of unhandled 500 errors.

3. Alembic commands reference

Command | Purpose
--- | ---
alembic init alembic | Initialize the alembic/ directory and alembic.ini configuration file.
alembic revision --autogenerate -m "..." --rev-id XXXX | Compare Base.metadata against the live DB schema and generate a migration script.
alembic revision -m "..." --rev-id XXXX | Create an empty migration template for manual operations without autogeneration.
alembic upgrade head | Apply all pending migrations up to the latest revision.
alembic upgrade 0001:0002 --sql | Output raw SQL statements for a revision range without modifying the DB (offline mode).
alembic downgrade -1 | Roll back the most recently applied migration by one step.
alembic current | Display the current database revision stored in the alembic_version table.
alembic heads | Show all branch heads in alembic/versions/ (used to detect diverging branches).
alembic merge heads -m "..." --rev-id XXXX | Merge multiple divergent migration branches into a single linear merge revision.
alembic check | Verify that SQLAlchemy models and the live database schema are completely in sync.
alembic stamp head | Mark an existing database as being at head without executing upgrade() DDL statements.

4. Experiment log (Experiments 1–8)

1. Naming convention mismatch (NAMING_CONVENTION): Temporarily changing "uq" from "%(table_name)s_%(column_0_N_name)s_key" to "%(table_name)s_%(column_0_name)s_unique" caused check_models.py to report mismatched constraint names (enrollments_course_id_unique, students_email_unique vs PostgreSQL's *_key). Restoring the original template resolved the diff.
2. Bypassing Pydantic validation (Field(min_length=2)): Removing min_length=2 on StudentIn.name allowed a 1-character name ("N") past FastAPI validation, which PostgreSQL immediately rejected via CheckConstraint("length(name) >= 2") (students_name_check), returning 500 Internal Server Error (try_errors.py passed 4 of 5). Restoring Field(min_length=2) restored 422 validation.
3. Typo in CONSTRAINT_ERRORS key: Renaming "students_email_key" to "students_email_uniq" in main.py caused duplicate email registration to fall through the constraint lookup dictionary and return 500 instead of 409 Conflict. Fixing the key restored 5 of 5 as expected.
4. Manual schema drift detection (alembic check): Altering courses.title directly in PostgreSQL (DROP NOT NULL and TYPE varchar(100)) caused alembic check to fail with FAILED: New upgrade operations detected (modify_nullable and modify_type). Reverting the column to TEXT NOT NULL restored schema parity.
5. Direct NOT NULL column addition on non-empty table: Running an autogenerated ALTER TABLE courses ADD COLUMN level TEXT NOT NULL failed with psycopg.errors.NotNullViolation: column "level" of relation "courses" contains null values. Splitting the migration into 3 steps (ADD COLUMN ... NULL -> UPDATE -> ALTER COLUMN ... SET NOT NULL) succeeded cleanly.
6. Missing import models in alembic/env.py: Commenting out import models left Base.metadata empty, causing alembic revision --autogenerate to generate op.drop_table(...) for enrollments, students, and courses. Uncommenting the import prevented destructive autogeneration.
7. Model change detection (Student.phone): Adding phone: Mapped[str | None] to Student triggered Detected added column 'students.phone' during alembic check. Removing the temporary field restored schema parity.
8. Branching and merging heads (alembic merge heads): Creating two parallel revisions (0003 and 0004 --head 0002 --splice) produced two concurrent heads in alembic heads. Running alembic merge heads --rev-id 0005 unified them (down_revision = ('0003', '0004')), after which the temporary files (0003–0005) were removed.

5. Design decisions

- Explicit NAMING_CONVENTION in MetaData: PostgreSQL automatically generates predictable constraint names (<table>_<col>_key, <table>_<col>_fkey, <table>_pkey). Configuring matching templates in SQLAlchemy prevents false-positive diffs during Alembic autogeneration and allows the API to map violated constraint names reliably.
- Three-step migration for mandatory columns: Adding a NOT NULL column without a permanent server_default to a populated table violates relational integrity. Separating schema addition (nullable=True), data backfill (UPDATE ... CASE WHEN is_elective ...), and constraint enforcement (nullable=False) ensures safe, deterministic migrations.
- Two-layer integrity protection (DB + API): Business invariants (credits > 0, likes >= 0, length(name) >= 2, UNIQUE(email), ON DELETE RESTRICT) are enforced directly inside PostgreSQL so data cannot be corrupted by any client, while raise_http_error translates diag.constraint_name into semantic HTTP status codes.
- Baseline synchronization via alembic stamp head: Because the initial tables were deployed via schema.sql in Lab 6, migration 0001 was verified on an empty scratch database and then stamped onto course_catalog as a clean baseline for subsequent migrations.

6. Migration 0002 self-check

To confirm that revision 0002 (0002_add_course_level.py) is fully reversible and leaves zero schema drift:

- Offline SQL inspection (alembic upgrade 0001:0002 --sql):

ALTER TABLE courses ADD COLUMN level TEXT;
UPDATE courses SET level = CASE WHEN is_elective THEN 'beginner' ELSE 'intermediate' END;
ALTER TABLE courses ALTER COLUMN level SET NOT NULL;
UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

- Round-trip execution:
  - alembic downgrade -1 executes ALTER TABLE courses DROP COLUMN level and reverts alembic_version to 0001.
  - alembic upgrade head re-adds courses.level, backfills 'beginner' for elective courses (api-design, ai-integration) and 'intermediate' for core courses, enforces NOT NULL, and advances alembic_version to 0002 (head).
- Verification checks:
  - alembic current -> 0002 (head)
  - alembic check -> No new upgrade operations detected.
  - GET /courses?level=beginner -> returns api-design and ai-integration with "level": "beginner".