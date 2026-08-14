from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import (
    CollectorRunHistoryRead,
    CollectorRunRead,
    CollectorRunStatus,
    CollectorTrigger,
)
from app.services.collector_runs import (
    execute_collector_run,
    list_collector_runs,
)
from app.services.collectors.la_bonne_alternance import (
    CollectorAPIError,
    CollectorConfigurationError,
)


router = APIRouter(
    prefix="/collectors",
    tags=["Collectors"],
)


@router.get(
    "/runs",
    response_model=list[CollectorRunHistoryRead],
)
def get_collector_runs(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    trigger: CollectorTrigger | None = Query(
        default=None,
    ),
    status: CollectorRunStatus | None = Query(
        default=None,
    ),
    db: Session = Depends(get_db),
) -> list:
    return list_collector_runs(
        db,
        limit=limit,
        trigger=trigger,
        status=status,
    )


@router.post(
    "/la-bonne-alternance/run",
    response_model=CollectorRunRead,
)
def run_la_bonne_alternance_collector(
    db: Session = Depends(get_db),
) -> CollectorRunRead:
    try:
        _, result = execute_collector_run(
            db,
            trigger="manual",
        )
    except CollectorConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "La Bonne Alternance API key "
                "is not configured"
            ),
        ) from error
    except CollectorAPIError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "La Bonne Alternance API "
                "is unavailable"
            ),
        ) from error

    return CollectorRunRead(
        found=result.found,
        added=result.added,
        duplicates=result.duplicates,
        errors=result.errors,
    )