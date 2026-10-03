import uuid
from datetime import UTC, datetime
from dataclasses import dataclass

from application.ports.repositories import CommunityReportRepository, ZoneRepository
from domain.entities.community_report import CommunityReport
from domain.exceptions import DomainError, ReportNotFoundError, ZoneNotFoundError


@dataclass(frozen=True)
class CommunityReportListResult:
    """Result of listing reports."""
    reports: list[CommunityReport]
    reports_by_zone: dict[str, list[CommunityReport]] | None = None


class ReportUseCases:
    """Use cases for community report submission and moderation."""

    def __init__(
        self,
        report_repo: CommunityReportRepository,
        zone_repo: ZoneRepository,
    ):
        self.report_repo = report_repo
        self.zone_repo = zone_repo

    async def submit_report(
        self,
        report_type: str,
        description: str,
        zone_id: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> CommunityReport:
        """Submit a new community report.
        
        If zone_id is missing but lat/lon are provided, finds the nearest zone.
        """
        resolved_zone_id = zone_id

        if not resolved_zone_id and latitude is not None and longitude is not None:
            nearest_zone = await self.zone_repo.find_nearest(latitude, longitude)
            if not nearest_zone:
                raise DomainError("No zones found near provided coordinates.")
            resolved_zone_id = nearest_zone.id

        if not resolved_zone_id:
            raise DomainError("Either zone_id or latitude/longitude must be provided.")

        observation = f"[{report_type}] {description}"
        report = CommunityReport(
            id=f"report-{uuid.uuid4()}",
            zone_id=resolved_zone_id,
            observation=observation,
            status="Pending",
            submitted_at=datetime.now(UTC),
        )

        return await self.report_repo.add(report)

    async def list_reports(
        self,
        status: str | None = None,
        zone_id: str | None = None,
    ) -> CommunityReportListResult:
        """List community reports with optional filtering."""
        if status:
            status = status.strip().capitalize()
            if status not in ("Pending", "Approved", "Rejected"):
                raise DomainError(f"Invalid status '{status}'. Must be pending, approved, or rejected.")
        
        reports = await self.report_repo.list_with_filters(status=status, zone_id=zone_id)
        
        status_is_approved = (status is not None) and (status.lower() == "approved")
        reports_by_zone = None
        
        if status_is_approved:
            reports_by_zone = {}
            for report in reports:
                if report.zone_id not in reports_by_zone:
                    reports_by_zone[report.zone_id] = []
                reports_by_zone[report.zone_id].append(report)
                
        return CommunityReportListResult(
            reports=reports,
            reports_by_zone=reports_by_zone,
        )

    async def moderate_report(
        self,
        report_id: str,
        new_status: str,
    ) -> CommunityReport:
        """Approve or reject a pending report."""
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            raise ReportNotFoundError(report_id)
            
        if report.status != "Pending":
            raise DomainError(f"Report is already {report.status.lower()}.")
            
        return await self.report_repo.update_status(report, new_status=new_status)
