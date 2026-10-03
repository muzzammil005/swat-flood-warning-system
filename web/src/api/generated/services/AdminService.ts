/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CreateUserRequest } from '../models/CreateUserRequest';
import type { OverrideRequest } from '../models/OverrideRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminService {
    /**
     * Create Manual Override
     * Force a zone's displayed risk tier.
     *
     * The most-recent override for a zone is treated as 'active'.
     * Requires admin JWT.
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createManualOverrideApiAdminOverridesPost(
        requestBody: OverrideRequest,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/overrides',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * List Overrides
     * List manual overrides for a zone, most recent first.
     *
     * Requires admin JWT.
     * @param zoneId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listOverridesApiAdminOverridesGet(
        zoneId: string,
    ): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/overrides',
            query: {
                'zone_id': zoneId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Resource Centers
     * Return all resource centers with their inventory.
     *
     * Public endpoint — used by the 'Active Relief Centers' dashboard panel.
     * No auth required.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getResourceCentersApiResourceCentersGet(): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/resource-centers',
        });
    }
    /**
     * List Users
     * List all users without password_hash.
     *
     * Requires admin JWT.
     * @returns any Successful Response
     * @throws ApiError
     */
    public static listUsersApiAdminUsersGet(): CancelablePromise<Array<Record<string, any>>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/admin/users',
        });
    }
    /**
     * Create User
     * Create a new operator account.
     *
     * Rejects duplicate usernames with HTTP 400.
     * Requires admin JWT.
     * @param requestBody
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createUserApiAdminUsersPost(
        requestBody: CreateUserRequest,
    ): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/admin/users',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
