from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from sqlalchemy.orm import Session

from app.api.auth_dependencies import (
    get_current_admin,
)
from app.db.session import get_db
from app.models import AdminUser
from app.schemas import (
    CollectorRunHistoryRead,
    CollectorRunRead,
    CollectorRunStatus,
    CollectorTrigger,
)
from app.services.collector_runs import (
    CollectorName,
    execute_all_collector_runs,
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


def execute_manual_collector(
    db: Session,
    collector: CollectorName,
) -> CollectorRunRead:
    try:
        _, result = execute_collector_run(
            db,
            trigger="manual",
            collector=collector,
        )
    except CollectorConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error
    except CollectorAPIError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error

    return CollectorRunRead(
        found=result.found,
        added=result.added,
        duplicates=result.duplicates,
        errors=result.errors,
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
    _admin: AdminUser = Depends(
        get_current_admin,
    ),
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


@router.post(
    "/france-travail/run",
    response_model=CollectorRunRead,
)
def run_france_travail_collector(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CollectorRunRead:
    return execute_manual_collector(
        db,
        "france-travail",
    )


@router.post(
    "/jooble/run",
    response_model=CollectorRunRead,
)
def run_jooble_collector(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CollectorRunRead:
    return execute_manual_collector(db, "jooble")


@router.post(
    "/choisir-service-public/run",
    response_model=CollectorRunRead,
)
def run_choisir_service_public_collector(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CollectorRunRead:
    return execute_manual_collector(
        db,
        "choisir-service-public",
    )


@router.post(
    "/emploi-territorial/run",
    response_model=CollectorRunRead,
)
def run_emploi_territorial_collector(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CollectorRunRead:
    return execute_manual_collector(db, "emploi-territorial")


@router.post("/greenhouse/run", response_model=CollectorRunRead)
def run_greenhouse_collector(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CollectorRunRead:
    return execute_manual_collector(db, "greenhouse")


@router.post("/lever/run", response_model=CollectorRunRead)
def run_lever_collector(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CollectorRunRead:
    return execute_manual_collector(db, "lever")


@router.post(
    "/smartrecruiters/run",
    response_model=CollectorRunRead,
)
def run_smartrecruiters_collector(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CollectorRunRead:
    return execute_manual_collector(db, "smartrecruiters")


@router.post(
    "/run-all",
    response_model=CollectorRunRead,
)
def run_all_collectors(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CollectorRunRead:
    result = execute_all_collector_runs(
        db,
        trigger="manual",
    )

    return CollectorRunRead(
        found=result.found,
        added=result.added,
        duplicates=result.duplicates,
        errors=result.errors,
    )
