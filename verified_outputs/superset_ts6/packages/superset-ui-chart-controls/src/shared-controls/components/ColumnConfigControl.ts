/**
 * packages/superset-ui-chart-controls/src/shared-controls/components/ColumnConfigControl.ts
 */
import { type DatasourceColumn, ChartProps } from '../../../../superset-ui-core/src/chart/models/ChartProps.js';

export interface ColumnConfigItem {
  visible?: boolean;
  d3NumberFormat?: string;
  alignPositiveNegative?: boolean;
  colorPositiveNegative?: boolean;
  displayWidth?: number;
}

export type ColumnConfigMap = Record<string, ColumnConfigItem>;

export interface ResolvedColumnSpec {
  name: string;
  label: string;
  type: string;
  visible: boolean;
  d3NumberFormat?: string;
  displayWidth: number;
}

export function resolveColumnConfigs(
  chartProps: ChartProps,
  overrides: ColumnConfigMap = {},
): ResolvedColumnSpec[] {
  const columns: DatasourceColumn[] = chartProps.datasource.columns;
  const formats = chartProps.datasource.column_formats ?? {};

  return columns.map((col) => {
    const override = overrides[col.column_name];
    const fallbackFormat = formats[col.column_name];
    const resolvedFormat = override?.d3NumberFormat ?? fallbackFormat;

    return {
      name: col.column_name,
      label: col.verbose_name ?? col.column_name,
      type: col.type,
      visible: override?.visible ?? true,
      ...(resolvedFormat !== undefined ? { d3NumberFormat: resolvedFormat } : {}),
      displayWidth: override?.displayWidth ?? 120,
    };
  });
}

export function getPrimaryColumnSpec(
  chartProps: ChartProps,
  overrides?: ColumnConfigMap,
): ResolvedColumnSpec {
  const specs = resolveColumnConfigs(chartProps, overrides);
  const first = specs[0];
  if (!first) {
    throw new Error('No columns available in datasource');
  }
  return first;
}
