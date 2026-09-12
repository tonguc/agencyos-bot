import { NextRequest } from "next/server";

export async function GET(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const key = process.env.NEXT_PUBLIC_API_KEY;
  if (!key || request.headers.get("X-API-Key") !== key) {
    return new Response("Yetkisiz istek", { status: 401 });
  }
  const { id } = await context.params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    return new Response("Geçersiz teklif", { status: 400 });
  }
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) return new Response("PDF servisi yapılandırılmadı", { status: 503 });
  try {
    const response = await fetch(`${base}/api/proposals/${id}/pdf`, {
      headers: { "X-API-Key": key }, cache: "no-store", signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) return new Response("PDF alınamadı", { status: response.status });
    return new Response(response.body, {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="teklif-${id.slice(0, 8)}.pdf"`,
        "Cache-Control": "private, no-store",
      },
    });
  } catch {
    return new Response("PDF servisine ulaşılamadı", { status: 502 });
  }
}
