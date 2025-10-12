/**
 * Welcome to Cloudflare Workers! This is your first worker.
 *
 * - Run `npm run dev` in your terminal to start a development server
 * - Open a browser tab at http://localhost:8787/ to see your worker in action
 * - Run `npm run deploy` to publish your worker
 *
 * Bind resources to your worker in `wrangler.jsonc`. After adding bindings, a type definition for the
 * `Env` object can be regenerated with `npm run cf-typegen`.
 *
 * Learn more at https://developers.cloudflare.com/workers/
 */
 let sharedCalendar = {};

 export default {
   async fetch(request, env, ctx) {
     const url = new URL(request.url);
     const pathname = url.pathname;

     if (request.method === "POST" && pathname === "/calendar") {
       try {
         const data = await request.json();
         sharedCalendar = data;
         return new Response(JSON.stringify({ message: "Calendar received!" }), {
           headers: { "Content-Type": "application/json" }
         });
       } catch (err) {
         return new Response("Invalid JSON", { status: 400 });
       }
     }

     if (request.method === "GET" && pathname === "/calendar") {
       return new Response(JSON.stringify(sharedCalendar), {
         headers: { "Content-Type": "application/json" }
       });
     }

     return new Response("Not Found", { status: 404 });
   }
 };
