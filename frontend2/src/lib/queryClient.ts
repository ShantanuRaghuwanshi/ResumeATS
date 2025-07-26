import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { getApiUrl, getSessionHeaders } from "@/lib/utils";

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    const text = (await res.text()) || res.statusText;
    throw new Error(`${res.status}: ${text}`);
  }
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response> {
  const apiUrl = getApiUrl();
  const fullUrl = url.startsWith("http") ? url : `${apiUrl}${url}`;

  const headers: Record<string, string> = {
    ...getSessionHeaders(fullUrl),
    ...(data ? { "Content-Type": "application/json" } : {}),
  };

  const res = await fetch(fullUrl, {
    method,
    headers,
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

  await throwIfResNotOk(res);
  return res;
}

export async function apiUpload(
  url: string,
  formData: FormData,
): Promise<Response> {
  const apiUrl = getApiUrl();
  const fullUrl = url.startsWith("http") ? url : `${apiUrl}${url}`;

  const headers: Record<string, string> = {
    ...getSessionHeaders(fullUrl),
  };

  const res = await fetch(fullUrl, {
    method: "POST",
    headers,
    body: formData,
    credentials: "include",
  });

  await throwIfResNotOk(res);
  return res;
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
    async ({ queryKey }) => {
      const apiUrl = getApiUrl();
      const fullUrl = `${apiUrl}/${queryKey.join("/")}` as string;
      const headers = getSessionHeaders(fullUrl);

      const res = await fetch(fullUrl, {
        headers,
        credentials: "include",
      });

      if (unauthorizedBehavior === "returnNull" && res.status === 401) {
        return null;
      }

      await throwIfResNotOk(res);
      return await res.json();
    };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }),
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: Infinity,
      retry: false,
    },
    mutations: {
      retry: false,
    },
  },
});
