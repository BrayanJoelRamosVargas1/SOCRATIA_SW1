"""Run the real P3-A configuration API smoke against the Docker stack."""

import json
import sys
import uuid

import httpx

from scripts.smoke_cu10 import API_URL, build_document


def main() -> int:
    client = httpx.Client(base_url=API_URL, timeout=300)
    suffix = uuid.uuid4().hex[:12]
    response = client.post(
        "/auth/register",
        json={
            "email": f"p3a-smoke-{suffix}@example.com",
            "full_name": "P3A Real Smoke",
            "password": f"Socratia simulation smoke {uuid.uuid4().hex}",
        },
    )
    response.raise_for_status()
    response = client.post(
        "/documents",
        files={
            "file": (
                "socratia-p3a-smoke.docx",
                build_document(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    response.raise_for_status()
    document_id = response.json()["id"]
    client.post(f"/documents/{document_id}/process").raise_for_status()
    client.post(f"/documents/{document_id}/questions/generate").raise_for_status()
    response = client.get("/jury-profiles")
    response.raise_for_status()
    profiles = response.json()
    if len(profiles) != 3:
        raise AssertionError("P3-A did not expose the three default jury profiles")
    response = client.post(
        "/simulations",
        json={
            "document_id": document_id,
            "jury_profile_id": profiles[1]["id"],
            "planned_duration_minutes": 15,
        },
    )
    response.raise_for_status()
    simulation = response.json()
    if simulation["status"] != "DRAFT" or simulation["question_count"] != 12:
        raise AssertionError("P3-A did not freeze a valid draft simulation")
    response = client.put(
        f"/simulations/{simulation['id']}/calibration",
        json={"camera_ready": True, "microphone_ready": True, "vision_ready": False},
    )
    response.raise_for_status()
    if response.json()["status"] != "DRAFT":
        raise AssertionError("Partial calibration must remain DRAFT")
    response = client.put(
        f"/simulations/{simulation['id']}/calibration",
        json={"camera_ready": True, "microphone_ready": True, "vision_ready": True},
    )
    response.raise_for_status()
    ready = response.json()
    if ready["status"] != "READY":
        raise AssertionError("Complete calibration did not transition to READY")
    print(
        json.dumps(
            {
                "simulation_id": ready["id"],
                "document_id": document_id,
                "jury_profile": ready["jury_profile"]["name"],
                "question_count": ready["question_count"],
                "planned_duration_minutes": ready["planned_duration_minutes"],
                "camera_ready": ready["camera_ready"],
                "microphone_ready": ready["microphone_ready"],
                "vision_ready": ready["vision_ready"],
                "status": ready["status"],
            },
            ensure_ascii=False,
        )
    )
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
