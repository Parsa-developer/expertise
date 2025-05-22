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

        auth_url = f"{oauth_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code"
        return Response({"auth_url": auth_url})


class OAuthCallbackView(APIView):
    """
    کالبک OAuth دیوار
    """

    def get(self, request, format=None):
        code = request.query_params.get('code')
        if not code:
            return Response({"error": "کد دریافت نشد"}, status=status.HTTP_400_BAD_REQUEST)

        # استفاده از تنظیمات از فایل settings
        token_url = settings.OAUTH2_TOKEN_URL
        client_id = settings.OAUTH2_CLIENT_ID
        client_secret = settings.OAUTH2_CLIENT_SECRET  # استفاده از متغیر محیطی از فایل settings
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


class UserTypeViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def process_user(self, request):
        user_type = request.data.get('user_type')
        username = request.data.get('username')

        if not user_type or not username:
            return Response({'error': 'user_type and username are required'}, status=status.HTTP_400_BAD_REQUEST)

        if user_type not in ['buyer', 'seller']:
            return Response({'error': 'Invalid user_type'}, status=status.HTTP_400_BAD_REQUEST)

        # ایجاد یا دریافت کاربر
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'user_type': user_type}
        )

        if user_type == 'buyer':
            profile, _ = BuyerProfile.objects.get_or_create(user=user)
            serializer = BuyerProfileSerializer(profile)
            # اگر شرایط تأیید نشده، کاربر را به API تأیید هدایت می‌کنیم
            if not profile.terms_accepted:
                accept_terms_url = reverse('buyers-accept-terms', kwargs={'pk': profile.id})
                return Response({
                    'message': 'Buyer profile created. Please accept terms and conditions.',
                    'data': serializer.data,
                    'next_step': {
                        'action': 'accept_terms',
                        'url': f'http://localhost:8000{accept_terms_url}',
                        'method': 'POST',
                        'payload': {'terms_accepted': True}
                    }
                }, status=status.HTTP_200_OK)
            return Response({
                'message': 'Buyer API executed. Terms already accepted.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)

        elif user_type == 'seller':
            profile, _ = SellerProfile.objects.get_or_create(user=user)
            serializer = SellerProfileSerializer(profile)
            if not profile.terms_accepted:
                accept_terms_url = reverse('sellers-accept-terms', kwargs={'pk': profile.id})
                return Response({
                    'message': 'Seller profile created. Please accept terms and conditions.',
                    'data': serializer.data,
                    'next_step': {
                        'action': 'accept_terms',
                        'url': f'http://localhost:8000{accept_terms_url}',
                        'method': 'POST',
                        'payload': {'terms_accepted': True}
                    }
                }, status=status.HTTP_200_OK)
            elif not profile.selected_day:
                select_day_url = reverse('sellers-select-day', kwargs={'pk': profile.id})
                return Response({
                    'message': 'Seller terms accepted. Please select a day.',
                    'data': serializer.data,
                    'next_step': {
                        'action': 'select_day',
                        'url': f'http://localhost:8000{select_day_url}',
                        'method': 'POST',
                        'payload': {'selected_day': 'monday'}  # نمونه
                    }
                }, status=status.HTTP_200_OK)
            return Response({
                'message': 'Seller API executed. Terms already accepted.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)


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
                    'url': f'http://localhost:8000{select_day_url}',
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