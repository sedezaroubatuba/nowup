"""Keep existing page calls compatible with Starlette's current request-first API."""
from starlette.templating import Jinja2Templates as BaseTemplates

class Jinja2Templates(BaseTemplates):
    def TemplateResponse(self,name=None,context=None,*,request=None,**kwargs):
        context=context or {}
        return super().TemplateResponse(request=request or context['request'],name=name,context=context,**kwargs)
