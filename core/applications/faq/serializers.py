from rest_framework import serializers
from .models import FAQCategory, FAQ

class FAQSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        fields = ['id', 'category', 'category_name', 'question', 'answer',
                 'is_active', 'created_at', 'updated_at', 'views']
        read_only_fields = ['created_at', 'updated_at', 'views']

    def get_category_name(self, obj):
        return obj.category.get_name_display()

    def create(self, validated_data):
        # Set the current user as creator if available
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)

class FAQCategorySerializer(serializers.ModelSerializer):
    faqs = FAQSerializer(many=True, read_only=True)
    name_display = serializers.SerializerMethodField()

    class Meta:
        model = FAQCategory
        fields = ['id', 'name', 'name_display', 'description', 'icon', 'order', 'faqs']

    def get_name_display(self, obj):
        return obj.get_name_display()
