/**
 * packages/superset-ui-core/src/chart/models/ChartProps.ts
 */
import { normalizeMetricLabel, } from '../../query/types/QueryFormData.js';
export class ChartProps {
    width;
    height;
    formData;
    datasource;
    queriesData;
    filterState;
    constructor(config) {
        this.width = config.width ?? 800;
        this.height = config.height ?? 600;
        this.formData = config.formData;
        this.datasource = config.datasource;
        this.queriesData = config.queriesData;
        if (config.filterState !== undefined) {
            this.filterState = config.filterState;
        }
    }
    getPrimaryMetricLabel() {
        const firstMetric = this.formData.metrics[0];
        return firstMetric !== undefined ? normalizeMetricLabel(firstMetric) : '';
    }
    getFirstQueryRows() {
        return this.queriesData[0]?.data ?? [];
    }
    withExtraFormData(extra) {
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
