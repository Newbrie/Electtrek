import bcrypt from 'bcryptjs';

export default {
  async fetch(request, env) {
    // Allow preflight requests
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    // Handle POST login
    if (request.method === 'POST') {
      try {
        const { password } = await request.json();
        const match = await bcrypt.compare(password, env.PASSWORD_HASH);

        return new Response(JSON.stringify({ success: match }), {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
          status: 500,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        });
      }
    }

    // Fallback for other methods
    return new Response('Use POST', {
      status: 405,
      headers: {
        'Access-Control-Allow-Origin': '*',
      },
    });
  },
};
