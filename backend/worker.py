from __future__ import annotations

import os
import time

from backend.main import process_next_enhancement_face


def main() -> None:
    poll_seconds = max(1.0, float(os.getenv("AIFX_WORKER_POLL_SECONDS", "2")))
    print(f"AIFX worker polling Supabase every {poll_seconds:g}s")
    while True:
        try:
            result = process_next_enhancement_face()
            print(
                f"worker status={result.get('status') or result.get('job_status')} "
                f"job_id={result.get('job_id', '-')} face_id={result.get('face_id', '-')}"
            )
            if result.get("status") == "idle":
                time.sleep(poll_seconds)
        except Exception as exc:
            print(f"worker cycle failed: {exc}")
            time.sleep(min(30.0, poll_seconds * 2))


if __name__ == "__main__":
    main()
