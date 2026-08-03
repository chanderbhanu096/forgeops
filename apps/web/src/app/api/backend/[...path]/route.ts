import { NextRequest, NextResponse } from "next/server";

const DEFAULT_API_URL =
  "https://forgeops-staging-api.greenrock-70958585.northeurope.azurecontainerapps.io";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: {
    path: string[];
  };
};

async function proxy(request: NextRequest, { params }: RouteContext): Promise<NextResponse> {
  const apiUrl = (process.env.API_URL || DEFAULT_API_URL).replace(/\/+$/, "");
  const upstreamUrl = new URL(`${apiUrl}/${params.path.join("/")}`);
  upstreamUrl.search = request.nextUrl.search;

  const requestHeaders = new Headers(request.headers);
  requestHeaders.delete("host");
  requestHeaders.delete("content-length");
  requestHeaders.delete("accept-encoding");
  requestHeaders.delete("connection");

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  try {
    const upstreamResponse = await fetch(upstreamUrl, {
      method: request.method,
      headers: requestHeaders,
      body,
      redirect: "manual",
      cache: "no-store",
    });

    const responseHeaders = new Headers(upstreamResponse.headers);
    responseHeaders.delete("content-encoding");
    responseHeaders.delete("content-length");
    responseHeaders.delete("transfer-encoding");

    return new NextResponse(upstreamResponse.body, {
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown upstream error";
    return NextResponse.json(
      { detail: `ForgeOps API proxy failed: ${message}` },
      { status: 502 }
    );
  }
}

export {
  proxy as DELETE,
  proxy as GET,
  proxy as HEAD,
  proxy as OPTIONS,
  proxy as PATCH,
  proxy as POST,
  proxy as PUT,
};
