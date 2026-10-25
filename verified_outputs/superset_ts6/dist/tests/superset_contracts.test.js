/**
 * tests/superset_contracts.test.ts
 * Verifies public package interfaces and runtime behavior across Superset packages.
 */
import assert from 'node:assert/strict';
import { createSimpleFilter, normalizeMetricLabel, QueryFormData, } from '../packages/superset-ui-core/src/query/types/QueryFormData.js';
import { SupersetClientClass } from '../packages/superset-ui-core/src/connection/SupersetClientClass.js';
import { ChartProps } from '../packages/superset-ui-core/src/chart/models/ChartProps.js';
import { resolveColumnConfigs, getPrimaryColumnSpec, } from '../packages/superset-ui-chart-controls/src/shared-controls/components/ColumnConfigControl.js';
import { DashboardState, dashboardStateReducer, buildEffectiveSliceFormData, } from '../src/dashboard/reducers/dashboardState.js';
import { getFormDataFromControls, hasControlValidationErrors, } from '../src/explore/controlUtils/getFormDataFromControls.js';
async function runTests() {
    // 1. Test QueryFormData & createSimpleFilter
    const filter1 = createSimpleFilter('country', '==', 'US');
    assert.equal(filter1.expressionType, 'SIMPLE');
    assert.equal(filter1.subject, 'country');
    assert.equal('clause' in filter1, false, 'Undefined optional properties should not be set with undefined when omitted');
    const filter2 = createSimpleFilter('revenue', '>', 1000, 'HAVING', true);
    assert.equal(filter2.clause, 'HAVING');
    assert.equal(filter2.isExtra, true);
    assert.equal(normalizeMetricLabel('count'), 'count');
    assert.equal(normalizeMetricLabel({ metric_name: 'sum__sales', expression: 'SUM(sales)', verbose_name: 'Total Sales' }), 'Total Sales');
    // 2. Test getFormDataFromControls
    const formData = getFormDataFromControls({
        datasource: { type: 'DatasourceControl', value: '7__table' },
        viz_type: { type: 'VizTypeControl', value: 'echarts_timeseries_bar' },
        metrics: { type: 'MetricsControl', value: ['count', { label: 'Rev', expressionType: 'SQL', sqlExpression: 'SUM(rev)' }] },
        row_limit: { type: 'SelectControl', value: 250 },
    });
    assert.equal(formData.datasource, '7__table');
    assert.equal(formData.viz_type, 'echarts_timeseries_bar');
    assert.equal(formData.metrics.length, 2);
    assert.equal(formData.row_limit, 250);
    assert.equal(hasControlValidationErrors({ a: { type: 'Text', value: 'x' } }), false);
    assert.equal(hasControlValidationErrors({ a: { type: 'Text', value: 'x', validationErrors: ['Required'] } }), true);
    // 3. Test ChartProps & ColumnConfigControl
    const chartProps = new ChartProps({
        formData,
        datasource: {
            id: 7,
            type: 'table',
            columns: [
                { column_name: 'country', verbose_name: 'Country', type: 'STRING' },
                { column_name: 'rev', type: 'FLOAT' },
            ],
            column_formats: { rev: '$,.2f' },
        },
        queriesData: [{ data: [{ country: 'US', rev: 500 }] }],
    });
    assert.equal(chartProps.getPrimaryMetricLabel(), 'count');
    assert.equal(chartProps.getFirstQueryRows().length, 1);
    const colSpecs = resolveColumnConfigs(chartProps, {
        country: { visible: true, displayWidth: 180 },
    });
    assert.equal(colSpecs.length, 2);
    assert.equal(getPrimaryColumnSpec(chartProps).label, 'Country');
    assert.equal(colSpecs[1]?.d3NumberFormat, '$,.2f');
    // 4. Test DashboardState reducer & cross-filtering
    let dashState = {
        sliceEntities: {
            42: {
                slice_id: 42,
                slice_name: 'Sales by Country',
                viz_type: 'echarts_timeseries_bar',
                form_data: formData,
            },
        },
        nativeFilters: {},
        activeTabs: ['TAB-1'],
        editMode: false,
    };
    dashState = dashboardStateReducer(dashState, {
        type: 'UPSERT_NATIVE_FILTER',
        filter: {
            filterId: 'NATIVE_FILTER-1',
            column: 'region',
            values: ['NA', 'EU'],
            timeRange: 'Last quarter',
        },
    });
    assert.equal(dashState.lastUpdatedFilterId, 'NATIVE_FILTER-1');
    const effectiveFormData = buildEffectiveSliceFormData(dashState, 42);
    assert.equal(effectiveFormData.time_range, 'Last quarter');
    assert.equal(effectiveFormData.extra_form_data?.filters?.length, 1);
    dashState = dashboardStateReducer(dashState, {
        type: 'CLEAR_NATIVE_FILTER',
        filterId: 'NATIVE_FILTER-1',
    });
    assert.equal(dashState.lastUpdatedFilterId, undefined);
    // 5. Test SupersetClientClass
    const client = new SupersetClientClass({ host: 'superset.internal' });
    client.registerEndpoint('/api/v1/chart/data', (req) => {
        const body = req.body;
        return {
            result: [
                {
                    data: [{ country: 'US', count: 10 }],
                    applied_filters: [`count:${body.filters.length}`],
                },
            ],
        };
    });
    const resp = await client.postChartData(effectiveFormData);
    assert.equal(resp.status, 200);
    assert.equal(resp.json.result[0]?.applied_filters[0], 'count:1');
    console.log('ALL_SUPERSET_CONTRACT_TESTS_PASSED');
}
runTests().catch((err) => {
    console.error('CONTRACT_TEST_FAILED:', err);
    process.exit(1);
});
