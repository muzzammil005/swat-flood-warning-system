/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request schema for updating a report status.
 */
export type CommunityReportUpdateRequest = {
    /**
     * New status: Approved or Rejected
     */
    status: string;
    /**
     * Optional admin notes
     */
    admin_notes?: (string | null);
};

