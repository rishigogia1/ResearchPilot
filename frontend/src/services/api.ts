import type {
  ApiErrorResponse,
  HealthResponse,
  ResearchRequest,
  ResearchResponse,
} from '../types/research';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

export class ApiClientError extends Error {
  status: number;
  code: string;
  details?: unknown;
  requestId?: string;

  constructor(status: number, message: string, code = 'API_ERROR', details?: unknown, requestId?: string) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

/**
 * Parse structured error payload from response or fallback to status message.
 */
async function parseErrorResponse(response: Response): Promise<ApiClientError> {
  const status = response.status;
  const requestId = response.headers.get('X-Request-ID') || undefined;

  try {
    const data = (await response.json()) as ApiErrorResponse;
    if (data && data.error) {
      return new ApiClientError(
        status,
        data.error.message || `Request failed with status ${status}`,
        data.error.code || 'HTTP_ERROR',
        data.error.details,
        requestId || data.error.request_id
      );
    }
  } catch {
    // Non-JSON response
  }

  // Fallback human-friendly messages based on status code
  let fallbackMessage = `Server returned status ${status}`;
  let code = 'HTTP_ERROR';

  if (status === 422) {
    fallbackMessage = 'The research query was invalid. Please ensure it contains between 3 and 1000 characters.';
    code = 'VALIDATION_ERROR';
  } else if (status === 502) {
    fallbackMessage = 'An external service provider (LLM or search tool) failed to respond.';
    code = 'UPSTREAM_FAILURE';
  } else if (status === 503) {
    fallbackMessage = 'Required external API credentials (OpenAI or Tavily) are unconfigured in backend/.env.';
    code = 'MISSING_CREDENTIALS';
  } else if (status === 504) {
    fallbackMessage = 'Research execution timed out while querying sources.';
    code = 'WORKFLOW_TIMEOUT';
  }

  return new ApiClientError(status, fallbackMessage, code, undefined, requestId);
}

/**
 * Submit research query to backend.
 */
export async function submitResearch(request: ResearchRequest): Promise<ResearchResponse> {
  let response: Response;

  try {
    response = await fetch(`${BASE_URL}/api/v1/research`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
  } catch (err) {
    throw new ApiClientError(
      0,
      `Cannot connect to backend server at ${BASE_URL}. Ensure the FastAPI server is running on port 8000.`,
      'NETWORK_ERROR',
      err
    );
  }

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  try {
    const data = (await response.json()) as ResearchResponse;
    return data;
  } catch (parseErr) {
    throw new ApiClientError(
      response.status,
      'Received an invalid response format from backend.',
      'PARSE_ERROR',
      parseErr
    );
  }
}

/**
 * Retrieve system health status.
 */
export async function getHealth(): Promise<HealthResponse> {
  let response: Response;

  try {
    response = await fetch(`${BASE_URL}/api/v1/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (err) {
    throw new ApiClientError(
      0,
      `Backend is unreachable at ${BASE_URL}.`,
      'BACKEND_OFFLINE',
      err
    );
  }

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  return (await response.json()) as HealthResponse;
}
