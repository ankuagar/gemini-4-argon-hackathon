/**
 * src/dashboard/reducers/dashboardState.ts
 */
import {
  type AdhocFilter,
  type ExtraFormData,
  type QueryFormData,
  createSimpleFilter,
} from '../../../packages/superset-ui-core/src/query/types/QueryFormData.js';

export interface SliceEntity {
  slice_id: number;
  slice_name: string;
  viz_type: string;
  form_data: QueryFormData;
}

export interface NativeFilterValue {
  filterId: string;
  column: string;
  values: Array<string | number>;
  timeRange?: string;
}

export interface DashboardState {
  sliceEntities: Record<number, SliceEntity>;
  nativeFilters: Record<string, NativeFilterValue>;
  activeTabs: string[];
  editMode: boolean;
  lastUpdatedFilterId?: string;
}

export const DashboardState = {} as const;

export type DashboardAction =
  | { type: 'SET_EDIT_MODE'; editMode: boolean }
  | { type: 'UPSERT_NATIVE_FILTER'; filter: NativeFilterValue }
  | { type: 'CLEAR_NATIVE_FILTER'; filterId: string }
  | { type: 'SET_ACTIVE_TABS'; tabs: string[] };

export function dashboardStateReducer(
  state: DashboardState,
  action: DashboardAction,
): DashboardState {
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
      const nextFilters: Record<string, NativeFilterValue> = {};
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

export function buildEffectiveSliceFormData(
  state: DashboardState,
  sliceId: number,
): QueryFormData {
  const slice = state.sliceEntities[sliceId];
  if (!slice) {
    throw new Error(`Slice ${sliceId} not found`);
  }
  const baseFormData = slice.form_data;

  const extraFilters: AdhocFilter[] = [];
  let effectiveTimeRange: string | undefined = baseFormData.time_range;

  for (const nf of Object.values(state.nativeFilters)) {
    if (nf.values.length > 0) {
      extraFilters.push(
        createSimpleFilter(nf.column, 'IN', nf.values, 'WHERE', true),
      );
    }
    if (nf.timeRange) {
      effectiveTimeRange = nf.timeRange;
    }
  }

  const extraFormData: ExtraFormData = {
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
