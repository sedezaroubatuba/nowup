"""PWA: uses the existing session and notification worker; no database changes."""
from fastapi import Request
from fastapi.responses import RedirectResponse

def register(app, current_user):
    @app.get('/app', include_in_schema=False)
    def pwa_entry(request: Request):
        user = current_user(request)
        destination = '/entrar?pwa=1'
        if user:
            destination = {'professional': '/painel', 'admin': '/admin'}.get(user['role'], '/cliente')
        return RedirectResponse(destination, status_code=303, headers={'Cache-Control': 'no-store'})
