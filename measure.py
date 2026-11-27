import time
import httpx

BASE_URL = "http://127.0.0.1:8000"
STUDENT_ID = 2

GQL_QUERY = """
query StudentCourses($id: ID!) {
  student(id: $id) {
    name
    email
    enrollments {
      course {
        title
        credits
        likes
      }
    }
  }
}
"""


def measure_rest(client: httpx.Client, student_id: int) -> dict:
    t0 = time.perf_counter()
    http_calls = 0
    sql_queries = 0
    total_bytes = 0

    # 1. GET /enrollments (фильтруем записи нужного студента)
    r_enr = client.get(f"{BASE_URL}/enrollments")
    r_enr.raise_for_status()
    http_calls += 1
    sql_queries += int(r_enr.headers.get("x-sql-queries", 0))
    total_bytes += len(r_enr.content)
    enrollments = [e for e in r_enr.json() if e["studentId"] == student_id]

    # 2. GET /courses/{courseId} для каждого курса студента
    for enr in enrollments:
        r_course = client.get(f"{BASE_URL}/courses/{enr['courseId']}")
        r_course.raise_for_status()
        http_calls += 1
        sql_queries += int(r_course.headers.get("x-sql-queries", 0))
        total_bytes += len(r_course.content)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "http": http_calls,
        "sql": sql_queries,
        "bytes": total_bytes,
        "ms": elapsed_ms,
    }


def measure_graphql(client: httpx.Client, student_id: int) -> dict:
    t0 = time.perf_counter()
    res = client.post(
        f"{BASE_URL}/graphql",
        json={"query": GQL_QUERY, "variables": {"id": str(student_id)}},
    )
    res.raise_for_status()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "http": 1,
        "sql": int(res.headers.get("x-sql-queries", 0)),
        "bytes": len(res.content),
        "ms": elapsed_ms,
    }


def main() -> None:
    with httpx.Client(timeout=15.0) as client:
        client.get(f"{BASE_URL}/")
        rest = measure_rest(client, STUDENT_ID)
        gql = measure_graphql(client, STUDENT_ID)

    print(f"{'Metric':<18} {'REST':>10} {'GraphQL':>10}")
    print("-" * 40)
    print(f"{'HTTP requests':<18} {rest['http']:>10} {gql['http']:>10}")
    print(f"{'SQL queries':<18} {rest['sql']:>10} {gql['sql']:>10}")
    print(f"{'Payload (bytes)':<18} {rest['bytes']:>10} {gql['bytes']:>10}")
    print(f"{'Time (ms)':<18} {rest['ms']:>10.2f} {gql['ms']:>10.2f}")


if __name__ == "__main__":
    main()