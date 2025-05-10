import csv
import json
from openai import OpenAI
import os 
from dotenv import load_dotenv, dotenv_values 
from sqlalchemy import (
    create_engine, Column, Integer, String, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import re

def extract_json_from_response(text: str) -> dict:
    """
    Given a ChatGPT response that contains a ```json ... ``` block,
    finds the first JSON object inside and returns it as a Python dict.
    """
    # This will match ```json { ... } ```
    pattern = r"```json\s*(\{.*?\})\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return json.loads(text)
    json_str = match.group(1)
    return json.loads(json_str)

# ── 1. Configure OpenAI ───────────────────────────────────────────────────────
def fetch_ai_data(term: str,client) -> dict:
    prompt = f"""
You are an excellent English Speaker. Given the input term: «{term}», do the following:
1) Detect if it's a single word or a multi-word phrase.
2) If it's a phrase, classify it as either:
   - a phrasal verb (then extract the verb part into "verb"), or
   - an idiom (set "verb" to null).
3) Produce:
   • "meaning": a one-sentence definition.
   • "examples": one example sentences.
   • "synonyms": (if word) an array of two synonyms.
   • "alternatives": (if phrase) an array of two alternative phrasings.

Return JSON file exactly in this content:
  "type": "word" | "phrase",
  "verb": string|null,
  "meaning": string,
  "examples": string,
  "synonyms": [string, string],
  "alternatives": [string, string]
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return extract_json_from_response(response.choices[0].message.content)

# ── 2. Define our SQL schema via SQLAlchemy ──────────────────────────────────
Base = declarative_base()

class Word(Base):
    __tablename__ = 'word'
    id      = Column(Integer, primary_key=True, autoincrement=True)
    word    = Column(String, nullable=False, unique=True)
    meaning = Column(Text,   nullable=False)
    synonym = Column(Text,   nullable=False)  # we'll JSON‐dump

class Phrase(Base):
    __tablename__ = 'phrase'
    id          = Column(Integer, primary_key=True, autoincrement=True)
    phrase      = Column(String, nullable=False) # unique=False because we want to allow same phrases with different meanings
    verb        = Column(String, nullable=True)
    meaning     = Column(Text,   nullable=False)
    examples    = Column(Text,   nullable=False)  # JSON‐dump
    alternative = Column(Text,   nullable=False)  # JSON‐dump

db_path = 'flashcards.db'
engine = create_engine(f'sqlite:///{db_path}')
Session = sessionmaker(bind=engine)
if not os.path.exists(db_path):
    Base.metadata.create_all(engine)

# ── 3. Read CSV → AI → DB ────────────────────────────────────────────────────
def process_csv(path='data.csv'):
    session = Session()
    client = OpenAI()
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
        for row in rows:
            print(row)
            term = row['Terms'].strip()
            if not term:
                continue

            if row['Stored'] == '1':
                print(f"Term '{term}' already stored, skipping.")
                continue

            data = fetch_ai_data(term,client)

            if data["type"] == "word":
                w = Word(
                    word    = term,
                    meaning = data["meaning"],
                    synonym = json.dumps(data["synonyms"], ensure_ascii=False)
                )
                session.merge(w) 
                row['Stored'] = '1'

            else:
                p = Phrase(
                    phrase      = term,
                    verb        = data["verb"],  # or None
                    meaning     = data["meaning"],
                    examples    = json.dumps(data["examples"], ensure_ascii=False),
                    alternative = json.dumps(data["alternatives"], ensure_ascii=False)
                )
                session.merge(p)
                row['Stored'] = '1'

    session.commit()
    with open(path, 'w', newline='', encoding='utf-8-sig') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    session.close()
    print("All terms processed and stored into SQL.")

if __name__ == "__main__":
    load_dotenv() 
    process_csv()
