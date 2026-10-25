/**
 * packages/superset-ui-chart-controls/src/shared-controls/components/ColumnConfigControl.ts
 */
import { ChartProps } from '../../../../superset-ui-core/src/chart/models/ChartProps.js';
export function resolveColumnConfigs(chartProps, overrides = {}) {
    const columns = chartProps.datasource.columns;
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
export function getPrimaryColumnSpec(chartProps, overrides) {
    const specs = resolveColumnConfigs(chartProps, overrides);
    const first = specs[0];
    if (!first) {
        throw new Error('No columns available in datasource');
    }
    return first;
}
