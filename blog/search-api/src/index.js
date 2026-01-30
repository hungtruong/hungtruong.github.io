export default {
    async fetch(request, env) {
        // CORS Headers
        const corsHeaders = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        };

        if (request.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
        if (request.method !== 'POST') return new Response('Method not allowed', { status: 405 });

        // Referer Check
        const referer = request.headers.get("Referer");
        const allowedHosts = ["hung-truong.com", "localhost", "127.0.0.1"];
        const isAllowed = referer && allowedHosts.some(host => referer.includes(host));

        if (!isAllowed) {
            return new Response(JSON.stringify({ error: 'Unauthorized referer' }), {
                status: 403,
                headers: { 'Content-Type': 'application/json', ...corsHeaders }
            });
        }

        // Rate Limiting (10 requests per minute)
        const ip = request.headers.get("CF-Connecting-IP") || "anonymous";
        const kvKey = `rate_limit:${ip}`;
        const currentCount = await env.RATE_LIMITER.get(kvKey);
        const count = parseInt(currentCount || "0");

        if (count >= 10) {
            return new Response(JSON.stringify({ error: 'Too many requests' }), {
                status: 429,
                headers: { 'Content-Type': 'application/json', ...corsHeaders }
            });
        }

        await env.RATE_LIMITER.put(kvKey, (count + 1).toString(), { expirationTtl: 60 });

        try {
            const { query } = await request.json();
            if (!query) return new Response(JSON.stringify({ error: 'Query is required' }), { status: 400, headers: corsHeaders });

            // Generate vector for the user's query using qwen3-0.6b
            // Temporary test: use content index
            const INDEX_NAME = 'blog-index-content';
            const MODEL_NAME = '@cf/qwen/qwen3-embedding-0.6b';
            const { data } = await env.AI.run(MODEL_NAME, {
                text: [query],
                instruction: "Given a web search query, retrieve relevant passages that answer the query"
            });
            // Determine which index to search
            const url = new URL(request.url);
            const indexType = url.searchParams.get('index_type') || 'content'; // Default to 'content'

            let vectorIndex = env.VECTOR_INDEX_CONTENT; // Default binding
            if (indexType === 'summary') {
                vectorIndex = env.VECTOR_INDEX;
            }

            // Perform vector search
            // Use qwen3-0.6b embedding from data[0]
            const matches = await vectorIndex.query(data[0], {
                topK: 10,
                returnValues: true,
                returnMetadata: true,
            });

            return new Response(JSON.stringify(matches), { headers: { 'Content-Type': 'application/json', ...corsHeaders } });
        } catch (e) {
            return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: corsHeaders });
        }
    }
};
