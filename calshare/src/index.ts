

const activeUsers = new Map<string, { lastSeen: number; name: string }>();
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request: Request, env: any, ctx: ExecutionContext): Promise<Response> {
    const kv = env.KVelecttrek;

    // ✅ Handle preflight OPTIONS early
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: corsHeaders,
      });
    }

    const url = new URL(request.url);
    const path = url.pathname;


    // ───────────────────────────────────────────────
    // 🔹 POST /current-election (save calendar)
    // ───────────────────────────────────────────────
    if (request.method === "POST" && path === "/current-election") {
      try {
        const body = await request.json(); // client's update
        const newSlots = body?.calendar_plan?.plan?.slots;

        // Get existing calendar
        const raw = await env.KVelecttrek.get("calendarData");
        const existing = raw ? JSON.parse(raw) : { calendar_plan: { plan: { slots: {} } } };

        // Merge: overwrite individual slots
        for (const [key, slot] of Object.entries(newSlots)) {
          existing.calendar_plan.plan.slots[key] = slot;
        }

        await env.KVelecttrek.put("calendarData", JSON.stringify(existing));

        return new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        });
      } catch (err: any) {
        return new Response(JSON.stringify({ ok: false, error: err.message }), {
          status: 500,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        });
      }
    }


    // ───────────────────────────────────────────────
    // 🔹 GET /current-election (return calendar)
    // ───────────────────────────────────────────────
    if (request.method === "GET" && path === "/current-election") {
      try {
      const raw = await env.KVelecttrek.get("calendarData");

      if (!raw) {
        return new Response(JSON.stringify({ error: "No calendar data yet" }), {
          status: 404,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        });
      }

      const parsed = JSON.parse(raw);
      return new Response(JSON.stringify(parsed), {
        status: 200,
        headers: { "Content-Type": "application/json", ...corsHeaders },
      });

        } catch (err: any) {
      return new Response(JSON.stringify({ ok: false, error: err.message }), {
        status: 500,
        headers: { "Content-Type": "application/json", ...corsHeaders },
      });
      }

    }

    // ───────────────────────────────────────────────
    // 🔹 POST /api/user-ping (update user presence)
    // ───────────────────────────────────────────────
    if (request.method === "POST" && path === "/api/user-ping") {
      try {
        const { user_id, display_name } = await request.json();
        if (!user_id) {
          return new Response(JSON.stringify({ ok: false, error: "Missing user_id" }), {
            status: 400,
            headers: { "Content-Type": "application/json", ...corsHeaders },
          });
        }

        await env.KVelecttrek.put(
        `user:${user_id}`,
        JSON.stringify({
          lastSeen: Date.now(),
          name: display_name || user_id.slice(0, 6),
        }),
        { expirationTtl: 60 } // Expire after 60 seconds
      );

        return new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        });
      } catch (err: any) {
        return new Response(JSON.stringify({ ok: false, error: err.message }), {
          status: 500,
          headers: { "Content-Type": "application/json", ...corsHeaders },
        });
      }
    }

    // ───────────────────────────────────────────────
    // 🔹 GET /api/active-users
    // ───────────────────────────────────────────────
    if (request.method === "GET" && path === "/api/active-users") {
      try {
      const now = Date.now();

      const list = await env.KVelecttrek.list({ prefix: "user:" });
      const activeList = [];

      for (const key of list.keys) {
        const value = await env.KVelecttrek.get(key.name, "json");
        if (value) {
          activeList.push({
            id: key.name.replace("user:", ""),
            name: value.name,
          });
        }
      }

      return new Response(JSON.stringify(activeList), {
        status: 200,
        headers: { "Content-Type": "application/json", ...corsHeaders },
      });
    }  catch (err: any) {
  return new Response(JSON.stringify({ ok: false, error: err.message }), {
    status: 500,
    headers: { "Content-Type": "application/json", ...corsHeaders },
  });
}
} // ✅ CLOSE the "GET /api/active-users" if-block properly

// 🔹 Default 404
return new Response("Not found", {
status: 404,
headers: corsHeaders,
});
}
};
