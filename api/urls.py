from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkerViewSet, OwnerViewSet, AssignmentViewSet, PaymentViewSet, ReportViewSet
from .auth_views import login_view, logout_view, me_view, register_view

router = DefaultRouter()
router.register(r'workers', WorkerViewSet, basename='worker')
router.register(r'owners', OwnerViewSet, basename='owner')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    path('daily-report/', ReportViewSet.as_view({'get': 'list'}), name='daily-report'),
    # Auth
    path('auth/login/', login_view, name='auth-login'),
    path('auth/logout/', logout_view, name='auth-logout'),
    path('auth/me/', me_view, name='auth-me'),
    path('auth/register/', register_view, name='auth-register'),
]
