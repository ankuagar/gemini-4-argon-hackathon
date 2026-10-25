/**
 * src/explore/controlUtils/getFormDataFromControls.ts
 */
import type {
  AdhocFilter,
  QueryFormData,
  QueryFormMetric,
} from '../../../packages/superset-ui-core/src/query/types/QueryFormData.js';

export interface ControlStateItem {
  type: string;
  value: unknown;
  default?: unknown;
  validationErrors?: string[];
}

export type ControlStateMapping = Record<string, ControlStateItem>;

export function getFormDataFromControls(
  controlsState: ControlStateMapping,
): QueryFormData {
  const datasourceCtrl = controlsState['datasource'];
  const datasourceVal = (datasourceCtrl?.value ??
    datasourceCtrl?.default ??
    '0__table') as string;

  const vizTypeCtrl = controlsState['viz_type'];
  const vizTypeVal = (vizTypeCtrl?.value ??
    vizTypeCtrl?.default ??
    'table') as string;

  const metricsRaw = controlsState['metrics']?.value ?? controlsState['metrics']?.default ?? [];
  const metrics = Array.isArray(metricsRaw) ? (metricsRaw as QueryFormMetric[]) : [];

  const groupbyRaw = controlsState['groupby']?.value;
  const groupby = Array.isArray(groupbyRaw) ? (groupbyRaw as string[]) : undefined;

  const filtersRaw = controlsState['adhoc_filters']?.value;
  const adhoc_filters = Array.isArray(filtersRaw) ? (filtersRaw as AdhocFilter[]) : undefined;

  const rowLimitRaw = controlsState['row_limit']?.value ?? controlsState['row_limit']?.default;
  const row_limit = typeof rowLimitRaw === 'number' ? rowLimitRaw : undefined;

  const timeRangeRaw = controlsState['time_range']?.value;
  const time_range = typeof timeRangeRaw === 'string' ? timeRangeRaw : undefined;

  return {
    datasource: datasourceVal,
    viz_type: vizTypeVal,
    metrics,
    ...(groupby !== undefined ? { groupby } : {}),
    ...(adhoc_filters !== undefined ? { adhoc_filters } : {}),
    ...(row_limit !== undefined ? { row_limit } : {}),
    ...(time_range !== undefined ? { time_range } : {}),
  };
}

export function hasControlValidationErrors(controlsState: ControlStateMapping): boolean {
  return Object.values(controlsState).some(
    (ctrl) => Boolean(ctrl.validationErrors && ctrl.validationErrors.length > 0),
  );
}
