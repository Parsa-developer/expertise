# Create your views here.

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.urls import reverse
from .models import User, BuyerProfile, SellerProfile
from .serializers import UserSerializer, BuyerProfileSerializer, SellerProfileSerializer
import logging
import requests
from django.conf import settings
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

class ApiRoot(APIView):
    """
    نقطه شروع API
    """
    def get(self, request, format=None):
        return Response({
            'welcome': 'به API خرید و فروش خوش آمدید',
            'oauth': reverse('oauth-redirect', request=request, format=format),
        })

class OAuthRedirectView(APIView):
    """
    ریدایرکت به OAuth دیوار
    """
    def get(self, request, format=None):
        # استفاده از تنظیمات از فایل settings
        oauth_url = settings.OAUTH2_AUTH_URL
        client_id = settings.OAUTH2_CLIENT_ID
        redirect_uri = request.build_absolute_uri(reverse('oauth-callback'))
        
        # ایجاد یک state تصادفی با طول کافی (حداقل ۸ کاراکتر)
        import secrets
        state = secrets.token_hex(16)  # ۳۲ کاراکتر هگزادسیمال
        
        # ذخیره state در session برای بررسی در کالبک
        request.session['oauth_state'] = state
        
        # طبق مستندات دیوار، اسکوپ را خالی می‌گذاریم یا از اسکوپ‌های مجاز استفاده می‌کنیم
        # برای دریافت refresh_token می‌توانیم از offline_access استفاده کنیم
        scope = "offline_access"
        
        # ساخت URL با پارامترهای لازم
        auth_url = f"{oauth_url}?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&state={state}&scope={scope}"
        return Response({"auth_url": auth_url})

class OAuthCallbackView(APIView):
    """
    کالبک OAuth دیوار
    """
    def get(self, request, format=None):
        code = request.query_params.get('code')
        state = request.query_params.get('state')
        
        # بررسی خطا
        error = request.query_params.get('error')
        error_description = request.query_params.get('error_description')
        if error:
            logger.error(f"خطای OAuth: {error} - {error_description}")
            return Response({"error": error, "error_description": error_description}, status=status.HTTP_400_BAD_REQUEST)
        
        # بررسی کد و state
        if not code:
            return Response({"error": "کد دریافت نشد"}, status=status.HTTP_400_BAD_REQUEST)
        
        # بررسی state برای جلوگیری از حملات CSRF
        stored_state = request.session.get('oauth_state')
        if not state or state != stored_state:
            return Response({"error": "state نامعتبر است"}, status=status.HTTP_400_BAD_REQUEST)
        
        # حذف state از session پس از استفاده
        if 'oauth_state' in request.session:
            del request.session['oauth_state']
        
        # استفاده از تنظیمات از فایل settings
        token_url = settings.OAUTH2_TOKEN_URL
        client_id = settings.OAUTH2_CLIENT_ID
        client_secret = settings.OAUTH2_CLIENT_SECRET
        redirect_uri = request.build_absolute_uri(reverse('oauth-callback'))
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri
        }
        
        # در محیط واقعی، این درخواست را ارسال کنید
        response = requests.post(token_url, data=payload)
        token_data = response.json()
        
        # برای نمونه، فرض می‌کنیم توکن دریافت شده و اطلاعات کاربر استخراج شده است
        # در محیط واقعی، باید از توکن برای دریافت اطلاعات کاربر استفاده کنید
        user_type = "buyer"  # یا "seller" بر اساس اطلاعات دریافتی
        user_id = "sample_user_id"  # باید با آیدی واقعی کاربر جایگزین شود
        
        # ذخیره اطلاعات کاربر
        user_profile, created = UserProfile.objects.get_or_create(
            user_id=user_id,
            defaults={"user_type": user_type}
        )
        
        # ریدایرکت به مسیر مناسب بر اساس نوع کاربر
        if user_type == "buyer":
            return Response({"redirect": reverse('buyer-terms')})
        else:
            return Response({"redirect": reverse('seller-terms')})


class BuyerViewSet(viewsets.ModelViewSet):
    queryset = BuyerProfile.objects.all()
    serializer_class = BuyerProfileSerializer

    @action(detail=True, methods=['post'])
    def accept_terms(self, request, pk=None):
        try:
            buyer_profile = self.get_object()
        except BuyerProfile.DoesNotExist:
            return Response({'error': 'Buyer profile not found'}, status=status.HTTP_404_NOT_FOUND)

        terms_accepted = request.data.get('terms_accepted')
        if terms_accepted is None:
            return Response({'error': 'terms_accepted is required'}, status=status.HTTP_400_BAD_REQUEST)

        buyer_profile.terms_accepted = terms_accepted
        buyer_profile.save()

        serializer = BuyerProfileSerializer(buyer_profile)
        return Response({
            'message': 'Terms acceptance updated. Buyer process completed.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class SellerViewSet(viewsets.ModelViewSet):
    queryset = SellerProfile.objects.all()
    serializer_class = SellerProfileSerializer

    @action(detail=True, methods=['post'])
    def accept_terms(self, request, pk=None):
        try:
            seller_profile = self.get_object()
        except SellerProfile.DoesNotExist:
            return Response({'error': 'Seller profile not found'}, status=status.HTTP_404_NOT_FOUND)

        terms_accepted = request.data.get('terms_accepted')
        if terms_accepted is None:
            return Response({'error': 'terms_accepted is required'}, status=status.HTTP_400_BAD_REQUEST)

        seller_profile.terms_accepted = terms_accepted
        seller_profile.save()

        serializer = SellerProfileSerializer(seller_profile)
        if terms_accepted:
            select_day_url = reverse('sellers-select-day', kwargs={'pk': seller_profile.id})
            return Response({
                'message': 'Terms acceptance updated. Please select a day.',
                'data': serializer.data,
                'next_step': {
                    'action': 'select_day',
                    'url': f'https://parsanami.pythonanywhere.com/{select_day_url}',
                    'method': 'POST',
                    'payload': {'selected_day': 'monday'}  # نمونه
                }
            }, status=status.HTTP_200_OK)
        return Response({
            'message': 'Terms acceptance updated.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def select_day(self, request, pk=None):
        try:
            seller_profile = self.get_object()
        except SellerProfile.DoesNotExist:
            return Response({'error': 'Seller profile not found'}, status=status.HTTP_404_NOT_FOUND)

        selected_day = request.data.get('selected_day')
        if not selected_day:
            return Response({'error': 'selected_day is required'}, status=status.HTTP_400_BAD_REQUEST)

        if selected_day not in [choice[0] for choice in SellerProfile.DAY_CHOICES]:
            return Response({'error': 'Invalid day'}, status=status.HTTP_400_BAD_REQUEST)

        seller_profile.selected_day = selected_day
        seller_profile.save()

        serializer = SellerProfileSerializer(seller_profile)
        return Response({
            'message': 'Day selected. Seller process completed.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)