from datetime import timedelta

from rest_framework import serializers

from ideas.models import AnalysisReport, BusinessIdea, BusinessPlan


class BusinessIdeaListSerializer(serializers.ModelSerializer):
    score = serializers.IntegerField(source="annotated_score", read_only=True)
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = BusinessIdea
        fields = [
            "id",
            "user",
            "title",
            "description",
            "is_deleted",
            "created_at",
            "score",
        ]
        read_only_fields = ["user"]

    def get_created_at(self, obj):
        if obj.created_at:
            local_time = obj.created_at + timedelta(hours=3)
            return local_time.strftime("%Y-%m-%d %H:%M:%S")
        return None


class AnalysisReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisReport
        fields = [
            "id",
            "raw_search_data",
            "ai_analysis",
            "score",
            "created_at",
            "steps",
        ]


class BusinessIdeaSerializer(serializers.ModelSerializer):
    reports = AnalysisReportSerializer(many=True, read_only=True)

    class Meta:
        model = BusinessIdea
        fields = [
            "id",
            "user",
            "title",
            "description",
            "is_deleted",
            "created_at",
            "reports",
        ]
        read_only_fields = ["user"]


class BusinessPlanListSerializer(serializers.ModelSerializer):
    report_id = serializers.IntegerField(source="report.id", read_only=True)
    idea_id = serializers.IntegerField(source="report.idea.id", read_only=True)
    title = serializers.CharField(source="report.idea.title", read_only=True)
    description = serializers.CharField(
        source="report.idea.description", read_only=True
    )

    class Meta:
        model = BusinessPlan
        fields = ["id", "report_id", "idea_id", "title", "description", "created_at"]


class BusinessPlanDetailSerializer(serializers.ModelSerializer):
    report_id = serializers.IntegerField(source="report.id", read_only=True)
    idea_id = serializers.IntegerField(source="report.idea.id", read_only=True)
    title = serializers.CharField(source="report.idea.title", read_only=True)
    description = serializers.CharField(
        source="report.idea.description", read_only=True
    )

    class Meta:
        model = BusinessPlan
        fields = [
            "id",
            "report_id",
            "idea_id",
            "title",
            "description",
            "executive_summary",
            "market_analysis",
            "competitor_positioning",
            "target_audience",
            "revenue_model",
            "marketing_strategy",
            "tech_architecture",
            "roadmap",
            "created_at",
            "updated_at",
        ]
