from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkerViewSet, OwnerViewSet, AssignmentViewSet, PaymentViewSet, ReportViewSet

router = DefaultRouter()
router.register(r'workers', WorkerViewSet, basename='worker')
router.register(r'owners', OwnerViewSet, basename='owner')
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    path('', include(router.urls)),
    path('daily-report/', ReportViewSet.as_view({'get': 'list'}), name='daily-report'),
]
