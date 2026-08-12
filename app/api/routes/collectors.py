from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import CollectorRunRead
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
    collect_lba_offers,
)
from app.services.offer_importer import import_job_offers


router = APIRouter(
    prefix="/collectors",
    tags=["Collectors"],
)


@router.post(
    "/la-bonne-alternance/run",
    response_model=CollectorRunRead,
)
def run_la_bonne_alternance_collector(
    db: Session = Depends(get_db),
) -> CollectorRunRead:
    try:
        offers = collect_lba_offers()
    except CollectorConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail="La Bonne Alternance API key is not configured",
        ) from error
    except CollectorAPIError as error:
        raise HTTPException(
            status_code=502,
            detail="La Bonne Alternance API is unavailable",
        ) from error

    result = import_job_offers(
        db=db,
        offers=offers,
    )

    return CollectorRunRead(
        found=result.found,
        added=result.added,
        duplicates=result.duplicates,
        errors=result.errors,
    )