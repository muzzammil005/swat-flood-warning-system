/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response schema for a community report.
 */
export type CommunityReportResponse = {
    id: string;
    zone_id: string;
    report_type: string;
    description: string;
    reporter_name?: (string | null);
    reporter_phone?: (string | null);
    latitude?: (number | null);
    longitude?: (number | null);
    submitted_at: string;
    status: string;
    admin_notes?: (string | null);
};

