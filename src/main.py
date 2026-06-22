from datetime import datetime
import json
import os


def generate_snapshot():

    data = {
        "date": str(datetime.now().date()),
        "pods": [
            {
                "name": "payments",
                "health": 8.5,
                "coverage": 87,
                "critical": 2,
                "high": 5,
                "medium": 10
            }
        ]
    }


    os.makedirs(
        "data/snapshots",
        exist_ok=True
    )


    today = datetime.now().date()


    with open(
        f"data/snapshots/{today}.json",
        "w"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


    with open(
        "data/latest.json",
        "w"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


if __name__ == "__main__":
    generate_snapshot()