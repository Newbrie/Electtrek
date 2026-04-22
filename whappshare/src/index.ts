import bcrypt from 'bcryptjs';
import { SignJWT, jwtVerify } from 'jose';

const corsHeaders = {
  'Access-Control-Allow-Origin': 'https://electtrek.com/api/*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

export default {
  async fetch(request, env) {
    // ✅ Handle preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);
    const path = url.pathname;

    // ─────────────────────────────────────────────
    // 🔒 RATE LIMIT (per IP)
    // ─────────────────────────────────────────────
  //  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  //  const key = `rate:${ip}`;
  //  const count = parseInt(await env.KV.get(key)) || 0;

  //  if (count > 10) {
  //    return new Response("Too many attempts", { status: 429 });
  //  }

  //  await env.KV.put(key, String(count + 1), { expirationTtl: 60 });

    // ─────────────────────────────────────────────
    // 🔑 LOGIN
    // ─────────────────────────────────────────────
    if (request.method === 'POST' && path === '/api/login') {
      try {
        const { password } = await request.json();

        const match = await bcrypt.compare(password, env.PASSWORD_HASH);

        if (!match) {
          return new Response(JSON.stringify({ error: "Invalid password" }), {
            status: 401,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
          });
        }

        const token = await new SignJWT({ role: "user" })
          .setProtectedHeader({ alg: "HS256" })
          .setExpirationTime("1h")
          .sign(new TextEncoder().encode(env.JWT_SECRET));

        return new Response(JSON.stringify({ token }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });

      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    }

    // ─────────────────────────────────────────────
    // 🔐 AUTH MIDDLEWARE
    // ─────────────────────────────────────────────
    async function requireAuth(request) {
      const auth = request.headers.get("Authorization");
      if (!auth) return null;

      try {
        const token = auth.replace("Bearer ", "");
        const { payload } = await jwtVerify(
          token,
          new TextEncoder().encode(env.JWT_SECRET)
        );
        return payload;
      } catch {
        return null;
      }
    }

    // ─────────────────────────────────────────────
    // 🔒 PROTECTED ROUTE EXAMPLE
    // ─────────────────────────────────────────────
    if (path === "/api/protected") {
      const user = await requireAuth(request);

      if (!user) {
        return new Response("Unauthorized", {
          status: 401,
          headers: corsHeaders,
        });
      }

      return new Response(JSON.stringify({
        message: "You are authenticated",
        user
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // ─────────────────────────────────────────────
    // ❌ DEFAULT
    // ─────────────────────────────────────────────
    return new Response("Not found", {
      status: 404,
      headers: corsHeaders,
    });
  },
};
