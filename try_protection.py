import httpx

URL = "http://127.0.0.1:8000/graphql"


def send(query: str):
    data = httpx.post(URL, json={"query": query}).json()
    if "errors" in data:
        return "blocked: " + data["errors"][0]["message"]
    return "allowed"



print("normal query :", send("{ student(id: 2) { enrollments { course { title } } } }"))


print("deep query   :", send(
    "{ courses { enrollments { course { enrollments { course { enrollments { id } } } } } } }"
))


aliases = " ".join(f"a{i}: courses {{ id }}" for i in range(12))
print("alias flood  :", send(f"{{ {aliases} }}"))

many_fields = " ".join(["id title"] * 300)
print("token flood  :", send(f"{{ courses {{ {many_fields} }} }}"))