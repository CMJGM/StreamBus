from django.shortcuts import render
from StreamBus.logging_mixins import LoggingMixin, DetailedLoggingMixin, log_view, log_view_detailed

@log_view
def index(request):
    params = {}    
    return render(request,"base.html", params)
