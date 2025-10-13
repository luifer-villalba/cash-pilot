from fastapi import APIRouter

router = APIRouter()

@router.get("", summary="Healthcheck")
def healthcheck():
    return {"status": "ok"}
