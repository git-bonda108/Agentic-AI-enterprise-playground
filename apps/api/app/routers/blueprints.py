from fastapi import APIRouter, Depends, HTTPException

from app.agents.core import REGISTRY
from app.agents.data import dataset_catalog
from app.agents.registry import all_blueprints
from app.auth import current_user
from app.catalog_store import get_entry, manifest_for

router = APIRouter(prefix="/v1/blueprints", tags=["blueprints"])
data_router = APIRouter(prefix="/v1/data", tags=["data"])


@router.get("")
def list_blueprints(_=Depends(current_user)) -> dict:
    return {"blueprints": all_blueprints()}


@router.get("/{blueprint_id}")
def get_blueprint(blueprint_id: str, _=Depends(current_user)) -> dict:
    bp = REGISTRY.get(blueprint_id)
    if bp is not None and bp.family != "Runtime":
        return bp.manifest()
    entry = get_entry(blueprint_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Unknown blueprint")
    return manifest_for(entry)


@data_router.get("")
def list_datasets(_=Depends(current_user)) -> dict:
    return {"datasets": dataset_catalog()}
