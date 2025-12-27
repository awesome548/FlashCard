import genanki
import random  
from supabase import create_client, Client
from dotenv import dotenv_values

# ── Configure Supabase ──────────────────────────────
SUPABASE_KEY = dotenv_values().get("SUPABASE_KEY")
SUPABASE_URL: str = "https://nzgzmikoutzhrajszvxz.supabase.co"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL and Key must be set in environment variables or directly in the script.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Generate unique Anki model ID ──────────────────
ids = random.randrange(1 << 30, 1 << 31)
print(f"Generated model ID: {ids}")
deck_id = 20010115 

my_model = genanki.Model(
  ids,
  'First Model',
  fields=[
    {'name': 'Vocab'},
    {'name': 'Meaning'},
    {'name': 'Example'},
    {'name': 'Alternatives'},
  ],
  templates=[
    {
      'name': 'Card 1',
      'qfmt': '''
        <div style="font-family: Arial, sans-serif; font-size: 24px; text-align: center; margin-top: 40px;">
          {{Vocab}}
        </div>
        <hr style="margin: 20px 0;">
      ''',
      'afmt': '''
        {{FrontSide}}
        <div style="font-family: Arial, sans-serif; font-size: 18px; margin: 10px 0; text-align:left;">
          <strong>Meaning:</strong>
          <br>
          {{Meaning}}
        </div>
        <div style="font-family: Arial, sans-serif; font-size: 18px; margin: 10px 0; text-align:left;">
          <strong>Example:</strong>
          <br>
          {{Example}}
        </div>
        <div style="font-family: Arial, sans-serif; font-size: 18px; margin: 10px 0; color: #555;">
          <strong>{{Alternatives}}</strong>
        </div>
      ''',
    },
  ]
)

my_deck = genanki.Deck(deck_id, 'English Vocabulary')


# ── Track IDs to update at the end ──────────────────
vocab_ids_to_update = []
sentence_ids_to_update = []


# ── Fetch vocabulary entries ────────────────────────
response = (
    supabase.table("vocabulary")
    .select("*")
    .neq("anki_added", 1) 
    .execute()
)

if not response.data:
    print("No vocabulary data found.")
else:
    for vocab_entry in response.data:
        vocab = vocab_entry["vocab"]
        meaning = vocab_entry["meaning"]
        examples = vocab_entry["examples"]
        vocab_id = vocab_entry["id"]

        # Fetch alternatives for this vocab entry
        alt_response = (
            supabase.table("alternative")
            .select("text")
            .eq("vocab_id", vocab_id)
            .execute()
        )

        # Build synonyms string
        synonyms = ", ".join([alt["text"] for alt in alt_response.data]) if alt_response.data else ""

        # Create note and add to deck
        note = genanki.Note(
            model=my_model,
            fields=[vocab, meaning, examples, synonyms]
        )
        my_deck.add_note(note)
        print(f"Added vocab: {vocab}")

        # Track this ID to update later
        vocab_ids_to_update.append(vocab_id)


# ── Fetch sentence entries ──────────────────────────
response = (
    supabase.table("sentence")
    .select("*")
    .neq("anki_added", 1)
    .execute()
)
if not response.data:
    print("No sentence data found.")
else:
    for vocab_entry in response.data:
        sentence = vocab_entry["sentence"]
        meaning = vocab_entry["meaning"]
        examples = vocab_entry["examples"]
        sentence_id = vocab_entry["id"]

        # Create note and add to deck
        note = genanki.Note(
            model=my_model,
            fields=[sentence, meaning, examples, ""]
        )
        my_deck.add_note(note)
        print(f"Added sentence: {sentence}")

        # Track this ID to update later
        sentence_ids_to_update.append(sentence_id)


# ── Export to .apkg file ────────────────────────────
genanki.Package(my_deck).write_to_file('vocabulary_flashcards_2.apkg')
print("Anki package created: vocabulary_flashcards_2.apkg")


# ── Update database entries to mark as added ────────
if vocab_ids_to_update:
    for vid in vocab_ids_to_update:
        _ = supabase.table("vocabulary").update({"anki_added": 1}).eq("id", vid).execute()

if sentence_ids_to_update:
    for sid in sentence_ids_to_update:
        _ = supabase.table("sentence").update({"anki_added": 1}).eq("id", sid).execute()