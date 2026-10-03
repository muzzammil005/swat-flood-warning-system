/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AlertListResponse } from '../models/AlertListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AlertsService {
    /**
     * Get Alerts
     * Get most recent 20 alerts across all zones, newest first.
     * @returns AlertListResponse Successful Response
     * @throws ApiError
     */
    public static getAlertsApiAlertsGet(): CancelablePromise<Array<AlertListResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/alerts/',
        });
    }
    /**
     * Get Alerts
     * Get most recent 20 alerts across all zones, newest first.
     * @returns AlertListResponse Successful Response
     * @throws ApiError
     */
    public static getAlertsApiAlertsGet1(): CancelablePromise<Array<AlertListResponse>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/alerts',
        });
    }
}
