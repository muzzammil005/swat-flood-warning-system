/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CommunityReportCreateRequest } from '../models/CommunityReportCreateRequest';
import type { CommunityReportListResponse } from '../models/CommunityReportListResponse';
import type { CommunityReportResponse } from '../models/CommunityReportResponse';
import type { CommunityReportUpdateRequest } from '../models/CommunityReportUpdateRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CommunityReportsService {
    /**
     * Submit Report
     * Submit a community report.
     *
     * Accepts either zone_id or lat/lon coordinates.
     * If coordinates provided, finds nearest zone.
     *
     * TODO: Add auth, move to use-cases layer, add proper error handling.
     * @param requestBody
     * @returns CommunityReportResponse Successful Response
     * @throws ApiError
     */
    public static submitReportApiReportsPost(
        requestBody: CommunityReportCreateRequest,
    ): CancelablePromise<CommunityReportResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/reports/',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Reports
     * Get community reports with composable optional filtering.
     *
     * Filters compose: ``status=approved&zone_id=X`` returns approved reports in X.
     * No filters returns all reports (unbounded — caller should paginate in future).
     *
     * Used for moderation list and official view.
     *
     * TODO: Add auth, move to use-cases layer, add proper error handling, add pagination.
     * @param status
     * @param zoneId
     * @returns CommunityReportListResponse Successful Response
     * @throws ApiError
     */
    public static getReportsApiReportsGet(
        status?: (string | null),
        zoneId?: (string | null),
    ): CancelablePromise<CommunityReportListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/reports/',
            query: {
                'status': status,
                'zone_id': zoneId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit Report
     * Submit a community report.
     *
     * Accepts either zone_id or lat/lon coordinates.
     * If coordinates provided, finds nearest zone.
     *
     * TODO: Add auth, move to use-cases layer, add proper error handling.
     * @param requestBody
     * @returns CommunityReportResponse Successful Response
     * @throws ApiError
     */
    public static submitReportApiReportsPost1(
        requestBody: CommunityReportCreateRequest,
    ): CancelablePromise<CommunityReportResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/reports',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Reports
     * Get community reports with composable optional filtering.
     *
     * Filters compose: ``status=approved&zone_id=X`` returns approved reports in X.
     * No filters returns all reports (unbounded — caller should paginate in future).
     *
     * Used for moderation list and official view.
     *
     * TODO: Add auth, move to use-cases layer, add proper error handling, add pagination.
     * @param status
     * @param zoneId
     * @returns CommunityReportListResponse Successful Response
     * @throws ApiError
     */
    public static getReportsApiReportsGet1(
        status?: (string | null),
        zoneId?: (string | null),
    ): CancelablePromise<CommunityReportListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/reports',
            query: {
                'status': status,
                'zone_id': zoneId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Report Status
     * Approve or reject a pending report.
     *
     * Requires admin JWT.
     * @param reportId
     * @param requestBody
     * @returns CommunityReportResponse Successful Response
     * @throws ApiError
     */
    public static updateReportStatusApiReportsReportIdPatch(
        reportId: string,
        requestBody: CommunityReportUpdateRequest,
    ): CancelablePromise<CommunityReportResponse> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/reports/{report_id}',
            path: {
                'report_id': reportId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
