NE PAS FUSIONNER — revue demandée à lazizbekravshanov.

Implements R24 (P1): When the background task `_write_task` fails (invalid plan or exception), the failure is now registered in `_FILM_WRITE_FAILED` keyed by `(lang, seconds)`. 

Changes:
- `naviguide-simulator/server/official_store.py`: Added `_FILM_WRITE_FAILED` set, populate it in `_write_task` on early return and exceptions, and `serve_film` returns `{"status": "failed", "hasWritten": false, "style": "written"}` when the key is in the failed set.
- `naviguide-simulator/src/hooks/useReplay.js`: In `filmWriteNextStep`, handle failure / status `"failed"` by setting `setFilmWriteError(true)` and `setFilmWriting(false)` so `ed2WriteFailed` is rendered.

All backend tests (76) and frontend tests (1195) pass.