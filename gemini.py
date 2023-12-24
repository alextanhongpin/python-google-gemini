import google.generativeai as genai
import os
import json
import sqlite3

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Configure the gemini client.
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel("gemini-pro")


conn = sqlite3.connect("gemini.db")
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS prompts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt TEXT,
        option JSON,
        completion JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
)
conn.commit()
conn.close()

# The results cannot be serialized directly.
def _join_safety_ratings(safety_ratings):
    return [
        dict(
            category=r.category,
            category_text=repr(r.category),
            probability=r.probability,
            probability_text=repr(r.probability),
        )
        for r in safety_ratings
    ]


def _join_response(response):
    return {
        "text": response.text,
        "candidates": [
            dict(
                index=candidate.index,
                content=dict(
                    role=candidate.content.role,
                    parts=[part.text for part in candidate.content.parts],
                ),
                finish_reason=candidate.finish_reason,
                finish_reason_text=repr(candidate.finish_reason),
                safety_ratings=_join_safety_ratings(candidate.safety_ratings),
            )
            for candidate in response.candidates
        ],
        "prompt_feedback": {
            "safety_ratings": _join_safety_ratings(
                response.prompt_feedback.safety_ratings
            )
        },
    }


# Create a decorator that snaphots the query and the result.
def snapshot(func):
    def wrapper(*args, **kwargs):
        # Call the function and get the result.
        result = func(*args, **kwargs)

        # Get the query.
        prompt = args[0]

        # Save the query and the result to the database.
        conn = sqlite3.connect("gemini.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO prompts(prompt, option, completion)
            VALUES (?, json(?), json(?))
            """,
            (prompt, json.dumps(kwargs), json.dumps(_join_response(result))),
        )
        conn.commit()
        conn.close()

        # Return the result.
        return result

    return wrapper


@snapshot
def generate_content(*args, **kwargs):
    return model.generate_content(*args, **kwargs)
