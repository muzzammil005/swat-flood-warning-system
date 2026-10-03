/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CommunityReportResponse } from './CommunityReportResponse';
/**
 * Response schema for list of community reports.
 */
export type CommunityReportListResponse = {
    reports: Array<CommunityReportResponse>;
    reports_by_zone?: (Record<string, Array<CommunityReportResponse>> | null);
};

