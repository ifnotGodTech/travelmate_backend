from rest_framework import serializers
from .models import AboutUs, PrivacyPolicy, TermsOfUse, PartnerCategory, Partner
from drf_spectacular.utils import extend_schema_field


class AboutUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutUs
        fields = ['id', 'content', 'updated_at']
        read_only_fields = ['updated_at']


class PrivacyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacyPolicy
        fields = ['id', 'content', 'last_updated', 'updated_at']
        read_only_fields = ['updated_at']


class TermsOfUseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsOfUse
        fields = ['id', 'content', 'last_updated', 'updated_at']
        read_only_fields = ['updated_at']


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ['id', 'name', 'logo', 'description', 'website', 'category', 'is_active']


class PartnerCategorySerializer(serializers.ModelSerializer):
    partners = PartnerSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerCategory
        fields = ['id', 'name', 'description', 'partners']


class PartnerCategoryDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    partners = PartnerSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerCategory
        fields = ['id', 'category_name', 'description', 'partners']

    @extend_schema_field(str)
    def get_category_name(self, obj):
        return obj.get_name_display()
