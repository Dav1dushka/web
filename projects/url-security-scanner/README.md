# URL Security Scanner

A small Python tool for checking a website's basic HTTP security configuration.

It looks at:

- HTTPS / TLS
- common security headers
- HTTP status code
- redirects
- server header

### Built with

Python · requests · ssl · sockets

### Run

```bash
pip install -r requirements.txt
python scanner.py https://example.com
```

This is a passive checker. It only makes normal HTTP requests and checks the response.

Only test websites you are allowed to inspect.
