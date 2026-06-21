function authHeader(credentials) {
    if (!credentials) return {};
    const b64 = btoa(`${credentials.username}:${credentials.password}`);
    return { Authorization: `Basic ${b64}` };
}

export async function fetchAstLog(credentials) {
    const res = await fetch('/sompyle/astlog', {
        headers: authHeader(credentials),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.text();
}

export async function fetchScoreText(credentials) {
    const res = await fetch('/sompyle/score.spls', {
        headers: authHeader(credentials),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.text();
}

export async function putScoreText(text, credentials) {
    const res = await fetch('/sompyle/score.spls', {
        method: 'PUT',
        headers: {
            ...authHeader(credentials),
            'Content-Type': 'text/yaml',
        },
        body: text,
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res;
}

export async function fetchStatus(credentials) {
    const res = await fetch('/sompyle/status.json', {
        headers: authHeader(credentials),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
}
