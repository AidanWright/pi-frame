from fastapi import APIRouter

router = APIRouter()


@router.get("/api/status")
def status():
    return {"status": "ok"}
