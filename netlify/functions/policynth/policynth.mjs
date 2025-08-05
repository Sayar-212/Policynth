export default async (request, context) => {
  try {
    // Check method
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    // Check authorization
    const authHeader = request.headers.get('authorization');
    if (!authHeader || !authHeader.startsWith('Bearer 16bf0d621ee347f1a4b56589f04b1d3430e0b93e3a4faa109f64b4789400e9d8')) {
      return new Response('Unauthorized', { status: 401 });
    }

    // Parse request body
    const body = await request.json();
    const { documents, questions } = body;

    if (!documents || !questions || !Array.isArray(questions)) {
      return new Response('Invalid request format', { status: 400 });
    }

    // Mock processing - replace with actual logic
    const answers = questions.map(question => 
      `Mock answer for: ${question} (from document: ${documents})`
    );

    return new Response(JSON.stringify({ answers }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });

  } catch (error) {
    return new Response(JSON.stringify({ error: error.toString() }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}