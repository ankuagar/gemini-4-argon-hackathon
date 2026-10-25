/// <reference types="node" />
/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.
 * packages/superset-ui-core/src/query/types/QueryFormData.ts
 */
export const QueryFormData = {};
export function normalizeMetricLabel(metric) {
    if (typeof metric === 'string') {
        return metric;
    }
    if ('metric_name' in metric) {
        return metric.verbose_name || metric.metric_name;
    }
    return metric.label;
}
export function createSimpleFilter(subject, operator, comparator, clause, isExtra) {
    return {
        expressionType: 'SIMPLE',
        subject,
        operator,
        comparator,
        ...(clause !== undefined ? { clause } : {}),
        ...(isExtra !== undefined ? { isExtra } : {}),
        filterOptionName: `filter_${subject}_${operator}`,
    };
}
