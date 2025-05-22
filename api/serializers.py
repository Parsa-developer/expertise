from rest_framework import serializers
from .models import User, BuyerProfile, SellerProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'user_type']


class BuyerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = BuyerProfile
        fields = ['user', 'terms_accepted']


class SellerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = SellerProfile
        fields = ['user', 'terms_accepted', 'address', 'selected_day']