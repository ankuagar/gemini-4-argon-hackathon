/**
 * packages/superset-ui-core/src/connection/SupersetClientClass.ts
 */
import { QueryFormData, AdhocFilter } from '../query/types/QueryFormData.js';

export interface ClientConfig {
  protocol?: 'http:' | 'https:';
  host?: string;
  appRoot?: string;
  csrfToken?: string;
  timeoutMs?: number;
}

export interface RequestConfig {
  endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  body?: unknown;
  searchParams?: Record<string, string | number | undefined>;
}

export interface SupersetApiResponse<T = unknown> {
  status: number;
  json: T;
  headers: Record<string, string>;
  errorMessage?: string;
}

export class SupersetClientClass {
  private readonly baseUrl: string;
  private readonly csrfToken?: string;
  private readonly timeoutMs: number;
  private readonly mockRoutes: Map<string, (req: RequestConfig) => unknown>;

  constructor(config: ClientConfig = {}) {
    const protocol = config.protocol ?? 'https:';
    const host = config.host ?? 'localhost:8088';
    const appRoot = config.appRoot ?? '';
    this.baseUrl = `${protocol}//${host}${appRoot}`;
    // Breaks exactOptionalPropertyTypes if config.csrfToken is undefined
    this.csrfToken = config.csrfToken;
    this.timeoutMs = config.timeoutMs ?? 30000;
    this.mockRoutes = new Map();
  }

  registerEndpoint(endpoint: string, handler: (req: RequestConfig) => unknown): void {
    this.mockRoutes.set(endpoint, handler);
  }

  buildUrl(endpoint: string, searchParams?: Record<string, string | number | undefined>): string {
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${this.baseUrl}${cleanEndpoint}`;
    if (!searchParams) {
      return url;
    }
    const pairs: string[] = [];
    for (const [key, val] of Object.entries(searchParams)) {
      if (val !== undefined) {
        pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(val))}`);
      }
    }
    return pairs.length > 0 ? `${url}?${pairs.join('&')}` : url;
  }

  async request<T>(config: RequestConfig): Promise<SupersetApiResponse<T>> {
    const headers: Record<string, string> = {
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
          json: null as T,
          headers,
          errorMessage: `No route registered for ${config.endpoint}`,
        };
      }
      const payload = handler({ ...config, headers }) as T;
      return {
        status: 200,
        json: payload,
        headers,
      };
    } catch (err) {
      // Breaks useUnknownInCatchVariables in TS 6: err is unknown, not Error
      return {
        status: 500,
        json: null as T,
        headers,
        errorMessage: err.message || 'Internal client error',
      };
    }
  }

  async postChartData(formData: QueryFormData): Promise<SupersetApiResponse<{
    result: Array<{ data: Record<string, unknown>[]; applied_filters: string[] }>;
  }>> {
    const baseFilters: AdhocFilter[] = formData.adhoc_filters ?? [];
    const extraFilters: AdhocFilter[] = formData.extra_form_data?.filters ?? [];
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
        form_data_key: formData.url_params?.form_data_key,
      },
    });
  }
}
