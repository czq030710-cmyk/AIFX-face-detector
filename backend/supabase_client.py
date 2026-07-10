from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from supabase import create_client


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
