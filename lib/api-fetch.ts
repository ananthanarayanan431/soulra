// lib/api-fetch.ts
// Wraps `fetch` to attach the current Clerk session token as a Bearer header,
// working in both Server Components/route handlers and Client Components.

declare global {
  interface Window {
    Clerk?: {
      session?: { getToken: () => Promise<string | null> } | null;
    };
  }
}

async function getAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    const { auth } = await import("@clerk/nextjs/server");
    const session = await auth();
    return session.getToken();
  }
  const clerk = window.Clerk;
  if (!clerk?.session) return null;
  return clerk.session.getToken();
}

export async function authedFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = await getAuthToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}
