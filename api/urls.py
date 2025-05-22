from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserTypeViewSet, BuyerViewSet, SellerViewSet, ApiRoot, OAuthCallbackView, OAuthRedirectView

router = DefaultRouter()
router.register(r'user-type', UserTypeViewSet, basename='user-type')
router.register(r'buyers', BuyerViewSet, basename='buyers')
router.register(r'sellers', SellerViewSet, basename='sellers')

urlpatterns = [
    path('', include(router.urls)),
path('', ApiRoot.as_view(), name='api-root'),
    path('oauth/redirect/', OAuthRedirectView.as_view(), name='oauth-redirect'),
    path('oauth/callback/', OAuthCallbackView.as_view(), name='oauth-callback'),
]