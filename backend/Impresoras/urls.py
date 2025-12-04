# impresoras/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# Registrar todos los ViewSets
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'user-profiles', views.UserProfileViewSet, basename='userprofile')
router.register(r'printers', views.PrinterViewSet, basename='printer')
router.register(r'user-printer-assignments', views.UserPrinterAssignmentViewSet, basename='userprinterassignment')
router.register(r'pricing-configs', views.PricingConfigViewSet, basename='pricingconfig')
router.register(r'user-pricing-profiles', views.UserPricingProfileViewSet, basename='userpricingprofile')
router.register(r'print-jobs', views.PrintJobViewSet, basename='printjob')
router.register(r'system-logs', views.SystemLogViewSet, basename='systemlog')

# URLs adicionales
urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('auth/register/', views.UserRegistrationView.as_view(), name='user-registration'),
]