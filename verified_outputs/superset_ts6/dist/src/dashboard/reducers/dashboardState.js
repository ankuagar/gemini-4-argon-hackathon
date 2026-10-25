/**
 * src/dashboard/reducers/dashboardState.ts
 */
import { createSimpleFilter, } from '../../../packages/superset-ui-core/src/query/types/QueryFormData.js';
export const DashboardState = {};
export function dashboardStateReducer(state, action) {
    switch (action.type) {
        case 'SET_EDIT_MODE':
            return {
                ...state,
                editMode: action.editMode,
            };
        case 'UPSERT_NATIVE_FILTER':
            return {
                ...state,
                nativeFilters: {
                    ...state.nativeFilters,
                    [action.filter.filterId]: action.filter,
                },
                lastUpdatedFilterId: action.filter.filterId,
            };
        case 'CLEAR_NATIVE_FILTER': {
            const nextFilters = {};
            for (const [id, val] of Object.entries(state.nativeFilters)) {
                if (id !== action.filterId) {
                    nextFilters[id] = val;
                }
            }
            const { lastUpdatedFilterId: _removed, ...restState } = state;
            return {
                ...restState,
                nativeFilters: nextFilters,
            };
        }
        case 'SET_ACTIVE_TABS':
            return {
                ...state,
                activeTabs: action.tabs,
            };
    }
}
export function buildEffectiveSliceFormData(state, sliceId) {
    const slice = state.sliceEntities[sliceId];
    if (!slice) {
        throw new Error(`Slice ${sliceId} not found`);
    }
    const baseFormData = slice.form_data;
    const extraFilters = [];
    let effectiveTimeRange = baseFormData.time_range;
    for (const nf of Object.values(state.nativeFilters)) {
        if (nf.values.length > 0) {
            extraFilters.push(createSimpleFilter(nf.column, 'IN', nf.values, 'WHERE', true));
        }
        if (nf.timeRange) {
            effectiveTimeRange = nf.timeRange;
        }
    }
    const extraFormData = {
        filters: extraFilters,
        ...(effectiveTimeRange !== undefined ? { time_range: effectiveTimeRange } : {}),
    };
    const { time_range: _baseTimeRange, ...restFormData } = baseFormData;
    return {
        ...restFormData,
        ...(effectiveTimeRange !== undefined ? { time_range: effectiveTimeRange } : {}),
        extra_form_data: extraFormData,
    };
}
