export class SupersetClientClass {
    baseUrl;
    csrfToken;
    timeoutMs;
    mockRoutes;
    constructor(config = {}) {
        const protocol = config.protocol ?? 'https:';
        const host = config.host ?? 'localhost:8088';
        const appRoot = config.appRoot ?? '';
        this.baseUrl = `${protocol}//${host}${appRoot}`;
        if (config.csrfToken !== undefined) {
            this.csrfToken = config.csrfToken;
        }
        this.timeoutMs = config.timeoutMs ?? 30000;
        this.mockRoutes = new Map();
    }
    registerEndpoint(endpoint, handler) {
        this.mockRoutes.set(endpoint, handler);
    }
    buildUrl(endpoint, searchParams) {
        const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
        const url = `${this.baseUrl}${cleanEndpoint}`;
        if (!searchParams) {
            return url;
        }
        const pairs = [];
        for (const [key, val] of Object.entries(searchParams)) {
            if (val !== undefined) {
                pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(val))}`);
            }
        }
        return pairs.length > 0 ? `${url}?${pairs.join('&')}` : url;
    }
    async request(config) {
        const headers = {
            'Content-Type': 'application/json',
            ...(config.headers ?? {}),
        };
        if (this.csrfToken) {
            headers['X-CSRFToken'] = this.csrfToken;
        }
        try {
            const handler = this.mockRoutes.get(config.endpoint);
            if (!handler) {
                return {
                    status: 404,
                    json: null,
                    headers,
                    errorMessage: `No route registered for ${config.endpoint}`,
                };
            }
            const payload = handler({ ...config, headers });
            return {
                status: 200,
                json: payload,
                headers,
            };
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            return {
                status: 500,
                json: null,
                headers,
                errorMessage: message || 'Internal client error',
            };
        }
    }
    async postChartData(formData) {
        const baseFilters = formData.adhoc_filters ?? [];
        const extraFilters = formData.extra_form_data?.filters ?? [];
        const mergedFilters = [...baseFilters, ...extraFilters];
        return this.request({
            endpoint: '/api/v1/chart/data',
            method: 'POST',
            body: {
                datasource: formData.datasource,
                viz_type: formData.viz_type,
                metrics: formData.metrics,
                filters: mergedFilters,
                row_limit: formData.row_limit ?? 1000,
            },
            searchParams: {
                form_data_key: formData.url_params?.['form_data_key'],
            },
        });
    }
}
