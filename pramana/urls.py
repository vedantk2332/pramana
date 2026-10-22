"""
Pramana App URL Routing.
"""

from django.urls import path
from pramana import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('api/status/', views.system_status_view, name='api_status'),
    path('api/learn/explain/', views.learn_explain_view, name='api_learn_explain'),
    path('api/debug/analyze/', views.debug_analyze_view, name='api_debug_analyze'),
    path('api/verify/', views.verify_code_view, name='api_verify'),
    path('api/rag/upload/', views.rag_upload_view, name='api_rag_upload'),
    path('api/rag/documents/', views.rag_documents_view, name='api_rag_documents'),
    path('api/rag/clear/', views.rag_clear_view, name='api_rag_clear'),
    path('api/rag/query/', views.rag_query_view, name='api_rag_query'),
    path('api/games/', views.games_list_view, name='api_games'),
    path('api/games/check/', views.games_check_view, name='api_games_check'),
]
