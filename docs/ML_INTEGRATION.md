# Optional local ML integration (not implemented)

Integration points, in order of effort:
1. **Category/colour suggestions on upload** – in `images.save_upload` (or a new `vision.py`), call a local model and return `suggested_category`
   next to `suggested_color` in `/api/uploads`. The frontend already treats suggestions as unconfirmed (see "Detected colour").
2. **Embeddings + similarity** – add `embedding BLOB` to `items` via a new entry in `db.MIGRATIONS`; compute locally after upload; expose `/api/items/{id}/similar`.
3. **Compatibility component** – add a 0..1 component in `engine.score_outfit` (e.g. `parts["learned"]`) and a weight in `engine.WEIGHTS`; the weighted mean and breakdown update automatically.

Guidelines: make it opt-in (e.g. `VEYA_ML=1`), download weights only after the user agrees, document size/licence/hardware first, keep the app fully functional without it,
and keep model output separate from user-confirmed fields.
