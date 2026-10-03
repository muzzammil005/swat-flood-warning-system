"""Community reports router for MVP demo.

Temporary implementation calling repositories directly for demo deadline.
Will be refactored into proper use-cases layer after demo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi import Request as FastAPIRequest

from infrastructure.db.session import get_session
from interfaces.http.auth_dependencies import require_admin
from interfaces.http.rate_limiter import limiter
from interfaces.schemas.reports import (
    CommunityReportCreateRequest,
    CommunityReportListResponse,
    CommunityReportResponse,
    CommunityReportUpdateRequest,
)

router = APIRouter(prefix="/reports", tags=["community-reports"])


@router.post("", response_model=CommunityReportResponse)
@router.post("/", response_model=CommunityReportResponse)
@limiter.limit("30/minute")
@limiter.limit("2/second")
async def submit_report(
    request: FastAPIRequest,
    body: Annotated[CommunityReportCreateRequest, Body()],
) -> CommunityReportResponse:
    """Submit a community report.

    Accepts either zone_id or lat/lon coordinates.
    If coordinates provided, finds nearest zone.

    TODO: Add auth, move to use-cases layer, add proper error handling.
    """
    async with get_session() as session:
        from infrastructure.db.repositories import CommunityReportRepositoryImpl, ZoneRepositoryImpl
        from application.use_cases.reports import ReportUseCases

        use_cases = ReportUseCases(
            report_repo=CommunityReportRepositoryImpl(session),
            zone_repo=ZoneRepositoryImpl(session),
        )

        saved_report = await use_cases.submit_report(
            report_type=body.report_type,
            description=body.description,
            zone_id=body.zone_id,
            latitude=body.latitude,
            longitude=body.longitude,
        )

        await session.commit()

        return CommunityReportResponse(
            id=saved_report.id,
            zone_id=saved_report.zone_id,
            report_type=body.report_type,  # From request
            description=body.description,  # From request
            reporter_name=body.reporter_name,
            reporter_phone=body.reporter_phone,
            latitude=body.latitude,
            longitude=body.longitude,
            submitted_at=saved_report.submitted_at,
            status=saved_report.status,
            admin_notes=None,
        )


@router.get("", response_model=CommunityReportListResponse)
@router.get("/", response_model=CommunityReportListResponse)
@limiter.limit("60/minute")
@limiter.limit("5/second")
async def get_reports(
    request: FastAPIRequest,
    status: str | None = None,
    zone_id: str | None = None,
) -> CommunityReportListResponse:
    """Get community reports with composable optional filtering.

    Filters compose: ``status=approved&zone_id=X`` returns approved reports in X.
    No filters returns all reports (unbounded — caller should paginate in future).

    Used for moderation list and official view.

    TODO: Add auth, move to use-cases layer, add proper error handling, add pagination.
    """
    async with get_session() as session:
        from infrastructure.db.repositories import CommunityReportRepositoryImpl, ZoneRepositoryImpl
        from application.use_cases.reports import ReportUseCases

        use_cases = ReportUseCases(
            report_repo=CommunityReportRepositoryImpl(session),
            zone_repo=ZoneRepositoryImpl(session),
        )

        result = await use_cases.list_reports(status=status, zone_id=zone_id)

        return CommunityReportListResponse(
            reports=[CommunityReportResponse.from_entity(r) for r in result.reports],
            reports_by_zone={
                zid: [CommunityReportResponse.from_entity(r) for r in zrs]
                for zid, zrs in result.reports_by_zone.items()
            } if result.reports_by_zone is not None else None,
        )


@router.patch("/{report_id}", response_model=CommunityReportResponse)
async def update_report_status(
    report_id: str,
    request: CommunityReportUpdateRequest,
    current_user: Annotated[dict, Depends(require_admin)],
) -> CommunityReportResponse:
    """Approve or reject a pending report.
    
    Requires admin JWT.
    """
    async with get_session() as session:
        from infrastructure.db.repositories import CommunityReportRepositoryImpl, ZoneRepositoryImpl
        from application.use_cases.reports import ReportUseCases
        
        use_cases = ReportUseCases(
            report_repo=CommunityReportRepositoryImpl(session),
            zone_repo=ZoneRepositoryImpl(session),
        )
        
        updated_report = await use_cases.moderate_report(
            report_id=report_id,
            new_status=request.status,
        )
        
        await session.commit()
        
        return CommunityReportResponse.from_entity(updated_report)
