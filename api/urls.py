from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WorkerViewSet, OwnerViewSet, AssignmentViewSet, PaymentViewSet, ReportViewSet

router = DefaultRouter()
router.register(r'workers', WorkerViewSet)
router.register(r'owners', OwnerViewSet)
router.register(r'assignments', AssignmentViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('daily-report/', ReportViewSet.as_view({'get': 'list'}), name='daily-report'),
]
