export function getFormDataFromControls(controlsState) {
    const datasourceCtrl = controlsState['datasource'];
    const datasourceVal = (datasourceCtrl?.value ??
        datasourceCtrl?.default ??
        '0__table');
    const vizTypeCtrl = controlsState['viz_type'];
    const vizTypeVal = (vizTypeCtrl?.value ??
        vizTypeCtrl?.default ??
        'table');
    const metricsRaw = controlsState['metrics']?.value ?? controlsState['metrics']?.default ?? [];
    const metrics = Array.isArray(metricsRaw) ? metricsRaw : [];
    const groupbyRaw = controlsState['groupby']?.value;
    const groupby = Array.isArray(groupbyRaw) ? groupbyRaw : undefined;
    const filtersRaw = controlsState['adhoc_filters']?.value;
    const adhoc_filters = Array.isArray(filtersRaw) ? filtersRaw : undefined;
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
export function hasControlValidationErrors(controlsState) {
    return Object.values(controlsState).some((ctrl) => Boolean(ctrl.validationErrors && ctrl.validationErrors.length > 0));
}
