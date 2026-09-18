from faker import Faker
import random
import json
import os

fake = Faker()

NUMBER_OF_CANDIDATES = 10

candidates = []

for i in range(NUMBER_OF_CANDIDATES):

    candidate = {
        "name": fake.name(),
        "email": fake.unique.email(),
        "exam_id": f"EXAM-{random.randint(1000, 9999)}",
        "score": random.randint(0, 100),
        "status": random.choice([
            "COMPLETED",
            "PAUSED",
            "SUBMITTED"
        ]),
        "start_time": str(fake.date_time_this_year()),
        "location": fake.city()
    }

    candidates.append(candidate)


os.makedirs("data", exist_ok=True)

file_path = "data/fake_candidates.json"

with open(file_path, "w") as file:
    json.dump(candidates, file, indent=4)


print("Synthetic data generated successfully!")
print(f"Number of candidates: {NUMBER_OF_CANDIDATES}")
print(f"Saved to: {file_path}")