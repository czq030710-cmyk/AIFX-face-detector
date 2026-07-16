from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions


@dataclass
class UserContext:
    user_id: str
    email: str | None
    access_token: str | None
    is_authenticated: bool


class SupabaseGateway:
    def __init__(self) -> None:
        self.url = os.getenv("SUPABASE_URL", "").strip()
        self.anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        self.bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "face-processing").strip()
        self.asset_buckets = {
            "original": os.getenv("SUPABASE_ORIGINAL_BUCKET", "aifx-originals").strip(),
            "crop": os.getenv("SUPABASE_CROP_BUCKET", "aifx-crops").strip(),
            "enhanced_crop": os.getenv("SUPABASE_ENHANCED_CROP_BUCKET", "aifx-enhanced-crops").strip(),
            "enhanced_original": os.getenv(
                "SUPABASE_ENHANCED_ORIGINAL_BUCKET",
                "aifx-enhanced-originals",
            ).strip(),
        }

        self.enabled = bool(self.url and self.anon_key and self.service_role_key)
        self.auth_client = create_client(self.url, self.anon_key) if self.url and self.anon_key else None
        self.service_client = (
            create_client(self.url, self.service_role_key)
            if self.enabled
            else None
        )

    def sign_up(self, email: str, password: str) -> dict[str, Any]:
        if not self.auth_client:
            raise HTTPException(status_code=503, detail="Supabase Auth is not configured.")
        try:
            response = self.auth_client.auth.sign_up({"email": email, "password": password})
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Sign up failed: {exc}") from exc
        return self._auth_response_to_dict(response)

    def sign_in(self, email: str, password: str) -> dict[str, Any]:
        if not self.auth_client:
            raise HTTPException(status_code=503, detail="Supabase Auth is not configured.")
        try:
            response = self.auth_client.auth.sign_in_with_password({"email": email, "password": password})
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Login failed: {exc}") from exc
        return self._auth_response_to_dict(response)

    def start_google_oauth(self, redirect_to: str) -> tuple[Any, str]:
        if not self.auth_client:
            raise HTTPException(status_code=503, detail="Supabase Auth is not configured.")
        oauth_client = create_client(
            self.url,
            self.anon_key,
            options=SyncClientOptions(flow_type="pkce", persist_session=True),
        )
        try:
            response = oauth_client.auth.sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {"redirect_to": redirect_to},
                }
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Starting Google login failed: {exc}") from exc
        oauth_url = str(getattr(response, "url", "") or "").strip()
        if not oauth_url:
            raise HTTPException(status_code=502, detail="Supabase did not return a Google login URL.")
        return oauth_client, oauth_url

    def exchange_oauth_code(self, oauth_client: Any, code: str) -> dict[str, Any]:
        try:
            response = oauth_client.auth.exchange_code_for_session({"auth_code": code})
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Google login callback failed: {exc}") from exc
        return self._auth_response_to_dict(response)

    def get_user_from_authorization(self, authorization: str | None) -> UserContext:
        if not self.enabled:
            return UserContext(
                user_id="local-demo-user",
                email=None,
                access_token=None,
                is_authenticated=False,
            )

        token = self._bearer_token(authorization)
        try:
            response = self.service_client.auth.get_user(token)
        except Exception as exc:
            raise HTTPException(status_code=401, detail=f"Invalid or expired login token: {exc}") from exc

        user = getattr(response, "user", None)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired login token.")
        return UserContext(
            user_id=user.id,
            email=getattr(user, "email", None),
            access_token=token,
            is_authenticated=True,
        )

    def upload_bytes(
        self,
        path: str,
        data: bytes,
        content_type: str,
        bucket_name: str | None = None,
        upsert: bool = False,
    ) -> str:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        try:
            bucket = self.service_client.storage.from_(bucket_name or self.bucket)
            bucket.upload(
                path,
                data,
                file_options={
                    "content-type": content_type,
                    "upsert": "true" if upsert else "false",
                },
            )
            return bucket.get_public_url(path)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Supabase Storage upload failed: {exc}") from exc

    def bucket_for_asset(self, asset_type: str) -> str:
        bucket = self.asset_buckets.get(asset_type)
        if not bucket:
            known_types = ", ".join(sorted(self.asset_buckets))
            raise HTTPException(status_code=400, detail=f"asset_type must be one of: {known_types}.")
        return bucket

    def ensure_asset_buckets(self) -> list[dict[str, str]]:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        existing_buckets = self.service_client.storage.list_buckets()
        existing_names = {
            getattr(bucket, "name", None) or bucket.get("name")
            for bucket in existing_buckets
        }
        results = []
        for asset_type, bucket_name in self.asset_buckets.items():
            if bucket_name in existing_names:
                results.append({"asset_type": asset_type, "bucket": bucket_name, "status": "exists"})
                continue
            try:
                self.service_client.storage.create_bucket(
                    bucket_name,
                    options={"public": True},
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Creating bucket '{bucket_name}' failed: {exc}") from exc
            results.append({"asset_type": asset_type, "bucket": bucket_name, "status": "created"})
        return results

    def next_enhancement_job_id(self) -> str:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        try:
            response = self.service_client.rpc("next_enhancement_job_id").execute()
            if response.data:
                return str(response.data)
        except Exception:
            # Older databases may not have the atomic counter function yet.
            pass

        prefix = datetime.now().strftime("%Y%m%d")
        try:
            response = (
                self.service_client.table("enhancement_jobs")
                .select("job_id")
                .like("job_id", f"{prefix}_%")
                .order("job_id", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Loading latest enhancement job id failed: {exc}") from exc

        latest_job_id = (response.data or [{}])[0].get("job_id") if response.data else None
        next_number = 1
        if latest_job_id:
            _, _, suffix = latest_job_id.partition("_")
            if suffix.isdigit():
                next_number = int(suffix) + 1
        return f"{prefix}_{next_number:02d}"

    def create_enhancement_batch(
        self,
        *,
        job: dict[str, Any],
        faces: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        if not faces:
            raise HTTPException(status_code=400, detail="At least one face is required.")
        try:
            self.service_client.table("enhancement_jobs").insert(job).execute()
            self.service_client.table("enhancement_job_faces").insert(faces).execute()
        except Exception as exc:
            try:
                self.service_client.table("enhancement_jobs").delete().eq(
                    "job_id",
                    job["job_id"],
                ).execute()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"Creating enhancement job failed: {exc}") from exc
        return self.get_enhancement_job_with_faces(job["job_id"], job["user_id"])

    def get_enhancement_job_with_faces(
        self,
        job_id: str,
        user: UserContext | str,
    ) -> dict[str, Any]:
        user_id = user.user_id if isinstance(user, UserContext) else user
        job = self.get_enhancement_job(job_id, UserContext(user_id, None, None, True))
        job["faces"] = self.list_enhancement_faces(job_id, user_id)
        return job

    def list_enhancement_faces(self, job_id: str, user_id: str) -> list[dict[str, Any]]:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        try:
            response = (
                self.service_client.table("enhancement_job_faces")
                .select("*")
                .eq("job_id", job_id)
                .eq("user_id", user_id)
                .order("output_index", desc=False)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Loading enhancement faces failed: {exc}") from exc
        return response.data or []

    def list_enhancement_jobs(self, user: UserContext, limit: int = 10) -> list[dict[str, Any]]:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        try:
            response = (
                self.service_client.table("enhancement_jobs")
                .select("*")
                .eq("user_id", user.user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Loading enhancement jobs failed: {exc}") from exc
        jobs = response.data or []
        for job in jobs:
            job["faces"] = self.list_enhancement_faces(job["job_id"], user.user_id)
        return jobs

    def claim_next_enhancement_face(self) -> dict[str, Any] | None:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        try:
            response = (
                self.service_client.table("enhancement_job_faces")
                .select("*")
                .in_("status", ["queued", "retrying"])
                .order("created_at", desc=False)
                .limit(50)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Loading queued faces failed: {exc}") from exc

        now = datetime.now(timezone.utc)
        for face in response.data or []:
            next_retry_at = face.get("next_retry_at")
            if next_retry_at:
                try:
                    retry_at = datetime.fromisoformat(next_retry_at.replace("Z", "+00:00"))
                except ValueError:
                    retry_at = now
                if retry_at > now:
                    continue
            try:
                claimed = (
                    self.service_client.table("enhancement_job_faces")
                    .update(
                        {
                            "status": "processing",
                            "updated_at": now.isoformat(timespec="seconds"),
                        }
                    )
                    .eq("id", face["id"])
                    .in_("status", ["queued", "retrying"])
                    .execute()
                )
            except Exception:
                continue
            if claimed.data:
                return claimed.data[0]
        return None

    def update_enhancement_face(
        self,
        face_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        update_fields = {
            **fields,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        try:
            response = (
                self.service_client.table("enhancement_job_faces")
                .update(update_fields)
                .eq("id", face_id)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Updating enhancement face failed: {exc}") from exc
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Enhancement face '{face_id}' was not found.")
        return response.data[0]

    def mark_enhancement_face_failure(
        self,
        *,
        face: dict[str, Any],
        error_message: str,
    ) -> dict[str, Any]:
        retry_count = int(face.get("retry_count") or 0) + 1
        max_retries = int(face.get("max_retries") or 3)
        failed_permanently = retry_count >= max_retries
        next_retry_at = None
        if not failed_permanently:
            next_retry_at = (
                datetime.now(timezone.utc) + timedelta(seconds=2 ** retry_count)
            ).isoformat(timespec="seconds")
        return self.update_enhancement_face(
            face["id"],
            {
                "status": "failed" if failed_permanently else "retrying",
                "retry_count": retry_count,
                "next_retry_at": next_retry_at,
                "last_error": error_message[:1000],
            },
        )

    def retry_enhancement_face(
        self,
        *,
        job_id: str,
        face_id: str,
        user: UserContext,
    ) -> dict[str, Any]:
        try:
            response = (
                self.service_client.table("enhancement_job_faces")
                .select("*")
                .eq("id", face_id)
                .eq("job_id", job_id)
                .eq("user_id", user.user_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Loading enhancement face failed: {exc}") from exc
        if not response.data:
            raise HTTPException(status_code=404, detail="Enhancement face was not found.")
        return self.update_enhancement_face(
            face_id,
            {
                "status": "queued",
                "retry_count": 0,
                "next_retry_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "last_error": None,
            },
        )

    def save_enhancement_upload(
        self,
        *,
        job_id: str,
        user: UserContext,
        asset_type: str,
        bucket: str,
        storage_path: str,
        storage_url: str,
        source_filename: str | None,
        purpose: str,
        content_type: str,
        size_bytes: int,
    ) -> None:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")

        field_prefixes = {
            "original": "original",
            "crop": "crop",
            "enhanced_crop": "enhanced_crop",
            "enhanced_original": "enhanced_original",
        }
        status_by_asset = {
            "original": "original_uploaded",
            "crop": "crop_uploaded",
            "enhanced_crop": "enhanced_crop_uploaded",
            "enhanced_original": "completed",
        }
        field_prefix = field_prefixes.get(asset_type)
        if not field_prefix:
            known_types = ", ".join(sorted(field_prefixes))
            raise HTTPException(status_code=400, detail=f"asset_type must be one of: {known_types}.")

        upload_metadata = {
            "last_upload": {
                "asset_type": asset_type,
                "purpose": purpose,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "stored_at": datetime.now().isoformat(timespec="seconds"),
            }
        }
        asset_fields = {
            f"{field_prefix}_bucket": bucket,
            f"{field_prefix}_path": storage_path,
            f"{field_prefix}_url": storage_url,
            "status": status_by_asset[asset_type],
            "metadata": upload_metadata,
        }

        try:
            if asset_type == "original":
                record = {
                    "job_id": job_id,
                    "user_id": user.user_id,
                    "source_filename": source_filename,
                    **asset_fields,
                }
                self.service_client.table("enhancement_jobs").upsert(
                    record,
                    on_conflict="job_id",
                ).execute()
                return

            response = (
                self.service_client.table("enhancement_jobs")
                .update(asset_fields)
                .eq("job_id", job_id)
                .eq("user_id", user.user_id)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Saving enhancement job upload failed: {exc}") from exc

        if not response.data:
            raise HTTPException(status_code=404, detail=f"Enhancement job '{job_id}' was not found for this user.")

    def get_enhancement_job(self, job_id: str, user: UserContext) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        try:
            response = (
                self.service_client.table("enhancement_jobs")
                .select("*")
                .eq("job_id", job_id)
                .eq("user_id", user.user_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Loading enhancement job failed: {exc}") from exc
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Enhancement job '{job_id}' was not found for this user.")
        return response.data[0]

    def update_enhancement_job(
        self,
        job_id: str,
        user: UserContext,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        update_fields = {
            **fields,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        try:
            response = (
                self.service_client.table("enhancement_jobs")
                .update(update_fields)
                .eq("job_id", job_id)
                .eq("user_id", user.user_id)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Updating enhancement job failed: {exc}") from exc
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Enhancement job '{job_id}' was not found for this user.")
        return response.data[0]

    def queue_comfy_upload(
        self,
        job_id: str,
        user: UserContext,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        job = self.get_enhancement_job(job_id, user)
        if not job.get("crop_url"):
            raise HTTPException(status_code=400, detail="Upload a crop asset before queueing ComfyUI upload.")
        return self.update_enhancement_job(
            job_id,
            user,
            {
                "status": "queued_for_comfy_upload",
                "retry_count": 0,
                "max_retries": max_retries,
                "next_retry_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "last_error": None,
            },
        )

    def next_comfy_upload_job(self, user: UserContext) -> dict[str, Any] | None:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        try:
            response = (
                self.service_client.table("enhancement_jobs")
                .select("*")
                .eq("user_id", user.user_id)
                .in_("status", ["queued_for_comfy_upload", "retrying_comfy_upload"])
                .order("created_at", desc=False)
                .limit(20)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Loading queued enhancement jobs failed: {exc}") from exc

        now = datetime.now(timezone.utc)
        for job in response.data or []:
            next_retry_at = job.get("next_retry_at")
            if not next_retry_at:
                return job
            try:
                retry_at = datetime.fromisoformat(next_retry_at.replace("Z", "+00:00"))
            except ValueError:
                return job
            if retry_at <= now:
                return job
        return None

    def mark_comfy_upload_success(
        self,
        *,
        job: dict[str, Any],
        user: UserContext,
        comfy_input_filename: str,
        comfy_input_subfolder: str = "",
        comfy_input_type: str = "input",
    ) -> dict[str, Any]:
        metadata = dict(job.get("metadata") or {})
        metadata["comfy_upload"] = {
            "filename": comfy_input_filename,
            "subfolder": comfy_input_subfolder,
            "type": comfy_input_type,
            "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        return self.update_enhancement_job(
            job["job_id"],
            user,
            {
                "status": "uploaded_to_comfy",
                "comfy_input_filename": comfy_input_filename,
                "comfy_input_subfolder": comfy_input_subfolder,
                "comfy_input_type": comfy_input_type,
                "last_error": None,
                "metadata": metadata,
            },
        )

    def mark_comfy_upload_failure(
        self,
        *,
        job: dict[str, Any],
        user: UserContext,
        error_message: str,
    ) -> dict[str, Any]:
        retry_count = int(job.get("retry_count") or 0) + 1
        max_retries = int(job.get("max_retries") or 3)
        retry_delay_seconds = 2 ** retry_count
        failed_permanently = retry_count >= max_retries
        next_retry_at = None
        if not failed_permanently:
            next_retry_at = (
                datetime.now(timezone.utc) + timedelta(seconds=retry_delay_seconds)
            ).isoformat(timespec="seconds")
        return self.update_enhancement_job(
            job["job_id"],
            user,
            {
                "status": "failed_comfy_upload" if failed_permanently else "retrying_comfy_upload",
                "retry_count": retry_count,
                "next_retry_at": next_retry_at,
                "last_error": error_message[:1000],
            },
        )

    def insert_task(self, record: dict[str, Any]) -> None:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        try:
            self.service_client.table("task_history").insert(record).execute()
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Saving task history failed: {exc}") from exc

    def list_tasks(self, user: UserContext, limit: int) -> list[dict[str, Any]]:
        if not self.enabled:
            raise RuntimeError("Supabase is not configured.")
        try:
            response = (
                self.service_client.table("task_history")
                .select("*")
                .eq("user_id", user.user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Loading task history failed: {exc}") from exc
        return response.data or []

    @staticmethod
    def _bearer_token(authorization: str | None) -> str:
        if not authorization:
            raise HTTPException(status_code=401, detail="Login required.")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Authorization header must use Bearer token.")
        return token.strip()

    @staticmethod
    def _auth_response_to_dict(response: Any) -> dict[str, Any]:
        session = getattr(response, "session", None)
        user = getattr(response, "user", None)
        return {
            "access_token": getattr(session, "access_token", None),
            "refresh_token": getattr(session, "refresh_token", None),
            "expires_at": getattr(session, "expires_at", None),
            "user": {
                "id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
            } if user else None,
            "message": (
                "Signed in."
                if session
                else "Account created. Check email confirmation settings if no token was returned."
            ),
        }
