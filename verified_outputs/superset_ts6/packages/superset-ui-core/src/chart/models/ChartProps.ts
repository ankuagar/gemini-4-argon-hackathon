/**
 * packages/superset-ui-core/src/chart/models/ChartProps.ts
 */
import {
  type QueryFormData,
  type ExtraFormData,
  normalizeMetricLabel,
} from '../../query/types/QueryFormData.js';

export interface DatasourceColumn {
  column_name: string;
  verbose_name?: string;
  type: string;
  is_dttm?: boolean;
}

export interface RawDatasource {
  id: number;
  type: 'table' | 'query';
  columns: DatasourceColumn[];
  column_formats?: Record<string, string>;
}

export interface ChartPropsConfig {
  width?: number;
  height?: number;
  formData: QueryFormData;
  datasource: RawDatasource;
  queriesData: Array<{
    data: Array<Record<string, unknown>>;
    colnames?: string[];
  }>;
  filterState?: {
    value?: unknown;
    selectedValues?: string[];
  };
}

export class ChartProps {
  readonly width: number;
  readonly height: number;
  readonly formData: QueryFormData;
  readonly datasource: RawDatasource;
  readonly queriesData: ChartPropsConfig['queriesData'];
  readonly filterState?: {
    value?: unknown;
    selectedValues?: string[];
  };

  constructor(config: ChartPropsConfig) {
    this.width = config.width ?? 800;
    this.height = config.height ?? 600;
    this.formData = config.formData;
    this.datasource = config.datasource;
    this.queriesData = config.queriesData;
    if (config.filterState !== undefined) {
      this.filterState = config.filterState;
    }
  }

  getPrimaryMetricLabel(): string {
    const firstMetric = this.formData.metrics[0];
    return firstMetric !== undefined ? normalizeMetricLabel(firstMetric) : '';
  }

  getFirstQueryRows(): Array<Record<string, unknown>> {
    return this.queriesData[0]?.data ?? [];
  }

  withExtraFormData(extra: ExtraFormData): ChartProps {
    return new ChartProps({
      width: this.width,
      height: this.height,
      datasource: this.datasource,
      queriesData: this.queriesData,
      ...(this.filterState !== undefined ? { filterState: this.filterState } : {}),
      formData: {
        ...this.formData,
        extra_form_data: extra,
      },
    });
  }
}
