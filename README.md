# FlashCard

Pipeline for turning Supabase content into Anki flashcards.

## Workflow
- Backend data processing happens in Google Colab: https://colab.research.google.com/drive/1I4D6d3C4fQQgHPRg-WKBdNbPijTXbM3D?usp=sharing
- Ensure the Supabase credentials are available (e.g., `SUPABASE_KEY` in a `.env` file).
- From the repo root, run `python Anki.py` to pull unexported rows from Supabase, build `vocabulary_flashcards_2.apkg`, and mark those rows as exported.
