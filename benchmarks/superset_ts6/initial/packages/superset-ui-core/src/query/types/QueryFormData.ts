/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.
 * packages/superset-ui-core/src/query/types/QueryFormData.ts
 */

export type FilterOperator = '==' | '!=' | '>' | '<' | '>=' | '<=' | 'IN' | 'NOT IN' | 'LIKE';

export interface SimpleAdhocFilter {
  expressionType: 'SIMPLE';
  subject: string;
  operator: FilterOperator;
  comparator: string | number | Array<string | number>;
  clause?: 'WHERE' | 'HAVING';
  isExtra?: boolean;
  filterOptionName?: string;
}

export interface SqlAdhocFilter {
  expressionType: 'SQL';
  sqlExpression: string;
  clause?: 'WHERE' | 'HAVING';
  isExtra?: boolean;
  filterOptionName?: string;
}

export type AdhocFilter = SimpleAdhocFilter | SqlAdhocFilter;

export interface SavedMetric {
  metric_name: string;
  expression: string;
  verbose_name?: string;
  d3format?: string;
}

export interface AdhocMetric {
  label: string;
  expressionType: 'SIMPLE' | 'SQL';
  column?: { column_name: string; type: string };
  aggregate?: 'SUM' | 'AVG' | 'COUNT' | 'MIN' | 'MAX';
  sqlExpression?: string;
}

export type QueryFormMetric = string | SavedMetric | AdhocMetric;

export interface ExtraFormData {
  filters?: AdhocFilter[];
  granularity_sqla?: string;
  time_range?: string;
  custom_form_data?: Record<string, unknown>;
}

export interface QueryFormData {
  datasource: string;
  viz_type: string;
  metrics: QueryFormMetric[];
  groupby?: string[];
  adhoc_filters?: AdhocFilter[];
  row_limit?: number;
  time_range?: string;
  extra_form_data?: ExtraFormData;
  url_params?: Record<string, string>;
}

export function normalizeMetricLabel(metric: QueryFormMetric): string {
  if (typeof metric === 'string') {
    return metric;
  }
  if ('metric_name' in metric) {
    return metric.verbose_name || metric.metric_name;
  }
  return metric.label;
}

export function createSimpleFilter(
  subject: string,
  operator: FilterOperator,
  comparator: string | number | Array<string | number>,
  clause?: 'WHERE' | 'HAVING',
  isExtra?: boolean,
): SimpleAdhocFilter {
  // Breaks exactOptionalPropertyTypes in TS 6 when clause or isExtra is undefined
  return {
    expressionType: 'SIMPLE',
    subject,
    operator,
    comparator,
    clause,
    isExtra,
    filterOptionName: `filter_${subject}_${operator}`,
  };
}
