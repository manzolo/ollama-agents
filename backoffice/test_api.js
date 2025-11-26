const http = require('http');

const options = {
    hostname: 'localhost',
    port: 8080,
    path: '/api/agents',
    method: 'GET',
};

const req = http.request(options, (res) => {
    let data = '';

    res.on('data', (chunk) => {
        data += chunk;
    });

    res.on('end', () => {
        try {
            console.log('Response status:', res.statusCode);
            const json = JSON.parse(data);
            console.log('Parsed JSON:', Object.keys(json));

            if (!json.agents) {
                throw new Error('Missing agents property');
            }

            const agents = json.agents;
            console.log('Agents keys:', Object.keys(agents));

            Object.entries(agents).forEach(([name, agent]) => {
                console.log(`Processing ${name}...`);
                // Simulate renderAgents logic
                const status = agent.status;
                const capabilities = agent.capabilities;

                if (capabilities && capabilities.length > 0) {
                    capabilities.map(c => c).join('');
                }
                console.log(`  OK: ${name} (${status})`);
            });

            console.log('SUCCESS: Response is compatible with frontend');

        } catch (e) {
            console.error('ERROR:', e.message);
            console.error('Raw data:', data);
        }
    });
});

req.on('error', (e) => {
    console.error(`Problem with request: ${e.message}`);
});

req.end();
